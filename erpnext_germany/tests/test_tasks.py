# Copyright (c) 2026, ALYF GmbH and Contributors
# See license.txt

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_months, now_datetime

from erpnext_germany.tasks import check_some_parties, get_customers, get_suppliers
from erpnext_germany.tests.utils import ERPNextGermanyTestSuite

VALID_RESULT = SimpleNamespace(
	valid=True,
	traderNameMatch=None,
	traderStreetMatch=None,
	traderPostcodeMatch=None,
	traderCityMatch=None,
	requestIdentifier="WAPIAAAAZ1234567",
	traderName="Example GmbH",
	traderAddress="Example Street 1",
)


class TestTasks(ERPNextGermanyTestSuite):
	def make_customer(self, customer_name, tax_id="DE329035522"):
		return (
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": customer_name,
					"customer_group": "_Test Customer Group",
					"territory": "_Test Territory",
					"tax_id": tax_id,
				}
			)
			.insert()
			.name
		)

	def make_supplier(self, supplier_name, tax_id="DE329035522"):
		return (
			frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": supplier_name,
					"supplier_group": "_Test Supplier Group",
					"tax_id": tax_id,
				}
			)
			.insert()
			.name
		)

	def make_check(self, party, status, creation, party_type="Customer"):
		with patch("frappe.enqueue"):
			doc = frappe.get_doc(
				{
					"doctype": "VAT ID Check",
					"party_type": party_type,
					"party": party,
					"party_vat_id": "DE329035522",
				}
			).insert()

		frappe.db.set_value(
			"VAT ID Check", doc.name, {"status": status, "creation": creation}, update_modified=False
		)

	def is_due(self, customer):
		return customer in [row[1] for row in get_customers(batch_size=10000)]

	def run_scheduler(self, customers, suppliers=()):
		with (
			patch("erpnext_germany.tasks.get_default_company", return_value=None),
			patch("erpnext_germany.tasks.get_customers", return_value=list(customers)),
			patch("erpnext_germany.tasks.get_suppliers", return_value=list(suppliers)),
			patch("erpnext_germany.utils.eu_vat.Client") as client,
		):
			client.return_value.service.checkVatApprox.return_value = VALID_RESULT
			check_some_parties()

		return client.return_value.service.checkVatApprox

	def get_status(self, party):
		return frappe.db.get_value("VAT ID Check", {"party": party}, "status")

	def test_unparseable_vat_id_does_not_stop_the_run(self):
		"""A party with an unparseable VAT ID is recorded as "Invalid Input", the others are checked."""
		unparseable = self.make_customer("_Test VAT Unparseable", "CHE-123.456.789 MWST")
		customer = self.make_customer("_Test VAT Customer")
		supplier = self.make_supplier("_Test VAT Supplier")

		check_vat_approx = self.run_scheduler(
			customers=[
				("Customer", unparseable, unparseable, None, "CHE-123.456.789 MWST"),
				("Customer", customer, customer, None, "DE329035522"),
			],
			suppliers=[("Supplier", supplier, supplier, None, "DE329035522")],
		)

		self.assertEqual(self.get_status(unparseable), "Invalid Input")
		self.assertEqual(self.get_status(customer), "Completed")
		self.assertEqual(self.get_status(supplier), "Completed")
		self.assertEqual(check_vat_approx.call_count, 2)

	def test_failing_party_does_not_stop_the_run(self):
		"""Any error for one party is logged and the remaining parties are still checked."""
		failing = self.make_customer("_Test VAT Failing")
		customer = self.make_customer("_Test VAT Next")

		self.run_scheduler(
			customers=[
				("Customer", failing, failing, "_Test Missing Address", "DE329035522"),
				("Customer", customer, customer, None, "DE329035522"),
			]
		)

		self.assertIsNone(self.get_status(failing))
		self.assertTrue(frappe.db.exists("Error Log", {"reference_name": failing}))
		self.assertEqual(self.get_status(customer), "Completed")

	def test_empty_tax_id_is_not_checked(self):
		customer = self.make_customer("_Test VAT Empty", "")
		supplier = self.make_supplier("_Test VAT Empty Supplier", "")

		self.assertFalse(self.is_due(customer))
		self.assertNotIn(supplier, [row[1] for row in get_suppliers(batch_size=10000)])

	def test_result_is_kept_for_three_months(self):
		customer = self.make_customer("_Test VAT Completed")
		self.assertTrue(self.is_due(customer))

		self.make_check(customer, "Completed", add_days(now_datetime(), -2))
		self.assertFalse(self.is_due(customer))

		frappe.db.set_value("VAT ID Check", {"party": customer}, "creation", add_months(now_datetime(), -4))
		self.assertTrue(self.is_due(customer))

	def test_service_unavailable_is_retried_after_a_day(self):
		customer = self.make_customer("_Test VAT Unavailable")

		self.make_check(customer, "Service Unavailable", now_datetime())
		self.assertFalse(self.is_due(customer))

		frappe.db.set_value("VAT ID Check", {"party": customer}, "creation", add_days(now_datetime(), -2))
		self.assertTrue(self.is_due(customer))

	def test_stale_check_is_retried_after_a_day(self):
		"""A check that never finished blocks the party for a day, not forever and not just one run."""
		customer = self.make_customer("_Test VAT Running")

		self.make_check(customer, "Running", now_datetime())
		self.assertFalse(self.is_due(customer))

		frappe.db.set_value("VAT ID Check", {"party": customer}, "creation", add_days(now_datetime(), -2))
		self.assertTrue(self.is_due(customer))

	def test_old_result_waits_for_recent_failure(self):
		"""An expired result does not bypass the delay after a failed attempt."""
		customer = self.make_customer("_Test VAT Expired")

		self.make_check(customer, "Completed", add_months(now_datetime(), -4))
		self.make_check(customer, "Service Unavailable", now_datetime())
		self.assertFalse(self.is_due(customer))
