# Copyright (c) 2023, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext_germany.utils.eu_vat import check_vat_approx, parse_vat_id

from tenacity import RetryError


class VATIDCheck(Document):
	def before_insert(self):
		if self.requester_vat_id:
			requester_country_code, requester_vat_number = parse_vat_id(
				self.requester_vat_id
			)
			self.requester_vat_id = f"{requester_country_code}{requester_vat_number}"

		country_code, vat_number = parse_vat_id(self.customer_vat_id)
		self.customer_vat_id = f"{country_code}{vat_number}"

	def after_insert(self):
		frappe.enqueue(
			run_check,
			doc=self,
			queue="long",
			now=frappe.conf.developer_mode or frappe.flags.in_test,
		)


def run_check(doc: VATIDCheck):
	doc.db_set("status", "Running", notify=True)
	requester_country_code, requester_vat_number = None, None
	if doc.requester_vat_id:
		requester_country_code, requester_vat_number = parse_vat_id(doc.requester_vat_id)

	country_code, vat_number = parse_vat_id(doc.customer_vat_id)
	try:
		result = check_vat_approx(
			country_code=country_code,
			vat_number=vat_number,
			trader_name=doc.trader_name,
			trader_street=doc.trader_street,
			trader_postcode=doc.trader_postcode,
			trader_city=doc.trader_city,
			requester_country_code=requester_country_code,
			requester_vat_number=requester_vat_number
		)
	except RetryError:
		doc.db_set("status", "Service Unavailable", notify=True)
		return

	doc.db_set(
		{
			"status": "Completed",
			"is_valid": result.valid,
			"request_id": result.requestIdentifier,
			"trader_name_match": result.traderNameMatch,
			"trader_street_match": result.traderStreetMatch,
			"trader_postcode_match": result.traderPostcodeMatch,
			"trader_city_match": result.traderCityMatch,
		},
		notify=True,
	)
