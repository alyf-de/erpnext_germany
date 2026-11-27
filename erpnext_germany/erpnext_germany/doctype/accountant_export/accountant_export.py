# Copyright (c) 2026, ALYF GmbH and contributors
# For license information, please see license.txt

"""
Collect the files of the accounting documents for the tax advisor in a ZIP file.

A document is part of the ZIP file once. Later runs skip it, unless *Allow
Duplicates* is set. Documents without attachments are not included and are
therefore considered again in the next run. Selecting by "up to the To Date and
not included yet" (instead of a fixed period) catches documents that were
submitted after the previous export was created.
"""

import os
import zipfile
from collections import defaultdict
from urllib.parse import quote

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType

from erpnext_germany.erpnext_germany.doctype.gdpdu_export.gdpdu_export import get_period_field

PRINT_FORMAT = "Accountant Export Cancelled Documents"
ATTACH_FIELDTYPES = ("Attach", "Attach Image")


class AccountantExport(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext_germany.erpnext_germany.doctype.accountant_export_cancelled_document.accountant_export_cancelled_document import (  # noqa: E501
			AccountantExportCancelledDocument,
		)
		from erpnext_germany.erpnext_germany.doctype.accountant_export_doctype.accountant_export_doctype import (  # noqa: E501
			AccountantExportDocType,
		)
		from erpnext_germany.erpnext_germany.doctype.accountant_export_document.accountant_export_document import (  # noqa: E501
			AccountantExportDocument,
		)

		allow_duplicates: DF.Check
		amended_from: DF.Link | None
		cancelled_documents: DF.Table[AccountantExportCancelledDocument]
		company: DF.Link
		doctypes: DF.Table[AccountantExportDocType]
		documents: DF.Table[AccountantExportDocument]
		from_date: DF.Date | None
		to_date: DF.Date
		zip_file: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		if not self.doctypes:
			self.extend("doctypes", get_default_doctypes())

		self.fill_documents()

	def validate(self):
		if self.from_date and self.to_date and self.from_date > self.to_date:
			frappe.throw(_("From Date has to be before To Date."))

		validate_doctypes(self.doctypes)

		# set if the documents were just filled, e.g. by "Refresh Documents"
		documents_filled = self.flags.pop("documents_filled", False)
		if self.docstatus == 0:
			if not self.is_new() and not documents_filled and self.filters_changed():
				self.fill_documents()

			self.show_other_drafts()

	def filters_changed(self) -> bool:
		"""Return whether the documents table is based on other filters than the current ones."""
		before = self.get_doc_before_save()
		if not before:
			return False

		def get_filters(doc):
			return (
				doc.from_date and str(doc.from_date),
				doc.to_date and str(doc.to_date),
				bool(doc.allow_duplicates),
				[(row.reference_doctype, row.attach_field or None) for row in doc.doctypes],
			)

		return get_filters(before) != get_filters(self)

	def show_other_drafts(self):
		"""Two drafts can contain the same documents. Only the first one submitted should export them."""
		other_drafts = frappe.get_all(
			"Accountant Export",
			filters={"company": self.company, "docstatus": 0, "name": ("!=", self.name)},
			pluck="name",
		)
		if not other_drafts:
			return

		frappe.msgprint(
			_(
				"There are other draft Accountant Exports for {0}: {1}. They may contain the same documents. Please submit or delete them first, and refresh the documents of this one afterwards."  # noqa: E501
			).format(self.company, ", ".join(other_drafts)),
			title=_("Other Drafts"),
			indicator="orange",
		)

	@frappe.whitelist()
	def refresh_documents(self):
		if self.docstatus != 0:
			frappe.throw(_("Documents can only be refreshed before submitting."))

		self.check_permission("write")
		self.fill_documents()
		self.save()

	def before_submit(self):
		self.update_attachment_counts()

	def on_submit(self):
		self.create_zip_file()

	def fill_documents(self):
		"""Find the documents to be exported, as well as the cancelled ones."""
		validate_doctypes(self.doctypes)

		documents = []
		for row in self.doctypes:
			names = self.get_document_names(row.reference_doctype)
			attachments = get_attachments(row.reference_doctype, names, row.attach_field)
			documents.extend(
				{
					"reference_doctype": row.reference_doctype,
					"reference_name": name,
					"attachments": len(attachments.get(name, [])),
				}
				for name in names
			)

		# stable sort: within the same count, the documents stay ordered by DocType and date
		documents.sort(key=lambda document: document["attachments"])
		self.set("documents", documents)
		self.set("cancelled_documents", self.get_cancelled_documents())
		self.show_documents_without_attachments()
		self.flags.documents_filled = True

	def get_document_names(self, doctype: str) -> list[str]:
		"""
		Return the submitted documents up to the To Date, in order of their date.

		The accountant needs the full picture, so the documents are not limited by
		the user's permissions. Instead, only Accounts Manager and System Manager
		have access to Accountant Export (and its ZIP file).
		"""
		date_field = get_period_field(frappe.get_meta(doctype))
		filters = {"company": self.company, "docstatus": 1}
		filters[date_field] = (
			("between", [self.from_date, self.to_date]) if self.from_date else ("<=", self.to_date)
		)

		names = frappe.get_all(doctype, filters=filters, pluck="name", order_by=f"{date_field} asc, name asc")

		if self.allow_duplicates:
			return names

		included = get_included_documents(doctype)
		return [name for name in names if name not in included]

	def get_cancelled_documents(self) -> list[dict]:
		"""Return the documents that were included in a previous export and have been cancelled since."""
		cancelled = []
		for doctype, included in get_included_documents_by_doctype(self.company).items():
			reported = get_reported_cancelled_documents(doctype)
			candidates = [name for name in included if name not in reported]
			if not candidates:
				continue

			cancelled.extend(
				{
					"reference_doctype": doctype,
					"reference_name": name,
					"previous_accountant_export": included[name],
				}
				for name in frappe.get_all(
					doctype,
					filters={"name": ("in", candidates), "docstatus": 2},
					pluck="name",
					order_by="name asc",
				)
			)

		return cancelled

	def show_documents_without_attachments(self):
		counts = defaultdict(int)
		for row in self.documents:
			if not row.attachments:
				counts[row.reference_doctype] += 1

		if not counts:
			return

		frappe.msgprint(
			_(
				"There are {0} without attachments. They are not included in the ZIP file and will be considered again in the next Accountant Export."  # noqa: E501
			).format(
				", ".join(
					_("{0} documents of type {1}").format(count, _(doctype))
					for doctype, count in counts.items()
				)
			),
			title=_("Documents without Attachments"),
			indicator="orange",
		)

	def update_attachment_counts(self):
		"""Files may have been added or removed since the documents were refreshed."""
		attach_fields = {row.reference_doctype: row.attach_field for row in self.doctypes}

		for doctype, rows in self.get_documents_by_doctype().items():
			if doctype not in attach_fields:
				frappe.throw(_("{0} is not selected in the DocTypes table.").format(_(doctype)))

			attachments = get_attachments(
				doctype, [row.reference_name for row in rows], attach_fields[doctype]
			)
			for row in rows:
				row.attachments = len(attachments.get(row.reference_name, []))

	def get_documents_by_doctype(self, with_attachments_only: bool = False) -> dict[str, list]:
		documents = defaultdict(list)
		for row in self.documents:
			if with_attachments_only and not row.attachments:
				continue

			documents[row.reference_doctype].append(row)

		return documents

	def create_zip_file(self):
		attach_fields = {row.reference_doctype: row.attach_field for row in self.doctypes}
		file_name = get_unique_file_name(f"{self.name}.zip")
		path = frappe.get_site_path("private", "files", file_name)
		frappe.db.after_rollback.add(lambda: os.path.exists(path) and os.remove(path))

		with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
			arcnames = set()
			for doctype, rows in self.get_documents_by_doctype(with_attachments_only=True).items():
				names = [row.reference_name for row in rows]
				attachments = get_attachments(doctype, names, attach_fields.get(doctype))
				for name in names:
					for file in attachments.get(name, []):
						arcname = get_unique_arcname(
							f"{doctype}/{quote(name, safe='')}/{file.file_name}", arcnames
						)
						archive.write(get_full_path(file), arcname=arcname)

			if self.cancelled_documents:
				archive.writestr(
					f"{_('Cancelled Documents')}.pdf",
					# printing flags the document as `in_print`, which turns `save` into a no-op
					frappe.get_print(
						self.doctype, self.name, PRINT_FORMAT, doc=frappe.get_doc(self.as_dict()), as_pdf=True
					),
				)

		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": file_name,
				"file_url": f"/private/files/{file_name}",
				"file_size": os.path.getsize(path),
				"is_private": 1,
				"attached_to_doctype": self.doctype,
				"attached_to_name": self.name,
			}
		)
		# the archive is already on disk, it must not be read into memory (and limited
		# by the maximum upload size) again
		file.flags.copy_from_existing_file = True
		file.insert(ignore_permissions=True)
		self.db_set("zip_file", file.name)


