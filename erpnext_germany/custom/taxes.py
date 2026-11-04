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


def set_tax_exemption_reason(doc, event=None):
	"""Quotation / Sales Order / Sales Invoice validate: collect the exemption texts of the lines'
	Item Tax Templates (field added by eu_einvoice). Keeps the value fetched from the Sales Taxes
	and Charges Template when no line has a text.
	"""
	if not frappe.get_meta("Item Tax Template").has_field("vat_exemption_reason_text"):
		return

	templates = dict.fromkeys(row.item_tax_template for row in doc.items if row.item_tax_template)
	texts = dict.fromkeys(
		text
		for template in templates
		if (text := frappe.get_cached_value("Item Tax Template", template, "vat_exemption_reason_text"))
	)
	if texts:
		doc.tax_exemption_reason = "\n".join(texts)
