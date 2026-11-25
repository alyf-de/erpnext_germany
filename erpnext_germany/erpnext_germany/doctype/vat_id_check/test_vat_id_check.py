# Copyright (c) 2023, ALYF GmbH and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_germany.erpnext_germany.doctype.vat_id_check.vat_id_check import run_check


class TestVATIDCheck(FrappeTestCase):
	def test_invalid_vat_id(self):
		"""A user creating a check for an unparseable VAT ID gets a validation message."""
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "VAT ID Check", "party_vat_id": "CHE-123.456.789 MWST"}).insert()

	def test_invalid_requester_vat_id(self):
		"""A user still gets a validation message for an unparseable requester VAT ID."""
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "VAT ID Check",
					"party_vat_id": "DE329035522",
					"requester_vat_id": "123/456/78901",
				}
			).insert()

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

	def test_rolled_back_check_is_not_run(self):
		"""A job whose check no longer exists does not ask VIES."""
		doc = frappe.get_doc({"doctype": "VAT ID Check", "party_vat_id": "DE329035522"})
		doc.name = "rolled-back-check"

		with patch("erpnext_germany.utils.eu_vat.Client") as client:
			run_check(doc)

		client.assert_not_called()
