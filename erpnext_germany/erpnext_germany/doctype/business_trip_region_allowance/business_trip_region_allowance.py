# Copyright (c) 2025, ALYF GmbH and contributors
# For license information, please see license.txt

<<<<<<< Updated upstream
# import frappe
# from frappe.model.document import Document


# class BusinessTripRegionAllowance(Document):
# 	  pass
=======
import frappe
from frappe.model.document import Document


class BusinessTripRegionAllowance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accommodation: DF.Currency
		arrival__departure: DF.Currency
		full_day: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		valid_till: DF.Date | None
	# end: auto-generated types
	pass
>>>>>>> Stashed changes
