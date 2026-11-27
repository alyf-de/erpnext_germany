# Copyright (c) 2025, ALYF GmbH and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from erpnext_germany.erpnext_germany.doctype.accountant_export.accountant_export import validate_doctypes


class ERPNextGermanySettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext_germany.erpnext_germany.doctype.accountant_export_doctype.accountant_export_doctype import (  # noqa: E501
			AccountantExportDocType,
		)

		accountant_export_doctypes: DF.Table[AccountantExportDocType]
		prevent_gaps_in_transaction_naming: DF.Check
	# end: auto-generated types

	def validate(self):
		validate_doctypes(self.accountant_export_doctypes)
