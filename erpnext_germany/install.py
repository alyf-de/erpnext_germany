import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def after_install():
	custom_fields = frappe.get_hooks("germany_custom_fields")
	create_custom_fields(custom_fields)
	make_property_setters()


def make_property_setters():
	germany_property_setters = frappe.get_hooks("germany_property_setters")
	for doctypes, property_setters in germany_property_setters.items():
		if isinstance(doctypes, str):
			doctypes = (doctypes,)

		for doctype in doctypes:
			for property_setter in property_setters:
				for_doctype = True if not property_setter[0] else False
				make_property_setter(doctype, *property_setter, for_doctype)
