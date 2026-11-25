# Copyright (c) 2023, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from tenacity import RetryError

from erpnext_germany.utils.eu_vat import check_vat_approx, parse_vat_id


class VATIDCheck(Document):
	def before_insert(self):
		if not self.flags.skip_vies_request:
			self.status = "Planned"

		if self.requester_vat_id:
			try:
				requester_country_code, requester_vat_number = parse_vat_id(self.requester_vat_id)
			except ValueError:
				if not self.flags.ignore_invalid_vat_id:
					frappe.throw(
						_("The VAT ID in {0} is invalid.").format(_(self.meta.get_label("requester_vat_id")))
					)

				# VIES accepts requests without a requester, they just get no request identifier.
				self.requester_vat_id = None
			else:
				self.requester_vat_id = f"{requester_country_code}{requester_vat_number}"

		try:
			country_code, vat_number = parse_vat_id(self.party_vat_id)
		except ValueError:
			if not self.flags.ignore_invalid_vat_id:
				frappe.throw(
					_("The VAT ID in {0} is invalid.").format(_(self.meta.get_label("party_vat_id")))
				)

			# Record the result, so that the scheduler doesn't pick this party again right away.
			self.status = "Invalid Input"
			self.is_valid = 0
			self.flags.skip_vies_request = True
			# A blank ID (e.g. a non-breaking space) would fail the mandatory check and not be recorded.
			self.flags.ignore_mandatory = True
			return

		self.party_vat_id = f"{country_code}{vat_number}"

	def after_insert(self):
		if self.flags.skip_vies_request:
			return

		frappe.enqueue(
			run_check,
			doc=self,
			queue="long",
			now=frappe.conf.developer_mode or frappe.in_test,
			enqueue_after_commit=True,
		)


def run_check(doc: VATIDCheck):
	# Rolling back to a savepoint keeps the after-commit job of a check that is gone.
	if not frappe.db.exists("VAT ID Check", doc.name):
		return

	doc.db_set("status", "Running", notify=True)
	requester_country_code, requester_vat_number = None, None
	if doc.requester_vat_id:
		try:
			requester_country_code, requester_vat_number = parse_vat_id(doc.requester_vat_id)
		except ValueError:
			doc.db_set({"status": "Invalid Input", "is_valid": False}, notify=True)
			return

	try:
		country_code, vat_number = parse_vat_id(doc.party_vat_id)
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
			requester_vat_number=requester_vat_number,
		)
	except (RetryError, ConnectionError):
		doc.db_set("status", "Service Unavailable", notify=True)
		return
	except Exception as e:
		if hasattr(e, "message") and e.message.upper() == "INVALID_INPUT":
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
