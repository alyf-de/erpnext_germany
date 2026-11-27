# Copyright (c) 2026, ALYF GmbH and Contributors
# See license.txt

import zipfile
from unittest.mock import patch

import frappe
from frappe.utils import add_days, today

from erpnext_germany.erpnext_germany.doctype.accountant_export.accountant_export import (
	PRINT_FORMAT,
	get_allowed_doctypes,
	get_unique_arcname,
)
from erpnext_germany.tests.utils import ERPNextGermanyTestSuite

COMPANY = "_Test Company"


class IntegrationTestAccountantExport(ERPNextGermanyTestSuite):
	def setUp(self):
		self.with_file = make_journal_entry()
		attach_file(self.with_file, "invoice.txt")
		self.without_file = make_journal_entry()

	def test_documents_are_counted_and_ordered(self):
		export = make_export()
		counts = get_counts(export)

		self.assertEqual(counts[self.with_file.name], 1)
		self.assertEqual(counts[self.without_file.name], 0)
		attachments = [row.attachments for row in export.documents]
		self.assertEqual(attachments, sorted(attachments))

	def test_zip_file_holds_the_attachments(self):
		export = make_export()
		export.submit()

		names = get_zip_names(export)
		self.assertIn(f"Journal Entry/{self.with_file.name}/invoice.txt", names)
		self.assertFalse(any(self.without_file.name in name for name in names))

	def test_included_documents_are_skipped_later(self):
		make_export().submit()

		counts = get_counts(make_export())
		self.assertNotIn(self.with_file.name, counts)
		# without attachment it was not part of the ZIP file, so it is considered again
		self.assertEqual(counts[self.without_file.name], 0)

	def test_allow_duplicates(self):
		make_export().submit()

		counts = get_counts(make_export(allow_duplicates=1))
		self.assertEqual(counts[self.with_file.name], 1)

	def test_late_submissions_are_included(self):
		"""A document dated before the previous export is picked up by the next one."""
		make_export().submit()
		late = make_journal_entry(posting_date=add_days(today(), -1))
		attach_file(late, "late.txt")

		self.assertEqual(get_counts(make_export())[late.name], 1)

	def test_from_date_limits_the_documents(self):
		counts = get_counts(make_export(from_date=add_days(today(), 1), to_date=add_days(today(), 1)))
		self.assertNotIn(self.with_file.name, counts)

	def test_files_added_before_submit_are_counted(self):
		export = make_export()
		attach_file(self.without_file, "receipt.txt")
		export.submit()

		self.assertEqual(get_counts(export)[self.without_file.name], 1)
		self.assertIn(f"Journal Entry/{self.without_file.name}/receipt.txt", get_zip_names(export))

	def test_cancelled_documents_are_reported_once(self):
		previous = make_export()
		previous.submit()
		self.with_file.reload()
		self.with_file.cancel()

		export = make_export()
		cancelled = {row.reference_name: row for row in export.cancelled_documents}
		self.assertEqual(cancelled[self.with_file.name].previous_accountant_export, previous.name)

		html = frappe.get_print(
			export.doctype, export.name, PRINT_FORMAT, doc=frappe.get_doc(export.as_dict())
		)
		self.assertIn(self.with_file.name, html)

		with patch("frappe.get_print", return_value=b"%PDF-1.4") as get_print:
			export.submit()

		get_print.assert_called_once()
		self.assertIn("Cancelled Documents.pdf", get_zip_names(export))

		later = make_export()
		self.assertNotIn(self.with_file.name, [row.reference_name for row in later.cancelled_documents])

	def test_cancelled_documents_without_previous_export_are_ignored(self):
		self.with_file.reload()
		self.with_file.cancel()

		cancelled = [row.reference_name for row in make_export().cancelled_documents]
		self.assertNotIn(self.with_file.name, cancelled)

	def test_unsupported_doctype_is_rejected(self):
		export = make_export(doctypes=[{"reference_doctype": "Sales Order"}], insert=False)
		self.assertRaises(frappe.ValidationError, export.insert)

	def test_invalid_attach_field_is_rejected(self):
		export = make_export(
			doctypes=[{"reference_doctype": "Journal Entry", "attach_field": "remark"}], insert=False
		)
		self.assertRaises(frappe.ValidationError, export.insert)

	def test_expense_claim_depends_on_hrms(self):
		self.assertEqual("Expense Claim" in get_allowed_doctypes(), "hrms" in frappe.get_installed_apps())

	def test_unique_arcname(self):
		arcnames = set()
		self.assertEqual(get_unique_arcname("a/b.pdf", arcnames), "a/b.pdf")
		self.assertEqual(get_unique_arcname("a/b.pdf", arcnames), "a/b (1).pdf")


def make_export(insert=True, **kwargs):
	export = frappe.get_doc(
		{
			"doctype": "Accountant Export",
			"company": COMPANY,
			"to_date": today(),
			"doctypes": [{"reference_doctype": "Journal Entry"}],
			**kwargs,
		}
	)
	return export.insert() if insert else export


def make_journal_entry(posting_date=None):
	journal_entry = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": COMPANY,
			"posting_date": posting_date or today(),
			"accounts": [
				{"account": "_Test Bank - _TC", "debit_in_account_currency": 100},
				{"account": "_Test Cash - _TC", "credit_in_account_currency": 100},
			],
		}
	)
	journal_entry.insert()
	journal_entry.submit()
	return journal_entry


def attach_file(doc, file_name):
	return frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"content": b"test",
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"is_private": 1,
		}
	).insert()


def get_counts(export):
	return {row.reference_name: row.attachments for row in export.documents}


def get_zip_names(export):
	path = frappe.get_doc("File", export.zip_file).get_full_path()
	with zipfile.ZipFile(path) as archive:
		return archive.namelist()
