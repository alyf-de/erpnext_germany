import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	custom_fields = frappe.get_hooks("germany_custom_fields")
	create_custom_fields(custom_fields)
