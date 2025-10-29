# Copyright (c) 2025, ALYF GmbH and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BusinessTripOtherExpense(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date: DF.Date
		description: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		receipt: DF.Attach | None
	# end: auto-generated types
	pass
