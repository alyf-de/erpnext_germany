import frappe
from erpnext import get_default_company
from frappe.database.database import savepoint
from frappe.query_builder import Case, DocType
from frappe.utils import add_to_date, now_datetime
from pypika import functions as fn

RECHECK_AFTER_MONTHS = 3
RETRY_AFTER_DAYS = 1


def all():
	check_some_parties()


def get_customers(batch_size=4):
	"""Return up to n customers that are due for a VAT ID check (see `due_condition`)."""
	customers = DocType("Customer")
	last_check = get_last_check_query("Customer")

	return (
		frappe.qb.from_(customers)
		.left_join(last_check)
		.on(customers.name == last_check.party)
		.select(
			fn.LiteralValue("'Customer'"),
			customers.name,
			customers.customer_name,
			customers.customer_primary_address,
			customers.tax_id,
		)
		.where(
			customers.tax_id.notnull()
			& (customers.tax_id != "")
			& (customers.disabled == 0)
			& due_condition(last_check)
		)
		.limit(batch_size)
		.run()
	)


def get_suppliers(batch_size=4):
	"""Return up to n suppliers that are due for a VAT ID check (see `due_condition`)."""
	suppliers = DocType("Supplier")
	last_check = get_last_check_query("Supplier")

	return (
		frappe.qb.from_(suppliers)
		.left_join(last_check)
		.on(suppliers.name == last_check.party)
		.select(
			fn.LiteralValue("'Supplier'"),
			suppliers.name,
			suppliers.supplier_name,
			suppliers.supplier_primary_address,
			suppliers.tax_id,
		)
		.where(
			suppliers.tax_id.notnull()
			& (suppliers.tax_id != "")
			& (suppliers.disabled == 0)
			& due_condition(last_check)
		)
		.limit(batch_size)
		.run()
	)


def get_last_check_query(party_type: str):
	vat_id_checks = DocType("VAT ID Check")
	return (
		frappe.qb.from_(vat_id_checks)
		.select(
			vat_id_checks.party,
			fn.Max(
				Case().when(vat_id_checks.status.isin(["Completed", "Invalid Input"]), vat_id_checks.creation)
			).as_("last_result"),
			fn.Max(vat_id_checks.creation).as_("last_attempt"),
		)
		.where(vat_id_checks.party_type == party_type)
		.groupby(vat_id_checks.party)
	)


def due_condition(last_check):
	"""Return the condition for a party without a recent result and without an attempt in the last day.

	Checks without a result ("Service Unavailable", "Error", or a job that never finished)
	are retried after a day instead of on every run. The limits are computed in Python, because
	`creation` is stored in the system time zone, which can differ from the database's.
	"""
	now = now_datetime()
	recheck_before = add_to_date(now, months=-RECHECK_AFTER_MONTHS)
	retry_before = add_to_date(now, days=-RETRY_AFTER_DAYS)

	return (last_check.last_result.isnull() | (last_check.last_result < recheck_before)) & (
		last_check.last_attempt.isnull() | (last_check.last_attempt < retry_before)
	)


def check_some_parties():
	"""Check the VAT IDs of some customers and suppliers that are due (see `due_condition`)."""
	requester_vat_id = None
	if company := get_default_company():
		requester_vat_id = frappe.get_cached_value("Company", company, "tax_id")

	for party_type, party, party_name, primary_address, vat_id in get_customers() + get_suppliers():
		frappe.db.savepoint("vat_id_check")
		try:
			create_vat_id_check(
				party_type, party, party_name, primary_address, vat_id, company, requester_vat_id
			)
		except Exception:
			# One failing party must not keep the others from being checked.
			frappe.db.rollback(save_point="vat_id_check")
			frappe.log_error("VAT ID Check Error", reference_doctype=party_type, reference_name=party)
			with savepoint(catch=Exception):
				record_failed_attempt(party_type, party, vat_id, company)
		else:
			frappe.db.release_savepoint("vat_id_check")


def create_vat_id_check(party_type, party, party_name, primary_address, vat_id, company, requester_vat_id):
	doc = frappe.new_doc("VAT ID Check")
	doc.party_type = party_type
	doc.party = party
	doc.trader_name = party_name
	doc.party_vat_id = vat_id
	doc.company = company
	doc.requester_vat_id = requester_vat_id
	if primary_address:
		address = frappe.get_doc("Address", primary_address)
		doc.trader_street = address.address_line1
		doc.trader_postcode = address.pincode
		doc.trader_city = address.city

	doc.flags.ignore_invalid_vat_id = True
	doc.insert(ignore_permissions=True)


def record_failed_attempt(party_type, party, vat_id, company):
	"""Store the attempt as "Error", so that the party waits a day instead of taking a slot on every run."""
	doc = frappe.new_doc("VAT ID Check")
	doc.party_type = party_type
	doc.party = party
	doc.party_vat_id = vat_id
	doc.company = company
	doc.status = "Error"
	doc.flags.ignore_invalid_vat_id = True
	doc.flags.skip_vies_request = True
	doc.insert(ignore_permissions=True)