@frappe.whitelist()
def get_allowed_doctypes() -> list[str]:
	doctypes = ["Purchase Invoice", "Sales Invoice", "Journal Entry", "Payment Entry"]
	if "hrms" in frappe.get_installed_apps():  # Expense Claim is part of HRMS
		doctypes.insert(0, "Expense Claim")

	return doctypes


@frappe.whitelist()
def get_default_doctypes() -> list[dict]:
	"""Return the DocTypes set in ERPNext Germany Settings, or all allowed ones."""
	frappe.has_permission("Accountant Export", "create", throw=True)
	allowed = get_allowed_doctypes()
	settings = frappe.get_single("ERPNext Germany Settings")
	defaults = [
		{"reference_doctype": row.reference_doctype, "attach_field": row.attach_field}
		for row in settings.accountant_export_doctypes
		if row.reference_doctype in allowed
	]

	return defaults or [{"reference_doctype": doctype} for doctype in allowed]


def validate_doctypes(rows):
	allowed = get_allowed_doctypes()
	seen = set()
	for row in rows:
		if row.reference_doctype not in allowed:
			frappe.throw(
				_("Row {0}: {1} is not supported. Please select one of {2}.").format(
					row.idx, _(row.reference_doctype), ", ".join(_(doctype) for doctype in allowed)
				)
			)

		if row.reference_doctype in seen:
			frappe.throw(
				_("Row {0}: {1} is selected more than once.").format(row.idx, _(row.reference_doctype))
			)

		seen.add(row.reference_doctype)

		if row.attach_field:
			df = frappe.get_meta(row.reference_doctype).get_field(row.attach_field)
			if not df or df.fieldtype not in ATTACH_FIELDTYPES:
				frappe.throw(
					_("Row {0}: {1} is not an attach field of {2}.").format(
						row.idx, row.attach_field, _(row.reference_doctype)
					)
				)


