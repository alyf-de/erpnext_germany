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
		try:
			requester_country_code, requester_vat_number = parse_vat_id(doc.requester_vat_id)
		except ValueError:
			doc.db_set({"status": "Invalid Input", "is_valid": False}, notify=True)
			return

	try:
		country_code, vat_number = parse_vat_id(doc.customer_vat_id)
	except ValueError:
		doc.db_set({"status": "Invalid Input", "is_valid": False}, notify=True)
		return

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
	except Exception as e:
		if e.message.upper() == "INVALID_INPUT":
			doc.db_set({"status": "Invalid Input", "is_valid": False}, notify=True)
		else:
			doc.db_set({"status": "Error"}, notify=True)
			frappe.log_error("VAT ID Check Error", frappe.get_traceback())

		return

	doc.db_set(
		{
			"status": "Completed",
			"is_valid": result.valid,
			"trader_name_match": bool(result.traderNameMatch),
			"trader_street_match": bool(result.traderStreetMatch),
			"trader_postcode_match": bool(result.traderPostcodeMatch),
			"trader_city_match": bool(result.traderCityMatch),
			"request_id": result.requestIdentifier,
			"actual_trader_name": result.traderName,
			"actual_trader_address": result.traderAddress,
		},
		notify=True,
	)
