from erpnext_germany.custom_fields import _
from frappe import get_installed_apps
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	if "hrms" in get_installed_apps():
		create_custom_fields(
			{
				"Expense Claim": [
					{
						"fieldtype": "Link",
						"fieldname": "business_trip",
						"label": _("Business Trip"),
						"options": "Business Trip",
						"insert_after": "company",
					},
				]
			}
		)
