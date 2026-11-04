# Copyright (c) 2025, ALYF GmbH and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ERPNextGermanySettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		prevent_gaps_in_transaction_naming: DF.Check
		warn_if_tax_category_missing: DF.Check
	# end: auto-generated types

	pass
