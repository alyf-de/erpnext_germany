from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	create_custom_fields(
		{
			("Quotation", "Sales Order", "Sales Invoice"): [
				{
					"label": "Tax Exemption Reason",
					"fieldtype": "Small Text",
					"fieldname": "tax_exemption_reason",
					"fetch_from": "taxes_and_charges.tax_exemption_reason",
					"depends_on": "tax_exemption_reason",
					"insert_after": "taxes_and_charges",
					"translatable": 0,
				},
			],
			"Sales Taxes and Charges Template": [
				{
					"label": "Tax Exemption Reason",
					"fieldtype": "Small Text",
					"fieldname": "tax_exemption_reason",
					"insert_after": "tax_category",
					"translatable": 0,
				}
			],
		}
	)