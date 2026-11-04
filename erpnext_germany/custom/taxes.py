import frappe
from frappe import _


def warn_if_tax_rows_incomplete(doc, event=None):
	"""Item / Item Group validate: tax rows that cover some, but not all, of the Tax Categories
	used by the company's sales Tax Rules.

	For a missing category ERPNext falls back to the Item Group (and its parents). E.g. a single
	"Inland" row on a service item in a goods group makes EU lines use the group's goods template.
	"""
	categories_by_company = {}
	for row in doc.taxes:
		if row.tax_category:
			company = frappe.get_cached_value("Item Tax Template", row.item_tax_template, "company")
			categories_by_company.setdefault(company, set()).add(row.tax_category)

	for company, categories in categories_by_company.items():
		used_categories = set(
			frappe.get_all(
				"Tax Rule",
				filters={"company": company, "tax_type": "Sales", "tax_category": ("is", "set")},
				pluck="tax_category",
				distinct=True,
			)
		)
		if missing := used_categories - categories:
			frappe.msgprint(
				_("Tax rows for {0} lack the Tax Categories {1}, so the Item Group's rows apply.").format(
					company, ", ".join(sorted(missing))
				),
				indicator="orange",
				alert=True,
			)


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
