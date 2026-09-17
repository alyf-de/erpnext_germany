# Copyright (c) 2026, ALYF GmbH and contributors
# For license information, please see license.txt

"""
Hand over recording- and retention-relevant data in machine-evaluable form.

On demand the business itself has to provide its data together with the
structural information needed to evaluate them (§ 147 Abs. 6 AO, GoBD in the
version of the BMF letter of 11.03.2024). This export writes one CSV file per
selected DocType plus an index.xml that describes them: the columns in physical
order, their data types, the separators used and the links between the tables.

It follows the description standard (Beschreibungsstandard) 1.6 of CaseWare
Germany GmbH, which is validated against a DTD that has to sit next to
index.xml, so both files travel in the ZIP.
"""

import csv
import io
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import quote

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_default_address
from frappe.model import no_value_fields
from frappe.model.document import Document
from frappe.utils import add_days, formatdate
from frappe.utils.file_manager import save_file

DTD_FILE_NAME = "gdpdu-01-03-2019.dtd"
INDEX_FILE_NAME = "index.xml"

PROLOG = (
	f'<?xml version="1.0" encoding="utf-8" standalone="no"?>\n<!DOCTYPE DataSet SYSTEM "{DTD_FILE_NAME}">\n'
)

# Row 1 holds the field names ("Kopfdatensatz", Anlage 1.4), the payload starts
# in row 2. There is no element that declares a header record, it is skipped by
# starting to read later.
FIRST_DATA_ROW = "2"

# Rows fetched per query. Tables are written to the archive while they are read,
# so only one batch is held in memory at a time.
BATCH_SIZE = 5000

# Fieldtypes that are not delivered as text, mapped to their number of decimals.
NUMERIC_FIELDTYPES = {
	"Currency": 2,
	"Float": 6,
	"Percent": 6,
	"Int": 0,
	"Long Int": 0,
	"Check": 0,
	"Rating": 2,
}

# Written by the database driver as YYYY-MM-DD. `Format` of a Date only knows
# the symbols DD, MM and YY/YYYY, so Datetime and Time stay AlphaNumeric.
DATE_FIELDTYPES = {"Date": "YYYY-MM-DD"}

# Cut by the period of the export, in this order of preference. `creation` is
# deliberately not among them: master data carries no business date, and cutting
# it by the period would leave the transactions referring to rows that are not
# part of the data set.
PERIOD_FIELDS = ("posting_date", "transaction_date", "date")

# Encrypted at rest and of no interest to the audit.
SKIPPED_FIELDTYPES = {"Password"}

# Recorded by the framework for every document, not part of `meta.fields`.
TRAILING_COLUMNS = (
	("owner", "Data"),
	("creation", "Datetime"),
	("modified", "Datetime"),
	("modified_by", "Data"),
	("docstatus", "Int"),
)

ATTACHMENT_COLUMNS = (
	("name", "Data"),
	("attached_to_doctype", "Data"),
	("attached_to_name", "Data"),
	("file_name", "Data"),
	("file_size", "Int"),
	("is_private", "Check"),
	("path", "Data"),
)


