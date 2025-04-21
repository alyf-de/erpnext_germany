import frappe


def execute():
	frappe.db.delete(
		"Property Setter",
		{
			"doc_type": "Employee",
			"field_name": "bank_ac_no",
			"property": "label",
			"value": "IBAN",
		},
	)

	frappe.db.delete(
		"Property Setter",
		{
			"doc_type": "Employee",
			"field_name": "ctc",
			"property": "hidden",
			"value": 1,
		},
	)
