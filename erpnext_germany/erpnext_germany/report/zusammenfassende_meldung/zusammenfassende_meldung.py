# Copyright (c) 2025, ALYF GmbH and contributors
# For license information, please see license.txt


# Recapitulative Statement (Zusammenfassende Meldung)
# ===================================================
# Within the EU single market, certain cross-border supplies of goods and services
# can be exempt from VAT in the supplier's country, provided specific conditions
# are met. In these cases, VAT is instead due in the customer's country and must
# be reported and paid there by the customer.
#
# To ensure correct taxation in the customer's country, EU member states operate
# a comprehensive system for exchanging VAT-related data between their central
# authorities.
#
# Businesses that make such tax-exempt intra-Community supplies of goods or
# services are required to submit a recapitulative statement (RS) reporting
# these transactions.


import calendar
import csv
import json
import re
from datetime import date
from io import StringIO

import frappe
from frappe import _
from frappe.query_builder.functions import Round, Sum
from pypika.functions import Cast

SPEC_VERSION_HEADER = "#v3.0"
COLUMN_LABELS = {
	"tax_id": "Umsatzsteuer-Identifikationsnummer (USt-IdNr.)",
	"amount": "Summe (Euro)",
	"service_type": "Art der Leistung",
}


def execute(filters=None):
	from_date, to_date = get_date_range(filters.get("year"), filters.get("period"))
	return get_columns(), get_data(
		company=filters.get("company"),
		from_date=from_date,
		to_date=to_date,
	)


def get_date_range(year: int, period: str):
	"""Returns the start and end date for the given year and period."""
	if "-" in period:
		from_month, to_month = period.split("-")
	else:
		from_month = period
		to_month = period

	from_date = date(year, int(from_month), 1)
	to_date = date(year, int(to_month), calendar.monthrange(year, int(to_month))[1])

	return from_date, to_date


def get_columns():
	return [
		{
			"fieldname": "tax_id",
			"label": COLUMN_LABELS["tax_id"],
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "amount",
			"label": COLUMN_LABELS["amount"],
			"fieldtype": "Int",
			"width": 150,
		},
		{
			"fieldname": "service_type",  # [D, L, S]
			"label": COLUMN_LABELS["service_type"],
			"fieldtype": "Data",
			"width": 150,
		},
	]


def get_data(company: str, from_date: date, to_date: date):
	country_code = get_company_country_code(company)
	sales_invoice = frappe.qb.DocType("Sales Invoice")
	data = frappe.get_list(
		"Sales Invoice",
		filters=(
			("docstatus", "=", 1),
			("company", "=", company),
			("posting_date", "between", [from_date, to_date]),
			("tax_id", "is", "set"),
			("tax_id", "not like", f"{country_code}%"),  # Not the same country as the company
		),
		fields=[
			"tax_id",
			Cast(Round(Sum(sales_invoice.base_grand_total), 0), "SIGNED").as_("amount"),
		],
		group_by="tax_id",
	)

	for row in data:
		# drop all characters except alphanumeric, + and *
		row.tax_id = re.sub(r"[^a-zA-Z0-9+*]", "", row.tax_id)
		row.service_type = "S"  # TODO: Determine service type based on the invoice

	return data


def get_company_country_code(company: str) -> str:
	company_vat_id = frappe.db.get_value("Company", company, "tax_id")
	if not company_vat_id:
		frappe.throw(_("Please set a VAT ID / Tax ID in Company {0}").format(company))
	return company_vat_id[:2].upper()


def get_csv(data: list, columns: list):
	csvfile = StringIO()
	writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
	writer.writerow([column["label"] for column in columns])
	for row in data:
		writer.writerow([row[column["fieldname"]] for column in columns])

	return "\n".join([SPEC_VERSION_HEADER, csvfile.getvalue()])


@frappe.whitelist()
def download_zm_csv(filters: str):
	frappe.only_for(["Accounts User", "Accounts Manager"])

	filters = json.loads(filters)
	from_date, to_date = get_date_range(filters.get("year"), filters.get("period"))
	company = filters.get("company")
	data = get_data(company, from_date, to_date)
	columns = get_columns()

	frappe.response["filecontent"] = get_csv(data, columns)
	frappe.response["filename"] = "ZM.csv"
	frappe.response["type"] = "binary"