class GDPdUExport(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext_germany.erpnext_germany.doctype.gdpdu_doctype.gdpdu_doctype import GDPdUDocType

		amended_from: DF.Link | None
		company: DF.Link
		export_file: DF.Attach | None
		exported_doctypes: DF.Table[GDPdUDocType]
		from_date: DF.Date | None
		status: DF.Literal["", "Queued", "Completed", "Failed"]
		to_date: DF.Date | None
	# end: auto-generated types

	def validate(self):
		if self.from_date and self.to_date and self.from_date > self.to_date:
			frappe.throw(_("From Date has to be before To Date."))

		if not self.exported_doctypes:
			frappe.throw(_("Select at least one DocType to export."))

		seen = set()
		for row in self.exported_doctypes:
			if row.exported_doctype in seen:
				frappe.throw(
					_("Row {0}: {1} is selected more than once.").format(row.idx, row.exported_doctype)
				)

			seen.add(row.exported_doctype)

			if frappe.get_meta(row.exported_doctype).is_virtual:
				frappe.throw(
					_("Row {0}: {1} is a virtual DocType and holds no data.").format(
						row.idx, row.exported_doctype
					)
				)

		self.check_export_permissions()

	def check_export_permissions(self):
		"""
		Check the right to export every selected DocType.

		The build reads whole tables without a permission check of its own, so
		every path that starts one has to ask first.
		"""
		for row in self.exported_doctypes:
			if not frappe.has_permission(row.exported_doctype, "export"):
				frappe.throw(
					_("Row {0}: You are not allowed to export {1}.").format(row.idx, row.exported_doctype),
					frappe.PermissionError,
				)

	def on_submit(self):
		self.enqueue_export()

	@frappe.whitelist()
	def enqueue_export(self):
		"""Queue the build, also to retry one that failed."""
		self.check_export_permissions()
		self.check_permission("submit")
		self.db_set("status", "Queued")
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"build_export",
			queue="long",
			timeout=3600,
			enqueue_after_commit=True,
		)

	def build_export(self):
		"""Write the archive and attach it to this document."""
		try:
			content = build_archive(self)
			# attaching fails on its own account, e.g. when the archive is larger
			# than the maximum file size, so it is watched along with the build
			file = save_file(f"{self.name}.zip", content, self.doctype, self.name, is_private=1)
			self.db_set("export_file", file.file_url)
			self.db_set("status", "Completed")
		except Exception:
			# the form reads the status: without it a failed export stays
			# indistinguishable from one that is still being generated
			self.db_set("status", "Failed")
			self.add_comment("Comment", _("The export failed, see the error log."))
			frappe.log_error(title=f"GDPdU Export {self.name} failed")


def build_archive(export) -> bytes:
	"""
	Return a ZIP archive holding one CSV per DocType, the attached files and index.xml.

	Arguments:
	export -- the `GDPdU Export` naming the DocTypes, the company and the period
	"""
	tables = []

	for row in export.exported_doctypes:
		# A child table is a table of its own, linked to its parent by `parent`, and
		# one per parent: `get_rows` cuts it to a single `parenttype`, so a DocType
		# used by two parents (Contact and Address both link Dynamic Link) has to be
		# delivered once per parent or the second parent's rows are missing.
		for doctype, parent in [(row.exported_doctype, None)] + [
			(child, row.exported_doctype) for child in get_child_doctypes(row.exported_doctype)
		]:
			tables.append(get_table(doctype, export, parent))

	# ponytail: the archive is built on disk but read into memory once to attach
	# it. Build the File document by hand if exports outgrow the worker.
	with tempfile.TemporaryDirectory() as directory:
		path = Path(directory) / "export.zip"

		with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
			for table in tables:
				write_csv(archive, table, export)

			for row in export.exported_doctypes:
				if row.include_attached_files:
					names = get_exported_names(row.exported_doctype, export)
					tables.append(write_attachments(archive, row.exported_doctype, names))

			archive.writestr(INDEX_FILE_NAME, get_index_xml(tables, export))
			archive.write(Path(__file__).parent / DTD_FILE_NAME, arcname=DTD_FILE_NAME)

		return path.read_bytes()


def get_table(doctype: str, export, parent: str | None = None) -> frappe._dict:
	"""Describe one DocType as a table of the data set."""
	meta = frappe.get_meta(doctype)
	# a child row carries neither company nor date of its own, its parent does
	filtered = frappe.get_meta(parent) if parent else meta
	# the table holds the rows of one parent only, so the name has to say which
	table_name = f"{doctype} ({parent})" if parent else doctype
	date_field = get_period_field(filtered)
	columns = [frappe._dict(fieldname="name", fieldtype="Data")]

	if meta.istable:
		# `parenttype` and `parentfield` disambiguate the link, `idx` orders the rows
		columns += [
			frappe._dict(fieldname="parent", fieldtype="Link", options=parent),
			frappe._dict(fieldname="parenttype", fieldtype="Data"),
			frappe._dict(fieldname="parentfield", fieldtype="Data"),
			frappe._dict(fieldname="idx", fieldtype="Int"),
		]

	columns += [df for df in meta.fields if is_exported(df)]
	columns += [
		frappe._dict(fieldname=fieldname, fieldtype=fieldtype) for fieldname, fieldtype in TRAILING_COLUMNS
	]

	return frappe._dict(
		doctype=doctype,
		name=table_name,
		description=_(meta.description or doctype),
		file_name=get_file_name(table_name),
		columns=columns,
		parent_doctype=parent,
		company_field=get_company_field(filtered),
		date_field=date_field,
		# only a table that is really cut by the period may claim one
		validity=(export.from_date, export.to_date)
		if date_field and (export.from_date or export.to_date)
		else None,
	)


