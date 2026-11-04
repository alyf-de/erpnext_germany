import frappe
from frappe import _


def warn_if_tax_category_missing(doc, event=None):
	"""Customer / Supplier / Sales and Purchase Invoice validate: without a Tax Category, no Tax Rule
	and no Item Group row that is bound to a Tax Category matches, so the invoice gets no taxes.

	Opt-in via ERPNext Germany Settings; the tax setup turns it on.
	"""
	if doc.tax_category or not frappe.db.get_single_value(
		"ERPNext Germany Settings", "warn_if_tax_category_missing"
	):
		return

	frappe.msgprint(
		_("No Tax Category is set, so taxes may not be applied automatically."),
		indicator="orange",
		alert=True,
	)
