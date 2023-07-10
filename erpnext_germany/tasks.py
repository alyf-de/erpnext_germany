from erpnext import get_default_company
import frappe


def all():
	check_some_customers()


def get_customers(n=4):
	"""Return a list of n customers who didn't have their VAT ID checked in the last 3 months."""
	from pypika import functions as fn, Interval
	from frappe.query_builder import DocType

	customers = DocType("Customer")
	vat_id_checks = DocType("VAT ID Check")
	last_check = (
		frappe.qb.from_(vat_id_checks)
		.select(
			vat_id_checks.customer,
			fn.Max(vat_id_checks.creation).as_("creation"),
		)
		.groupby(vat_id_checks.customer)
	)

	return (
		frappe.qb.from_(customers)
		.left_join(last_check)
		.on(customers.name == last_check.customer)
		.select(
			customers.name,
			customers.customer_name,
			customers.customer_primary_address,
			customers.tax_id
		)
		.where(
			customers.tax_id.notnull()
			& (customers.disabled == 0)
			& (
				last_check.creation.isnull()
				| (last_check.creation < fn.Now() - Interval(months=3))
			)
		)
		.limit(n)
		.run()
	)


def check_some_customers():
	"""Check VAT IDs of customers who didn't have their VAT ID checked in the last 3 months."""
	requester_vat_id = None
	if company := get_default_company():
		requester_vat_id = frappe.get_cached_value("Company", company, "tax_id")

	for customer, customer_name, primary_address, vat_id in get_customers():
		doc = frappe.new_doc("VAT ID Check")
		doc.customer = customer
		doc.trader_name = customer_name
		doc.customer_vat_id = vat_id
		doc.company = company
		doc.requester_vat_id = requester_vat_id
		if primary_address:
			address = frappe.get_doc("Address", primary_address)
			doc.trader_street = address.address_line1
			doc.trader_postcode = address.pincode
			doc.trader_city = address.city

		doc.insert(ignore_permissions=True)
