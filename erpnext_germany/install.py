import contextlib
from csv import DictReader

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.customize_form.customize_form import (
	docfield_properties,
	doctype_properties,
)
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.exceptions import DuplicateEntryError
from frappe.utils.data import getdate

from .custom_fields import get_custom_fields
from .property_setters import get_property_setters


def after_install():
	make_custom_fields()
	make_property_setters()
	import_data()
	insert_custom_records()


def import_data():
	for doctype, filename, processor in (
		("Religious Denomination", "religious_denomination.csv", generic_csv_import),
		("Employee Health Insurance", "employee_health_insurance.csv", generic_csv_import),
		("Expense Claim Type", "expense_claim_type.csv", generic_csv_import),
		("Business Trip Region", "business_trip_region.csv", business_trip_region_csv_import),
	):
		if not frappe.db.exists("DocType", doctype):
			continue

		path = frappe.get_app_path("erpnext_germany", "data", filename)
		import_csv(doctype, path, processor)


def import_csv(doctype, path, processor):
	with open(path) as csvfile:
		reader = DictReader(csvfile)
		for row in reader:
			processor(doctype, row)


def generic_csv_import(doctype, row):
	"""Import a simple CSV row that corresponds to a single record without child tables."""
	if frappe.db.exists(doctype, row):
		# This doesn't catch all duplicates, because it expects all
		# fields to match, not (only) the primary key.
		return

	doc = frappe.new_doc(doctype)
	doc.update(row)
	with contextlib.suppress(DuplicateEntryError):
		doc.insert()


def business_trip_region_csv_import(doctype, row):
	"""Import a Business Trip Region CSV row that corresponds to a child table entry.

	If the parent record already exists, we append the new child table row to the existing record.
	If the parent record does not exist, we create a new record.
	"""
	existing_record = frappe.db.get_value(doctype, {"title": row["title"]})
	if existing_record:
		region = frappe.get_doc(doctype, existing_record)
	else:
		region = frappe.new_doc(doctype)
		region.title = row["title"]

	row_valid_from = getdate(row["valid_from"])

	# Find existing allowance with matching valid_from date
	existing_allowance = next((a for a in region.allowances if getdate(a.valid_from) == row_valid_from), None)

	if existing_allowance:
		# Update valid_to if source has it but existing doesn't
		if row["valid_to"] and not existing_allowance.valid_to:
			existing_allowance.valid_to = row["valid_to"]
			region.save()
	else:
		# Append new allowance
		region.append(
			"allowances",
			{
				"valid_from": row["valid_from"],
				"valid_to": row.get("valid_to"),
				"whole_day": row["whole_day"],
				"arrival_or_departure": row["arrival_or_departure"],
				"accommodation": row["accommodation"],
			},
		)
		region.save()


def make_property_setters():
	for doctypes, property_setters in get_property_setters().items():
		if isinstance(doctypes, str):
			doctypes = (doctypes,)

		for doctype in doctypes:
			for property_setter in property_setters:
				if property_setter[0]:
					for_doctype = False
					property_type = docfield_properties[property_setter[1]]
				else:
					for_doctype = True
					property_type = doctype_properties[property_setter[1]]

				make_property_setter(
					doctype=doctype,
					fieldname=property_setter[0],
					property=property_setter[1],
					value=property_setter[2],
					property_type=property_type,
					for_doctype=for_doctype,
				)


def make_custom_fields():
	create_custom_fields(get_custom_fields())


def insert_custom_records():
	for custom_record in frappe.get_hooks("germany_custom_records"):
		filters = custom_record.copy()
		# Clean up filters. They need to be a plain dict without nested dicts or lists.
		for key, value in custom_record.items():
			if isinstance(value, list | dict):
				del filters[key]

		if not frappe.db.exists(filters):
			frappe.get_doc(custom_record).insert(ignore_if_duplicate=True)