def get_company_field(meta) -> str | None:
	"""Return the field that ties a document to a company."""
	if meta.name == "Company":
		return "name"

	for df in meta.fields:
		if df.fieldtype == "Link" and df.options == "Company":
			return df.fieldname

	return None


def get_period_field(meta) -> str | None:
	"""Return the business date of a document, if it has one."""
	for fieldname in PERIOD_FIELDS:
		df = meta.get_field(fieldname)
		if df and df.fieldtype in ("Date", "Datetime"):
			return fieldname

	return None


def is_exported(df) -> bool:
	"""A virtual field holds no column in the database, so there is nothing to read."""
	return (
		df.fieldtype not in no_value_fields and df.fieldtype not in SKIPPED_FIELDTYPES and not df.is_virtual
	)


def get_child_doctypes(doctype: str) -> list[str]:
	"""Return the DocTypes of all child tables, without duplicates and in field order."""
	children = []
	for df in frappe.get_meta(doctype).fields:
		if df.fieldtype in ("Table", "Table MultiSelect") and df.options not in children:
			children.append(df.options)

	return children


def get_file_name(table_name: str) -> str:
	"""Return the file a table is written to.

	A DocType name carries letters, numbers, spaces, underscores and hyphens only,
	so it is a file name as it stands. Substituting anything in it would be the one
	way two tables could end up in one file: `A_ B` and `A _B` both read `A___B`
	once the space becomes an underscore, however the underscore is escaped.
	"""
	return table_name + ".csv"


def get_rows(table: frappe._dict, export, fieldnames: list[str], start: int) -> list[dict]:
	"""
	Read one batch of a table, cut to the company and period of the export.

	A DocType without a company field (master data such as Customer or Account)
	is read in full on purpose. Cutting it would leave the ForeignKeys of the
	transactions pointing out of the data set.
	"""
	# `rows[fieldname]` and not `rows.fieldname`: frappe replaces `field()` with a
	# PseudoColumn and routes attribute access through __getattr__, where a field
	# named like a real attribute of the table would not reach.
	rows = frappe.qb.DocType(table.doctype)
	# permissions were checked per DocType in `check_export_permissions`
	query = frappe.qb.from_(rows).select(*(rows[fieldname] for fieldname in fieldnames))

	if table.parent_doctype:
		parent = frappe.qb.DocType(table.parent_doctype)
		query = (
			query.join(parent)
			.on(parent["name"] == rows["parent"])
			.where(rows["parenttype"] == table.parent_doctype)
		)
	else:
		parent = rows

	if table.company_field:
		query = query.where(parent[table.company_field] == export.company)

	if table.date_field and export.from_date:
		query = query.where(parent[table.date_field] >= export.from_date)

	if table.date_field and export.to_date:
		# exclusive next-day bound, or a Datetime late on the last day would be cut
		query = query.where(parent[table.date_field] < add_days(export.to_date, 1))

	return query.orderby(rows["name"]).limit(BATCH_SIZE).offset(start).run(as_dict=True)


def get_exported_names(doctype: str, export) -> list[str] | None:
	"""Return the names of the exported rows, or None if the whole table is exported."""
	table = get_table(doctype, export)
	if not table.company_field and not table.validity:
		return None

	# ponytail: the names are collected to filter the attachments by them. Turn it
	# into a subquery if a single DocType ever holds too many to pass along.
	names, start = [], 0
	while rows := get_rows(table, export, ["name"], start):
		names.extend(row["name"] for row in rows)
		start += BATCH_SIZE

	return names


def write_csv(archive: zipfile.ZipFile, table: frappe._dict, export) -> None:
	"""Stream one DocType into the archive, a batch of rows at a time."""
	fieldnames = [column.fieldname for column in table.columns]

	with archive.open(table.file_name, "w") as raw:
		writer, stream = get_writer(raw)
		writer.writerow(fieldnames)

		start = 0
		while True:
			rows = get_rows(table, export, fieldnames, start)
			if not rows:
				break

			writer.writerows([[escape(row[fieldname]) for fieldname in fieldnames] for row in rows])
			start += BATCH_SIZE

		stream.flush()
		stream.detach()