def get_attachments(doctype: str, names: list[str], attach_field: str | None = None) -> dict[str, list]:
	"""
	Return the local files attached to the given documents, by document name.

	If an attach field is set, only the file referenced in that field is returned.
	"""
	if not names:
		return {}

	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": doctype, "attached_to_name": ("in", names), "is_folder": 0},
		fields=["name", "attached_to_name", "file_name", "file_url", "is_private"],
		order_by="creation asc",
	)

	if attach_field:
		values = dict(
			frappe.get_all(
				doctype,
				filters={"name": ("in", names)},
				fields=["name", attach_field],
				as_list=True,
			)
		)
		files = [
			file for file in files if file.file_url and file.file_url == values.get(file.attached_to_name)
		]

	attachments = defaultdict(list)
	for file in files:
		# remote files cannot be put into the archive
		if file.file_url and file.file_url.startswith(("/files/", "/private/files/")):
			attachments[file.attached_to_name].append(file)

	return attachments


def get_included_documents(doctype: str) -> set[str]:
	"""Return the documents that are part of the ZIP file of a submitted Accountant Export."""
	document = DocType("Accountant Export Document")
	export = DocType("Accountant Export")
	return set(
		frappe.qb.from_(document)
		.join(export)
		.on(document.parent == export.name)
		.select(document.reference_name)
		.where(
			(export.docstatus == 1)
			& (document.parenttype == "Accountant Export")
			& (document.parentfield == "documents")
			& (document.reference_doctype == doctype)
			& (document.attachments > 0)
		)
		.run(pluck=True)
	)


def get_included_documents_by_doctype(company: str) -> dict[str, dict[str, str]]:
	"""Return {doctype: {name: latest Accountant Export}} for everything included for the company."""
	document = DocType("Accountant Export Document")
	export = DocType("Accountant Export")
	rows = (
		frappe.qb.from_(document)
		.join(export)
		.on(document.parent == export.name)
		.select(document.reference_doctype, document.reference_name, export.name)
		.where(
			(export.docstatus == 1)
			& (export.company == company)
			& (document.parenttype == "Accountant Export")
			& (document.parentfield == "documents")
			& (document.attachments > 0)
		)
		.orderby(export.creation)
		.run()
	)

	included = defaultdict(dict)
	for doctype, name, export_name in rows:
		included[doctype][name] = export_name

	return included


def get_reported_cancelled_documents(doctype: str) -> set[str]:
	"""Return the cancelled documents that are already listed in a submitted Accountant Export."""
	cancelled = DocType("Accountant Export Cancelled Document")
	export = DocType("Accountant Export")
	return set(
		frappe.qb.from_(cancelled)
		.join(export)
		.on(cancelled.parent == export.name)
		.select(cancelled.reference_name)
		.where(
			(export.docstatus == 1)
			& (cancelled.parenttype == "Accountant Export")
			& (cancelled.reference_doctype == doctype)
		)
		.run(pluck=True)
	)


def get_full_path(file) -> str:
	path = frappe.get_doc("File", file.name).get_full_path()
	if not os.path.exists(path):
		frappe.throw(
			_("The file {0} attached to {1} does not exist on disk.").format(
				file.file_name, file.attached_to_name
			)
		)

	return path


def get_unique_file_name(file_name: str) -> str:
	if not os.path.exists(frappe.get_site_path("private", "files", file_name)):
		return file_name

	stem, extension = os.path.splitext(file_name)
	return f"{stem}-{frappe.generate_hash(length=6)}{extension}"


def get_unique_arcname(arcname: str, arcnames: set[str]) -> str:
	"""Two files of one document may share a name, the second one must not overwrite the first."""
	stem, extension = os.path.splitext(arcname)
	candidate = arcname
	counter = 1
	while candidate in arcnames:
		candidate = f"{stem} ({counter}){extension}"
		counter += 1

	arcnames.add(candidate)
	return candidate
