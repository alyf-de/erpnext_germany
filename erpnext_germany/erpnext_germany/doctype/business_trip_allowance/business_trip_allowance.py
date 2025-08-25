# Copyright (c) 2024, ALYF GmbH and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BusinessTripAllowance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accommodation_was_provided: DF.Check
		amount: DF.Currency
		breakfast_was_provided: DF.Check
		date: DF.Date
		dinner_was_provided: DF.Check
		from_time: DF.Time | None
		lunch_was_provided: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		to_time: DF.Time | None
		whole_day: DF.Check
	# end: auto-generated types
	pass