def write_attachments(archive: zipfile.ZipFile, doctype: str, names: list[str] | None) -> frappe._dict:
	"""
	Put the files attached to a DocType into the archive and describe them as a table.

	Arguments:
	names -- the exported rows, or None if the DocType is exported in full. A file
	         of a document outside the company or the period is none of the audit's
	         business and would point at a row that is not in the CSV.
	"""
	table_name = f"{doctype} Attachments"
	table = frappe._dict(
		doctype="File",
		name=table_name,
		description=_("Files attached to {0}").format(_(doctype)),
		file_name=get_file_name(table_name),
		columns=[
			frappe._dict(fieldname=fieldname, fieldtype=fieldtype)
			for fieldname, fieldtype in ATTACHMENT_COLUMNS
		],
		# `attached_to_name` is a Dynamic Link, this table holds one DocType only
		references=doctype,
	)
	fieldnames = [column.fieldname for column in table.columns]

	# The files have to go in before the CSV describing them: a ZIP archive
	# tolerates only one open writing handle at a time.
	filters = {"attached_to_doctype": doctype}
	if names is not None:
		filters["attached_to_name"] = ("in", names)

	rows = []
	for name in frappe.get_all("File", filters=filters, pluck="name", order_by="name"):
		# ponytail: one query per file, the document is needed for its path
		# anyway. Batch it if an export ever holds enough files to hurt.
		file = frappe.get_doc("File", name)
		# One directory per document, so the files of an invoice are found together.
		# A document name is not as tame as a DocType name: it may carry a slash and
		# would otherwise open a directory of its own, so it is percent encoded, which
		# is reversible and leaves an ordinary name untouched. Two files of one
		# document cannot collide, frappe keeps `file_name` unique.
		directory = quote(file.attached_to_name, safe="")
		path = f"attachments/{doctype}/{directory}/{file.file_name}"

		try:
			archive.write(file.get_full_path(), arcname=path)
		except (OSError, frappe.ValidationError):
			# a File whose content is gone must not lose us the whole export
			frappe.log_error(title=f"GDPdU Export: cannot read file {file.name}")
			continue

		values = frappe._dict(file.as_dict(), path=path)
		rows.append([escape(values.get(fieldname)) for fieldname in fieldnames])

	with archive.open(table.file_name, "w") as raw:
		writer, stream = get_writer(raw)
		writer.writerow(fieldnames)
		writer.writerows(rows)
		stream.flush()
		stream.detach()

	return table


def get_writer(raw) -> tuple[csv.writer, io.TextIOWrapper]:
	stream = io.TextIOWrapper(raw, encoding="utf-8", newline="")
	writer = csv.writer(
		stream,
		delimiter=";",
		quotechar='"',
		# the encapsulator is only for the fields that need it
		quoting=csv.QUOTE_MINIMAL,
		lineterminator="\r\n",
	)

	return writer, stream


def escape(value) -> str:
	"""
	Return a value that cannot be mistaken for a separator.

	Anlage 4 of the BMF letter demands unambiguous field and record separation
	criteria and forbids the text enclosure character as field content.
	"""
	if value is None:
		return ""

	return str(value).replace('"', "'").replace("\r", " ").replace("\n", " ")


def get_index_xml(tables: list[frappe._dict], export) -> bytes:
	"""Describe the delivered CSV files according to the description standard."""
	table_names = {table.name for table in tables}

	data_set = ET.Element("DataSet")
	# version of the data delivery, not of the description standard
	ET.SubElement(data_set, "Version").text = "1.0"

	if export.company:
		add_data_supplier(data_set, export)

	media = ET.SubElement(data_set, "Media")
	ET.SubElement(media, "Name").text = "ERPNext"

	for table in tables:
		add_table(media, table, table_names)

	ET.indent(data_set)
	xml = PROLOG + ET.tostring(data_set, encoding="unicode") + "\n"

	# a literal CR in the record delimiter would be normalized to LF by any XML
	# parser, so it has to be a character reference
	return xml.replace("\r\n", "&#13;&#10;").encode("utf-8")


