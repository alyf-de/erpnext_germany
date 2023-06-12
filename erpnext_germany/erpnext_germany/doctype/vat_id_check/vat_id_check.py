# Copyright (c) 2023, ALYF GmbH and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from erpnext_germany.utils.eu_vat import check_vat_approx, parse_vat_id


class VATIDCheck(Document):
	def before_insert(self):
		requester_country_code, requester_vat_number = None, None
		if self.company_tax_id:
			requester_country_code, requester_vat_number = parse_vat_id(self.company_tax_id)
			self.company_tax_id = f"{requester_country_code}{requester_vat_number}"

		country_code, vat_number = parse_vat_id(self.tax_id)
		self.tax_id = f"{country_code}{vat_number}"
		result = check_vat_approx(
			country_code, vat_number, requester_country_code, requester_vat_number
		)
		self.is_valid = result.valid
		self.request_id = result.requestIdentifier
