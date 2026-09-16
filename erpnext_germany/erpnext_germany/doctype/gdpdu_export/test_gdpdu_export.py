# Copyright (c) 2026, ALYF GmbH and Contributors
# See license.txt

import io
import xml.etree.ElementTree as ET
import zipfile

import frappe
from frappe.tests import IntegrationTestCase, set_user

from erpnext_germany.erpnext_germany.doctype.gdpdu_export.gdpdu_export import (
	FIRST_DATA_ROW,
	build_archive,
	get_index_xml,
	get_rows,
	get_table,
)

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]

# Child order is prescribed by the DTD, a reader rejects any other order.
TABLE_CHILDREN = [
	"URL",
	"Name",
	"Description",
	"UTF8",
	"DecimalSymbol",
	"DigitGroupingSymbol",
	"Range",
	"VariableLength",
]

COLUMN_TAGS = ("VariablePrimaryKey", "VariableColumn")


class IntegrationTestGDPdUExport(IntegrationTestCase):
	"""
	Integration tests for GDPdUExport.
	Use this class for testing interactions between multiple components.
	"""

	def setUp(self):
		self.export = frappe._dict(company=None, from_date=None, to_date=None)
		self.tables = [
			get_table("User", self.export),
			get_table("Has Role", self.export, parent="User"),
		]
		self.described = {
			table.findtext("Name"): table for table in ET.fromstring(get_index_xml(self.tables)).iter("Table")
		}

	def test_table_child_order(self):
		for name, table in self.described.items():
			self.assertEqual([child.tag for child in table], TABLE_CHILDREN, msg=name)

	def test_columns_match_the_file(self):
		"""The described columns have to be the written ones, in the same order."""
		for table in self.tables:
			described = [
				column.findtext("Name")
				for column in self.described[table.name].iter()
				if column.tag in COLUMN_TAGS
			]
			self.assertEqual(described, [column.fieldname for column in table.columns])

	def test_name_is_the_primary_key(self):
		"""Every VariablePrimaryKey has to precede the first VariableColumn."""
		for name, table in self.described.items():
			columns = [child for child in table.find("VariableLength") if child.tag in COLUMN_TAGS]
			self.assertEqual(columns[0].tag, "VariablePrimaryKey", msg=name)
			self.assertEqual(columns[0].findtext("Name"), "name", msg=name)
			self.assertNotIn("VariablePrimaryKey", [column.tag for column in columns[1:]], msg=name)

	def test_header_record_is_skipped(self):
		for name, table in self.described.items():
			self.assertEqual(table.find("Range").findtext("From"), FIRST_DATA_ROW, msg=name)

	def test_child_table_links_to_its_parent(self):
		links = {
			(key.findtext("Name"), key.findtext("References"))
			for key in self.described["Has Role"].iter("ForeignKey")
		}
		self.assertIn(("parent", "User"), links)

	def test_links_out_of_the_data_set_are_not_declared(self):
		"""A ForeignKey may only reference a table that is part of the export."""
		for name, table in self.described.items():
			for key in table.iter("ForeignKey"):
				self.assertIn(key.findtext("References"), set(self.described), msg=name)

	def test_passwords_are_not_exported(self):
		columns = [column.fieldname for column in self.tables[0].columns]
		self.assertNotIn("new_password", columns)
		self.assertNotIn("api_secret", columns)

	def test_permission_is_checked_per_doctype(self):
		export = frappe.get_doc(
			{"doctype": "GDPdU Export", "exported_doctypes": [{"exported_doctype": "User"}]}
		)
		with set_user("Guest"):
			self.assertRaises(frappe.PermissionError, export.validate)

	def test_attached_files_land_in_the_archive(self):
		"""A ZIP tolerates one open writing handle, so the files come before their CSV."""
		todo = frappe.get_doc({"doctype": "ToDo", "description": "GDPdU export test"}).insert()
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "gdpdu.txt",
				"content": "hello",
				"attached_to_doctype": "ToDo",
				"attached_to_name": todo.name,
				"is_private": 1,
			}
		).insert()

		export = frappe._dict(
			company=None,
			from_date=None,
			to_date=None,
			exported_doctypes=[frappe._dict(exported_doctype="ToDo", include_attached_files=1)],
		)
		names = zipfile.ZipFile(io.BytesIO(build_archive(export))).namelist()

		self.assertIn("ToDo.csv", names)
		self.assertIn("ToDo_Attachments.csv", names)
		self.assertIn("index.xml", names)
		self.assertIn("gdpdu-01-03-2019.dtd", names)
		self.assertTrue(
			any(name.startswith("attachments/ToDo/") for name in names),
			msg=f"no attachment in {names}",
		)

	def test_attachments_stay_inside_the_export(self):
		"""A file of a document that is not exported has no business in the archive."""

		def todo_with_file(date):
			todo = frappe.get_doc(
				{"doctype": "ToDo", "description": "GDPdU export test", "date": date}
			).insert()
			frappe.get_doc(
				{
					"doctype": "File",
					"file_name": f"gdpdu-{date}.txt",
					"content": date,
					"attached_to_doctype": "ToDo",
					"attached_to_name": todo.name,
					"is_private": 1,
				}
			).insert()

		todo_with_file("2024-06-01")
		todo_with_file("2025-06-01")

		export = frappe._dict(
			company=None,
			from_date="2024-01-01",
			to_date="2024-12-31",
			exported_doctypes=[frappe._dict(exported_doctype="ToDo", include_attached_files=1)],
		)
		names = zipfile.ZipFile(io.BytesIO(build_archive(export))).namelist()

		self.assertTrue(any(name.endswith("gdpdu-2024-06-01.txt") for name in names), msg=names)
		self.assertFalse(any(name.endswith("gdpdu-2025-06-01.txt") for name in names), msg=names)

	def test_the_last_day_of_the_period_is_complete(self):
		"""A Datetime late on the To Date still belongs to the period."""
		activity = frappe.get_doc(
			{
				"doctype": "Asset Activity",
				"asset": "_Test GDPdU Asset",
				"subject": "GDPdU export test",
				"date": "2024-12-31 23:30:00",
				"user": "Administrator",
			}
		).insert(ignore_links=True)

		export = frappe._dict(company=None, from_date="2024-01-01", to_date="2024-12-31")
		table = get_table("Asset Activity", export)
		self.assertEqual(table.date_field, "date")

		names = [row["name"] for row in get_rows(table, export, ["name"], 0)]
		self.assertIn(activity.name, names)

	def test_only_dated_doctypes_are_cut_by_the_period(self):
		"""Master data has to stay complete, or the ForeignKeys point out of the data set."""
		export = frappe._dict(company="_Test Company", from_date="2024-01-01", to_date="2024-12-31")

		dated = get_table("Sales Invoice", export)
		self.assertEqual(dated.date_field, "posting_date")
		self.assertEqual(dated.company_field, "company")
		self.assertEqual(dated.validity, ("2024-01-01", "2024-12-31"))

		master = get_table("Customer", export)
		self.assertIsNone(master.date_field)
		self.assertIsNone(master.validity)

	def test_a_child_table_is_filtered_by_its_parent(self):
		export = frappe._dict(company="_Test Company", from_date="2024-01-01", to_date="2024-12-31")
		child = get_table("Sales Invoice Item", export, parent="Sales Invoice")

		self.assertEqual(child.parent_doctype, "Sales Invoice")
		self.assertEqual(child.company_field, "company")
		self.assertEqual(child.date_field, "posting_date")

	def test_validity_is_described(self):
		export = frappe._dict(company="_Test Company", from_date="2024-01-01", to_date="2024-12-31")
		table = ET.fromstring(get_index_xml([get_table("Sales Invoice", export)])).find(".//Table")

		self.assertEqual(
			[child.tag for child in table],
			["URL", "Name", "Description", "Validity", *TABLE_CHILDREN[3:]],
		)
		self.assertEqual(table.find("Validity/Range").findtext("From"), "2024-01-01")
		self.assertEqual(table.find("Validity/Range").findtext("To"), "2024-12-31")

	def test_rows_are_readable_for_every_shape_of_table(self):
		"""frappe replaces Table.field(), so a wrong column accessor only fails at runtime."""
		export = frappe._dict(company=None, from_date="2024-01-01", to_date="2024-12-31")

		shapes = (
			("Sales Invoice", None),  # a parent with company and date
			("Sales Invoice Item", "Sales Invoice"),  # a child, filtered through its parent
			("Customer", None),  # master data, read in full
		)
		for doctype, parent in shapes:
			table = get_table(doctype, export, parent)
			fieldnames = [column.fieldname for column in table.columns]
			rows = get_rows(table, export, fieldnames, 0)

			self.assertIsInstance(rows, list, msg=doctype)
			if rows:
				self.assertEqual(set(rows[0]), set(fieldnames), msg=doctype)
