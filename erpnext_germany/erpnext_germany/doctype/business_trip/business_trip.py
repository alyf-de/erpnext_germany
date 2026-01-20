# Copyright (c) 2024, ALYF GmbH and contributors
# For license information, please see license.txt
from typing import TYPE_CHECKING

import frappe
from frappe import get_installed_apps
from frappe.model.document import Document
from frappe.utils.data import fmt_money

DEFAULT_EXPENSE_CLAIM_TYPE = "Additional meal expenses"

if TYPE_CHECKING:
	from erpnext_germany.erpnext_germany.doctype.business_trip_settings.business_trip_settings import (
		BusinessTripSettings,
	)


class BusinessTrip(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext_germany.erpnext_germany.doctype.business_trip_accommodation.business_trip_accommodation import (  # noqa: E501
			BusinessTripAccommodation,
		)
		from erpnext_germany.erpnext_germany.doctype.business_trip_allowance.business_trip_allowance import (
			BusinessTripAllowance,
		)
		from erpnext_germany.erpnext_germany.doctype.business_trip_journey.business_trip_journey import (
			BusinessTripJourney,
		)
		from erpnext_germany.erpnext_germany.doctype.business_trip_other_expense.business_trip_other_expense import (  # noqa: E501
			BusinessTripOtherExpense,
		)

		accommodations: DF.Table[BusinessTripAccommodation]
		allowances: DF.Table[BusinessTripAllowance]
		amended_from: DF.Link | None
		company: DF.Link | None
		cost_center: DF.Link | None
		currency: DF.Link | None
		customer: DF.Link | None
		employee: DF.Link
		employee_name: DF.Data | None
		from_date: DF.Date
		journeys: DF.Table[BusinessTripJourney]
		other_expenses: DF.Table[BusinessTripOtherExpense]
		project: DF.Link | None
		region: DF.Link
		status: DF.Literal["", "Submitted", "Approved", "Rejected", "Paid", "Billed"]
		title: DF.Data
		to_date: DF.Date
		total_allowance: DF.Currency
		total_mileage_allowance: DF.Currency
	# end: auto-generated types

	def before_save(self):
		self.reset_distance()
		self.set_regional_amount()
		self.set_whole_day_time()
		self.calculate_total()
		self.calculate_total_mileage_allowance()

	def validate(self):
		self.validate_from_to_dates("from_date", "to_date")

	def set_regional_amount(self):
		if not self.region:
			return

		for allowance in self.allowances:
			whole_day = 0.0
			arrival_or_departure = 0.0
			accommodation = 0.0

			allowance_rates = _get_allowance_rates(self.region, allowance.date)
			days_rates = allowance_rates[0] if allowance_rates else None

			if days_rates:
				whole_day = days_rates.whole_day
				arrival_or_departure = days_rates.arrival_or_departure
				accommodation = days_rates.accommodation

			amount = whole_day if allowance.whole_day else arrival_or_departure
			if allowance.breakfast_was_provided:
				amount -= whole_day * 0.2

			if allowance.lunch_was_provided:
				amount -= whole_day * 0.4

			if allowance.dinner_was_provided:
				amount -= whole_day * 0.4

			if not allowance.accommodation_was_provided:
				amount += accommodation

			allowance.amount = max(amount, 0.0)

	def reset_distance(self):
		for journey in self.journeys:
			if journey.mode_of_transport not in {"Car (private)", "Car (rental)", "Car"}:
				journey.distance = 0

	def set_whole_day_time(self):
		for allowance in self.allowances:
			if allowance.whole_day:
				allowance.from_time = "00:00"
				allowance.to_time = "23:59"

	def calculate_total(self):
		self.total_allowance = sum(allowance.amount for allowance in self.allowances)

	def calculate_total_mileage_allowance(self):
		mileage_allowance = frappe.db.get_single_value("Business Trip Settings", "mileage_allowance") or 0
		self.total_mileage_allowance = (
			sum(journey.distance for journey in self.journeys if journey.mode_of_transport == "Car (private)")
			* mileage_allowance
		)

	def before_submit(self):
		self.status = "Submitted"

	def on_submit(self):
		if not self.allowances and not self.journeys:
			return

		if "hrms" not in get_installed_apps():
			return

		settings: BusinessTripSettings = frappe.get_single("Business Trip Settings")
		expenses = get_mileage_allowances(
			self,
			expense_claim_type=settings.expense_claim_type_car or DEFAULT_EXPENSE_CLAIM_TYPE,
			mileage_allowance=settings.mileage_allowance or 0.0,
		)
		expenses.extend(get_meal_expenses(self, settings.expense_claim_type or DEFAULT_EXPENSE_CLAIM_TYPE))

		if not expenses:
			return

		# Create Expense Claim for Car (private) and Allowance
		expense_claim = frappe.new_doc("Expense Claim")
		expense_claim.update(
			{
				"employee": self.employee,
				"company": self.company,
				"posting_date": frappe.utils.today(),
				"business_trip": self.name,
				"project": self.project,
				"cost_center": self.cost_center,
			}
		)
		expense_claim.extend("expenses", expenses)
		expense_claim.save()


def get_mileage_allowances(
	business_trip: BusinessTrip, expense_claim_type: str, mileage_allowance: float
) -> list[dict]:
	"""Return a list of expense claim rows for mileage allowances."""
	expenses = []
	for journey in business_trip.journeys:
		if journey.mode_of_transport != "Car (private)":
			continue

		description = (
			"{distance} * {mileage_allowance} von {from_place} nach {to_place} (Fahrt mit Privatauto)".format(
				distance=journey.get_formatted("distance"),
				mileage_allowance=fmt_money(mileage_allowance),
				from_place=getattr(journey, "from"),
				to_place=journey.to,
			)
		)
		mileage_amount = journey.distance * mileage_allowance
		expenses.append(
			{
				"expense_date": journey.date,
				"expense_type": expense_claim_type,
				"description": description,
				"amount": mileage_amount,
				"sanctioned_amount": mileage_amount,
				"project": business_trip.project,
				"cost_center": business_trip.cost_center,
			},
		)

	return expenses


def get_meal_expenses(business_trip: BusinessTrip, expense_claim_type: str) -> list[dict]:
	"""Return a list of expense claim rows for meal expenses"""
	expenses = []
	for allowance in business_trip.allowances:
		description = "Ganztägig" if allowance.whole_day else "An-/Abreise"

		accommodation = 0.0
		allowance_rates = _get_allowance_rates(business_trip.region, allowance.date)
		if allowance_rates:
			accommodation = allowance_rates[0].accommodation

		if not allowance.accommodation_was_provided and accommodation:
			description += ", zzgl. Hotel"

		if allowance.breakfast_was_provided:
			description += ", abzügl. Frühstück"

		if allowance.lunch_was_provided:
			description += ", abzügl. Mittagessen"

		if allowance.dinner_was_provided:
			description += ", abzügl. Abendessen"

		expenses.append(
			{
				"expense_date": allowance.date,
				"expense_type": expense_claim_type,
				"description": description,
				"amount": allowance.amount,
				"sanctioned_amount": allowance.amount,
				"project": business_trip.project,
				"cost_center": business_trip.cost_center,
			},
		)

	return expenses


@frappe.whitelist()
def get_processing_details(business_trip: str):
	"""Get linked Expense Claims and Purchase Invoices for the Business Trip"""
	frappe.has_permission("Business Trip", doc=business_trip, throw=True)

	# Get Expense Claims
	expense_claims = frappe.get_all(
		"Expense Claim",
		filters={
			"business_trip": business_trip,
			"docstatus": ["!=", 2],
		},
		fields=["name", "grand_total", "status"],
	)

	# Get Purchase Invoices
	purchase_invoices = frappe.get_all(
		"Purchase Invoice",
		filters={
			"business_trip": business_trip,
			"docstatus": ["!=", 2],
		},
		fields=["name", "grand_total", "status", "supplier_name"],
	)

	# Combine and add doctype field
	combined_records = []

	for claim in expense_claims:
		claim["doctype"] = "Expense Claim"
		combined_records.append(claim)

	for invoice in purchase_invoices:
		invoice["doctype"] = "Purchase Invoice"
		combined_records.append(invoice)

	return combined_records


def _get_allowance_rates(region: str, date: str):
	"""Return allowance rates for a region valid on or before a date.

	Results are ordered by `valid_from` in descending order so the most recent applicable rate is first.
	"""
	return frappe.get_all(
		"Business Trip Region Allowance",
		filters={
			"parent": region,
			"valid_from": ["<=", date],
		},
		order_by="valid_from DESC",
		fields=["valid_from", "whole_day", "arrival_or_departure", "accommodation"],
	)
