# Copyright (c) 2024, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import get_installed_apps
from frappe.model.document import Document
from frappe.utils.data import fmt_money

DEFAULT_EXPENSE_CLAIM_TYPE = "Additional meal expenses"


class BusinessTrip(Document):
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

		region = frappe.get_doc("Business Trip Region", self.region)
		whole_day = region.whole_day or 0.0
		arrival_or_departure = region.arrival_or_departure or 0.0
		accomodation = region.accommodation or 0.0

		for allowance in self.allowances:
			amount = whole_day if allowance.whole_day else arrival_or_departure
			if allowance.breakfast_was_provided:
				amount -= whole_day * 0.2

			if allowance.lunch_was_provided:
				amount -= whole_day * 0.4

			if allowance.dinner_was_provided:
				amount -= whole_day * 0.4

			if not allowance.accommodation_was_provided:
				amount += accomodation

			allowance.amount = max(amount, 0.0)

	def reset_distance(self):
		for journey in self.journeys:
			if journey.mode_of_transport != "Car (private)":
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
		self.total_mileage_allowance = sum(journey.distance for journey in self.journeys) * mileage_allowance

	def before_submit(self):
		self.status = "Submitted"

	def on_submit(self):
		if not self.allowances and not self.journeys:
			return

		if "hrms" not in get_installed_apps():
			return

		settings = frappe.get_single("Business Trip Settings")
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
		if not allowance.accommodation_was_provided and frappe.db.get_value(
			"Business Trip Region", business_trip.region, "accommodation"
		):
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
