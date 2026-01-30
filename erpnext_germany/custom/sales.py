import frappe
from erpnext.controllers.selling_controller import SellingController
from frappe import _


def on_trash(doc: SellingController, event: str | None = None) -> None:
	if doc.flags.ignore_validate:
		return

	if not frappe.db.get_single_value("ERPNext Germany Settings", "prevent_gaps_in_transaction_naming"):
		return

	if is_not_latest_in_series(
		doc.doctype, doc.name, doc.creation, doc.company, getattr(doc, "naming_series", None)
	):
		frappe.throw(
			msg=_(
				"Only the most recent {0} within the same series can be deleted to avoid gaps in numbering."
			).format(_(doc.doctype)),
			title=_("Cannot delete this transaction"),
		)


def is_not_latest_in_series(doctype, name, creation, company, naming_series: str | None = None):
	"""Check if the document is not the latest within its naming series and company."""
	if not naming_series:
		# find a newer doc with the same company
		return frappe.db.exists(
			doctype,
			{
				"creation": (">", creation),
				"name": ("!=", name),
				"company": company,
			},
		)

	# find a newer doc with the same naming series and company
	return frappe.db.exists(
		doctype,
		{
			"creation": (">", creation),
			"name": ("!=", name),
			"company": company,
			"naming_series": naming_series,
		},
	)