def add_data_supplier(data_set: ET.Element, export) -> None:
	"""
	Name the business that hands the data over, it is the one obliged to do so.

	Child order is prescribed by the DTD and none of the three may be left out.
	`Comment` is free text. The published example names the kind of handover, its
	date and somebody to call back, so this one does the same.
	"""
	address = get_default_address("Company", export.company)
	city, country = frappe.db.get_value("Address", address, ["city", "country"]) if address else (None, None)

	# The remark is read by a German tax auditor, so it stays German whatever
	# language the user who ran the export works in.
	remark = [f"Datenträgerüberlassung nach § 147 Abs. 6 AO vom {formatdate(export.creation, 'dd.MM.yyyy')}"]
	contact = (
		frappe.db.get_value("User", export.owner, ["full_name", "phone", "mobile_no"], as_dict=True)
		if export.owner
		else None
	)
	if contact:
		remark.append(contact.full_name)
		if phone := (contact.mobile_no or contact.phone):
			remark.append(f"Tel: {phone}")

	supplier = ET.SubElement(data_set, "DataSupplier")
	ET.SubElement(supplier, "Name").text = export.company
	# the published example reads "Singen/Deutschland"
	ET.SubElement(supplier, "Location").text = "/".join(filter(None, (city, country)))
	ET.SubElement(supplier, "Comment").text = ", ".join(remark)


def add_table(media: ET.Element, table: frappe._dict, table_names: set[str]) -> None:
	"""Describe one CSV file. Child order is prescribed by the DTD."""
	element = ET.SubElement(media, "Table")
	# relative to the directory of index.xml, absolute URLs are not allowed
	ET.SubElement(element, "URL").text = table.file_name
	ET.SubElement(element, "Name").text = table.name
	ET.SubElement(element, "Description").text = table.description

	if table.validity:
		from_date, to_date = table.validity
		validity = ET.SubElement(element, "Validity")
		validity_range = ET.SubElement(validity, "Range")
		ET.SubElement(validity_range, "From").text = str(from_date or "")
		if to_date:
			ET.SubElement(validity_range, "To").text = str(to_date)
		ET.SubElement(validity, "Format").text = "YYYY-MM-DD"

	ET.SubElement(element, "UTF8")
	# Python writes numbers with a dot and without grouping
	ET.SubElement(element, "DecimalSymbol").text = "."
	ET.SubElement(element, "DigitGroupingSymbol").text = ","

	# skip the header record holding the field names
	row_range = ET.SubElement(element, "Range")
	ET.SubElement(row_range, "From").text = FIRST_DATA_ROW

	variable_length = ET.SubElement(element, "VariableLength")
	ET.SubElement(variable_length, "ColumnDelimiter").text = ";"
	ET.SubElement(variable_length, "RecordDelimiter").text = "\r\n"
	ET.SubElement(variable_length, "TextEncapsulator").text = '"'

	for column in table.columns:
		add_column(variable_length, column)

	# every ForeignKey comes after the last column
	for column in table.columns:
		references = table.references if column.fieldname == "attached_to_name" else column.options
		if references in table_names:
			add_foreign_key(variable_length, column.fieldname, references)


def add_column(variable_length: ET.Element, column: frappe._dict) -> None:
	"""Describe one column. Columns must be listed in the order of the file."""
	# `name` identifies the row and has to come before every VariableColumn
	tag = "VariablePrimaryKey" if column.fieldname == "name" else "VariableColumn"
	element = ET.SubElement(variable_length, tag)
	ET.SubElement(element, "Name").text = column.fieldname

	if column.fieldtype in NUMERIC_FIELDTYPES:
		numeric = ET.SubElement(element, "Numeric")
		ET.SubElement(numeric, "Accuracy").text = str(
			column.precision or NUMERIC_FIELDTYPES[column.fieldtype]
		)
	elif column.fieldtype in DATE_FIELDTYPES:
		date = ET.SubElement(element, "Date")
		ET.SubElement(date, "Format").text = DATE_FIELDTYPES[column.fieldtype]
	else:
		ET.SubElement(element, "AlphaNumeric")


def add_foreign_key(variable_length: ET.Element, fieldname: str, references: str) -> None:
	"""Declare a link between two tables, as required for machine evaluation."""
	foreign_key = ET.SubElement(variable_length, "ForeignKey")
	ET.SubElement(foreign_key, "Name").text = fieldname
	ET.SubElement(foreign_key, "References").text = references

	# the referenced column is always the primary key of the other table
	alias = ET.SubElement(foreign_key, "Alias")
	ET.SubElement(alias, "From").text = fieldname
	ET.SubElement(alias, "To").text = "name"
