# Copyright (c) 2025, ALYF GmbH and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BusinessTripRegionAllowance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accommodation: DF.Currency
		arrival_or_departure: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		valid_from: DF.Date
		whole_day: DF.Currency
	# end: auto-generated types
	pass
