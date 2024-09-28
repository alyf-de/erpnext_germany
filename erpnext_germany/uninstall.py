import frappe
from .custom_fields import get_custom_fields


def before_uninstall():
	remove_custom_fields()
	remove_property_setters()
	remove_custom_records()


def remove_custom_fields():
	print("* removing custom fields...")
	for doctypes, custom_fields in get_custom_fields().items():
		if isinstance(doctypes, str):
			doctypes = (doctypes,)

		for doctype in doctypes:
			for cf in custom_fields:
				frappe.db.delete(
					"Custom Field",
					{
						"dt": doctype,
						"fieldname": cf.get("fieldname"),
					}
				)


def remove_property_setters():
	print("* removing property setters...")
	for doctype, property_setters in frappe.get_hooks("germany_property_setters").items():
		for ps in property_setters:
			frappe.db.delete(
				"Property Setter",
				{
					"doc_type": doctype,
					"property": ps[0],
					"value": ps[-2]
				}
			)


def remove_custom_records():
	print("* removing custom records...")
	for record in frappe.get_hooks("germany_custom_records"):
		doctype = record.pop("doctype")
		frappe.db.delete(doctype, record)
