# Copyright (c) 2023, ALYF GmbH and Contributors
# See license.txt

from types import SimpleNamespace
from unittest.mock import patch

import frappe

from erpnext_germany.tests.utils import ERPNextGermanyTestSuite


class TestVATIDCheck(ERPNextGermanyTestSuite):
	def run_check_with_vies(self, check_vat_approx):
		"""Insert a VAT ID Check (runs synchronously in tests) with a stubbed VIES client."""
		with patch("erpnext_germany.utils.eu_vat.Client") as client:
			client.return_value.service.checkVatApprox = check_vat_approx
			doc = frappe.get_doc({"doctype": "VAT ID Check", "party_vat_id": "DE329035522"}).insert()

		doc.reload()
		return doc

	def test_valid_result(self):
		result = SimpleNamespace(
			valid=True,
			traderNameMatch=None,
			traderStreetMatch=None,
			traderPostcodeMatch=None,
			traderCityMatch=None,
			requestIdentifier="WAPIAAAAZ1234567",
			traderName="Example GmbH",
			traderAddress="Example Street 1",
		)

		def check_vat_approx(**kwargs):
			self.assertEqual(kwargs["countryCode"], "DE")
			self.assertEqual(kwargs["vatNumber"], "329035522")
			return result

		doc = self.run_check_with_vies(check_vat_approx)

		self.assertEqual(doc.status, "Completed")
		self.assertTrue(doc.is_valid)
		self.assertEqual(doc.request_id, "WAPIAAAAZ1234567")

	def test_service_unavailable(self):
		"""Exhausted retries must end as "Service Unavailable", not as "Error"."""

		def check_vat_approx(**_kwargs):
			raise Exception("SERVICE_UNAVAILABLE")

		doc = self.run_check_with_vies(check_vat_approx)

		self.assertEqual(doc.status, "Service Unavailable")

	def test_invalid_vat_id(self):
		"""A user creating a check for an unparseable VAT ID gets a validation message."""
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "VAT ID Check", "party_vat_id": "CHE-123.456.789 MWST"}).insert()

	def test_invalid_vat_id_recorded(self):
		"""With the flag set, an unparseable VAT ID is stored as "Invalid Input" without asking VIES."""
		doc = frappe.get_doc({"doctype": "VAT ID Check", "party_vat_id": "CHE-123.456.789 MWST"})
		doc.flags.ignore_invalid_vat_id = True
		with patch("frappe.enqueue") as enqueue:
			doc.insert()

		enqueue.assert_not_called()
		doc.reload()
		self.assertEqual(doc.status, "Invalid Input")
		self.assertFalse(doc.is_valid)

	def test_enqueued_after_commit(self):
		"""The job is requested after commit. Tests run it inline, so only the argument is checked."""
		with patch("frappe.enqueue") as enqueue:
			frappe.get_doc({"doctype": "VAT ID Check", "party_vat_id": "DE329035522"}).insert()

		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])

	def test_duplicate_is_checked_again(self):
		"""A check created with a status from another check (e.g. via Duplicate) still asks VIES."""
		with patch("frappe.enqueue") as enqueue:
			doc = frappe.get_doc(
				{"doctype": "VAT ID Check", "party_vat_id": "DE329035522", "status": "Completed"}
			).insert()

		enqueue.assert_called_once()
		self.assertEqual(doc.status, "Planned")

	def test_status_is_not_copied(self):
		self.assertTrue(frappe.get_meta("VAT ID Check").get_field("status").no_copy)
