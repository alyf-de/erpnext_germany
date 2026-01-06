# Copyright (c) 2024, ALYF GmbH and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BusinessTripRegion(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext_germany.erpnext_germany.doctype.business_trip_region_allowance.business_trip_region_allowance import (  # noqa: E501
			BusinessTripRegionAllowance,
		)

		allowances: DF.Table[BusinessTripRegionAllowance]
		disabled: DF.Check
		title: DF.Data | None
	# end: auto-generated types
	pass
