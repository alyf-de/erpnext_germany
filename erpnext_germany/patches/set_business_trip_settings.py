import frappe

from erpnext_germany.erpnext_germany.doctype.business_trip.business_trip import (
	DEFAULT_EXPENSE_CLAIM_TYPE,
)


def execute():
	if not frappe.db.exists("Expense Claim Type", DEFAULT_EXPENSE_CLAIM_TYPE):
		return

	settings = frappe.get_single("Business Trip Settings")
	if not settings.expense_claim_type:
		settings.expense_claim_type = DEFAULT_EXPENSE_CLAIM_TYPE
	if not settings.expense_claim_type_car:
		settings.expense_claim_type_car = DEFAULT_EXPENSE_CLAIM_TYPE
	if not settings.mileage_allowance:
		settings.mileage_allowance = 0.3

	settings.save()
