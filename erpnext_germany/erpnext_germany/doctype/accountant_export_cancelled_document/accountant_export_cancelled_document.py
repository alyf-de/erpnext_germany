# Copyright (c) 2026, ALYF GmbH and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AccountantExportCancelledDocument(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		previous_accountant_export: DF.Link | None
		reference_doctype: DF.Link
		reference_name: DF.Data
	# end: auto-generated types

	pass
