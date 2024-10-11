import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import get_installed_apps

def _(message: str) -> str:
	return message
  
def get_custom_fields():
	custom_fields = {}
    if "hrms" in get_installed_apps():
        custom_fields["Expense Claim"] = [
            {
                "fieldtype": "Link",
                "fieldname": "business_trip",
                "label": _("Business Trip"),
                "options": "Business Trip",
                "insert_after": "company",
            },
        ]

    return custom_fields

def execute():
    create_custom_fields(get_custom_fields())
