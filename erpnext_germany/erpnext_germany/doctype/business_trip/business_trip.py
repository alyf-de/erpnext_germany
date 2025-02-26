# Copyright (c) 2024, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import get_installed_apps

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
		whole_day = region.get("whole_day", 0.0)
		arrival_or_departure = region.get("arrival_or_departure", 0.0)
		accomodation = region.get("accomodation", 0.0)

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
		if not self.allowances:
			return

		if "hrms" not in get_installed_apps():
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

		settings = frappe.get_single("Business Trip Settings")
		for journey in self.journeys:
			if journey.mode_of_transport == "Car (private)":
				description = "{distance} * {mileage_allowance} von {from_place} nach {to_place} (Fahrt mit Privatauto)".format(
					distance=journey.get_formatted("distance"),
					mileage_allowance=settings.get_formatted("mileage_allowance"),
					from_place=getattr(journey, "from"),
					to_place=getattr(journey, "to"),
				)
				mileage_amount = journey.distance * (settings.mileage_allowance or 0)
				expense_claim.append(
					"expenses",
					{
						"expense_date": journey.date,
						"expense_type": settings.expense_claim_type_car or DEFAULT_EXPENSE_CLAIM_TYPE,
						"description": description,
						"amount": mileage_amount,
						"sanctioned_amount": mileage_amount,
						"project": self.project,
						"cost_center": self.cost_center,
					},
				)
			else:
				journey.distance = 0

		for allowance in self.allowances:
			description = "Ganztägig" if allowance.whole_day else "An-/Abreise"
			if not allowance.accommodation_was_provided and frappe.db.get_value(
				"Business Trip Region", self.region, "accommodation"
			):
				description += ", zzgl. Hotel"

			if allowance.breakfast_was_provided:
				description += ", abzügl. Frühstück"

			if allowance.lunch_was_provided:
				description += ", abzügl. Mittagessen"

			if allowance.dinner_was_provided:
				description += ", abzügl. Abendessen"

			expense_claim.append(
				"expenses",
				{
					"expense_date": allowance.date,
					"expense_type": settings.expense_claim_type or DEFAULT_EXPENSE_CLAIM_TYPE,
					"description": description,
					"amount": allowance.amount,
					"sanctioned_amount": allowance.amount,
					"project": self.project,
					"cost_center": self.cost_center,
				},
			)

		expense_claim.save()
