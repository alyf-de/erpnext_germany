import frappe
from frappe import _
from erpnext.controllers.selling_controller import SellingController


def on_trash(doc: SellingController, event: str = None) -> None:
	if doc.flags.ignore_validate:
		return

	if is_not_latest(doc.doctype, doc.name, doc.creation, doc.company):
		frappe.throw(
			msg=_(
				"Only the most recent {0} can be deleted in order to avoid gaps in numbering."
			).format(_(doc.doctype)),
			title=_("Cannot delete this transaction"),
		)


def is_not_latest(doctype, name, creation, company):
	return frappe.db.exists(
		doctype,
		{
			"creation": (">", creation),
			"name": ("!=", name),
			"company": ("=", company),
		},
	)
