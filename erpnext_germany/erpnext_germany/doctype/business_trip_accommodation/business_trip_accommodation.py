# Copyright (c) 2024, ALYF GmbH and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BusinessTripAccommodation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		city: DF.Data
		from_date: DF.Date
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		receipt: DF.Attach | None
		to_date: DF.Date
	# end: auto-generated types
	pass
