from erpnext import get_default_company
import frappe


def all():
	check_some_customers()


def create_vat_id_check(
	customer: str, tax_id: str, company: str, company_tax_id: str
) -> str:
	"""Create a VAT ID check document and return its name."""
	doc = frappe.new_doc("VAT ID Check")
	doc.customer = customer
	doc.tax_id = tax_id
	doc.company = company
	doc.company_tax_id = company_tax_id
	doc.insert(ignore_permissions=True)

	return doc.name


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
		.select(customers.name, customers.tax_id)
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
	company_tax_id = None
	if company := get_default_company():
		company_tax_id = frappe.get_cached_value("Company", company, "tax_id")

	for customer, tax_id in get_customers():
		create_vat_id_check(customer, tax_id, company_tax_id)
