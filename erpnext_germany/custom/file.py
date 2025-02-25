from typing import TYPE_CHECKING

import frappe
from frappe import _

if TYPE_CHECKING:
	from frappe.core.doctype.file import File

APPLICABLE_DOCTYPES = (
	"Quotation",
	"Sales Order",
	"Delivery Note",
	"Sales Invoice",
	"Request for Quotation",
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Receipt",
	"Purchase Invoice",
)


def on_trash(doc: "File", method: str):
	if doc.attached_to_doctype not in APPLICABLE_DOCTYPES:
		# Not applicable
		return

	docstatus = frappe.db.get_value(
		doc.attached_to_doctype, doc.attached_to_name, "docstatus"
	)
	if docstatus != 1:
		# Not submitted
		return

	prevent_attachment_deletion = frappe.db.get_single_value(
		"ERPNext Germany Settings", "prevent_attachment_deletion"
	)
	if prevent_attachment_deletion:
		msg = _(
			"Attachments to the submitted record {0} of type {1} cannot be deleted."
		).format(doc.attached_to_name, _(doc.attached_to_doctype))

		if "System Manager" in frappe.get_roles():
			msg += " " + _("You can allow deletion via <b>ERPNext Germany Settings</b>.")

		frappe.throw(msg, title=_("Attachment Deletion Restricted"))
