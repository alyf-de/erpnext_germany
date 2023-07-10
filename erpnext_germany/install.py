from csv import DictReader

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from erpnext_germany.holiday_list.holiday_list import update_holiday_lists


def after_install():
	custom_fields = frappe.get_hooks("germany_custom_fields")
	create_custom_fields(custom_fields)
	make_property_setters()

	if "hrms" in frappe.get_installed_apps():
		import_data()
		update_holiday_lists()


def import_data():
	for doctype, filename in (
		("Religious Denomination", "religious_denomination.csv"),
		("Employee Health Insurance", "employee_health_insurance.csv"),
	):
		if not frappe.db.exists("DocType", doctype):
			continue

		path = frappe.get_app_path("erpnext_germany", "data", filename)
		import_csv(doctype, path)


def import_csv(doctype, path):
	with open(path) as csvfile:
		reader = DictReader(csvfile)
		for row in reader:
			if frappe.db.exists(doctype, row):
				continue

			doc = frappe.new_doc(doctype)
			doc.update(row)
			doc.insert()


def make_property_setters():
	germany_property_setters = frappe.get_hooks("germany_property_setters")
	for doctypes, property_setters in germany_property_setters.items():
		if isinstance(doctypes, str):
			doctypes = (doctypes,)

		for doctype in doctypes:
			for property_setter in property_setters:
				for_doctype = not property_setter[0]
				make_property_setter(doctype, *property_setter, for_doctype)
