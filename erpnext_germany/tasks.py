import frappe
from erpnext import get_default_company
from frappe.database.database import savepoint
from frappe.query_builder import Case, DocType
from pypika import Interval
from pypika import functions as fn

from erpnext_germany.utils.eu_vat import parse_vat_id


def all():
	check_some_parties()


def get_customers(batch_size=4):
	"""Return a list of n customers who didn't have their VAT ID checked in the last 3 months."""
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
			& is_due(last_check)
		)
		.limit(batch_size)
		.run()
	)


def get_suppliers(batch_size=4):
	"""Return a list of n suppliers who didn't have their VAT ID checked in the last 3 months."""
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
			& is_due(last_check)
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
			).as_("creation"),
			fn.Max(vat_id_checks.creation).as_("last_attempt"),
		)
		.where(vat_id_checks.party_type == party_type)
		.groupby(vat_id_checks.party)
	)


def is_due(last_check):
	"""A party is due if it has no result from the last 3 months and no attempt from the last day.

	Checks without a result ("Service Unavailable", "Error", or a job that never finished)
	are retried after a day instead of on every run.
	"""
	return (last_check.creation.isnull() | (last_check.creation < fn.Now() - Interval(months=3))) & (
		last_check.last_attempt.isnull() | (last_check.last_attempt < fn.Now() - Interval(days=1))
	)


def check_some_parties():
	"""Check VAT IDs of customers who didn't have their VAT ID checked in the last 3 months."""
	company = get_default_company()
	requester_vat_id = get_requester_vat_id(company)

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


def get_requester_vat_id(company: str | None) -> str | None:
	"""Return the company's VAT ID, or None if it is missing or cannot be parsed.

	VIES accepts requests without a requester, they just don't get a request identifier.
	"""
	vat_id = frappe.get_cached_value("Company", company, "tax_id") if company else None
	if not vat_id:
		return None

	try:
		parse_vat_id(vat_id)
	except ValueError:
		return None

	return vat_id


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
