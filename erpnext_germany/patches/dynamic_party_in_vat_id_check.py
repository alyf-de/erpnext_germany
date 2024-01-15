import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	"""Copy data to renamed fields in VAT ID Check.

	party_type -> "Customer",
	customer -> party,
	customer_vat_id -> party_vat_id,
	customer_address -> party_address,

	Add link to Supplier connections.
	Update link in Customer connections.
	"""
	dt = "VAT ID Check"

	frappe.db.sql("UPDATE `tabVAT ID Check` SET party_type = 'Customer'")

	rename_field(dt, "customer", "party")
	rename_field(dt, "customer_vat_id", "party_vat_id")
	rename_field(dt, "customer_address", "party_address")

	# Add link to Supplier connections
	frappe.get_doc(
		{
			"doctype": "DocType Link",
			"parent": "Supplier",
			"parentfield": "links",
			"parenttype": "Customize Form",
			"group": "Vendor Evaluation",
			"link_doctype": dt,
			"link_fieldname": "party",
			"custom": 1,
		}
	).insert(ignore_if_duplicate=True)

	# Update link in Customer connections
	customer_link = frappe.db.exists("DocType Link", {"link_doctype": dt, "link_fieldname": "customer"})
	if customer_link:
		frappe.db.set_value("DocType Link", customer_link, "link_fieldname", "party")
