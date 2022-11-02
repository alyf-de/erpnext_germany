__version__ = "0.0.3"

import frappe
from frappe import _

from erpnext import get_region


def create_transaction_log(doc, method):
	"""
	Appends the transaction to a chain of hashed logs for legal resons.
	Called on submit of Sales Invoice and Payment Entry.
	"""
	region = get_region()
	if region != "Germany":
		return

	data = str(doc.as_dict())

	frappe.get_doc(
		{
			"doctype": "Transaction Log",
			"reference_doctype": doc.doctype,
			"document_name": doc.name,
			"data": data,
		}
	).insert(ignore_permissions=True)
