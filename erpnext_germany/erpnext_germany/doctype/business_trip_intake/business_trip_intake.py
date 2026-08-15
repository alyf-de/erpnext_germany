# Copyright (c) 2026, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import add_days, fmt_money, get_datetime, getdate

from erpnext_germany.erpnext_germany.doctype.business_trip.business_trip import (
	ONE_DAY_TRIP_MINIMUM_HOURS,
)
from erpnext_germany.erpnext_germany.doctype.business_trip_distance.business_trip_distance import (
	get_distance,
)
from erpnext_germany.erpnext_germany.doctype.employee_vehicle.employee_vehicle import (
	PRIVATE,
	get_person_vehicles,
)

CAR_MODES = ("Car", "Car (private)", "Car (rental)")
PRIVATE_CAR = "Car (private)"
MEAL_FIELDS = (
	"breakfast_was_provided",
	"lunch_was_provided",
	"dinner_was_provided",
	"accommodation_was_provided",
)
DAY_START = "00:00:00"
DAY_END = "23:59:00"

DRAFT = "Draft"
QUESTIONS_OPEN = "Questions Open"
READY = "Ready"
TRANSFERRED = "Transferred"
DISCARDED = "Discarded"


class BusinessTripIntake(Document):
	"""The facts of a trip, as told by the traveller, before they become a Business Trip.

	An assistant fills this in from a sentence and answers the questions it gets back. The
	amounts are never calculated here either: `calculation_preview` is produced by running the
	real Business Trip logic on an unsaved document.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accommodation_was_provided: DF.Check
		breakfast_was_provided: DF.Check
		business_trip: DF.Link | None
		calculation_preview: DF.SmallText | None
		company: DF.Link | None
		cost_center: DF.Link | None
		create_trip: DF.Check
		customer: DF.Link | None
		destination: DF.Data | None
		dinner_was_provided: DF.Check
		distance: DF.Int
		employee: DF.Link | None
		employee_name: DF.Data | None
		employee_vehicle: DF.Link | None
		end_datetime: DF.Datetime | None
		lunch_was_provided: DF.Check
		meals_confirmed: DF.Check
		mode_of_transport: DF.Literal[
			"", "Car", "Car (private)", "Car (rental)", "Taxi", "Bus", "Train", "Airplane", "Public Transport"
		]
		open_questions: DF.SmallText | None
		origin: DF.Data | None
		project: DF.Link | None
		purpose: DF.Data | None
		raw_input: DF.SmallText | None
		region: DF.Link | None
		return_journey: DF.Check
		start_datetime: DF.Datetime | None
		status: DF.Literal["Draft", "Questions Open", "Ready", "Transferred", "Discarded"]
	# end: auto-generated types

	def validate(self):
		if self.status in (DISCARDED, TRANSFERRED):
			return

		self._missing_employee_for_company = False
		self.validate_dates()
		self.set_defaults()
		self.resolve_region()
		self.resolve_distance()
		self.resolve_vehicle()
		self.set_open_questions()
		self.set_preview()
		self.validate_ready_to_transfer()

	def validate_ready_to_transfer(self):
		"""Say why nothing was created, instead of ignoring the checkbox in silence."""
		if self.create_trip and not self.business_trip and self.status == QUESTIONS_OPEN:
			frappe.throw(
				questions_open_message(self.open_questions),
				title=_("Questions Open"),
			)

	def on_update(self):
		"""The chat has no way to call a method, so a checkbox is what triggers the transfer."""
		if self.create_trip and not self.business_trip and self.status == READY:
			self.create_business_trip()

	def validate_dates(self):
		if self.start_datetime and self.end_datetime:
			if get_datetime(self.end_datetime) < get_datetime(self.start_datetime):
				frappe.throw(_("The return must not be before the departure."))

	def set_defaults(self):
		if not self.employee:
			own = frappe.get_all("Employee", filters={"user_id": frappe.session.user}, pluck="name", limit=1)
			if own:
				self.employee = own[0]

		if not self.employee:
			return

		if not self.company:
			self.company = frappe.get_cached_value("Employee", self.employee, "company")
			return

		self.match_employee_to_company()

	def match_employee_to_company(self):
		"""Pick the employee record of the chosen company.

		Someone who works for several companies has one employee record per company, but the
		user id may only sit on one of them. Without this, an expense claim would be built for
		the wrong company and refused on submit.
		"""
		employee_name, employee_company = frappe.get_cached_value(
			"Employee", self.employee, ["employee_name", "company"]
		)

		if employee_company == self.company:
			return

		sibling = frappe.get_all(
			"Employee",
			filters={"employee_name": employee_name, "company": self.company, "status": "Active"},
			pluck="name",
			limit=1,
		)

		self.employee = sibling[0] if sibling else None
		self._missing_employee_for_company = not sibling

	def resolve_region(self):
		"""Derive the region from the destination, otherwise fall back to the default.

		A wrong region silently changes every rate, so the fallback is named in the preview
		instead of being applied quietly.
		"""
		if self.region or not self.destination:
			return

		matching = frappe.get_all(
			"Business Trip Region",
			filters={"title": self.destination, "disabled": 0},
			pluck="name",
			limit=1,
		)

		self.region = matching[0] if matching else get_default_region()

	def resolve_distance(self):
		if self.distance or self.mode_of_transport not in CAR_MODES:
			return

		if not (self.origin and self.destination):
			return

		known = get_distance(self.origin, self.destination, self.company)
		if known:
			self.distance = known["distance"]

	def resolve_vehicle(self):
		"""Preselect the vehicle when there is nothing to choose: only one, or a default."""
		self._private_vehicles = []

		if self.employee_vehicle or self.mode_of_transport != PRIVATE_CAR or not self.employee:
			return

		self._private_vehicles = get_person_vehicles(self.employee, ownership=PRIVATE, limit=2)

		if self._private_vehicles and (
			self._private_vehicles[0].is_default or len(self._private_vehicles) == 1
		):
			self.employee_vehicle = self._private_vehicles[0].name

	def set_open_questions(self):
		questions = self.get_open_questions()
		self.open_questions = "\n".join(
			f"{question['field']}: {question['question']}" for question in questions
		)
		self.status = QUESTIONS_OPEN if questions else READY

	def get_open_questions(self) -> list[dict]:
		"""Return what still has to be asked, in the order a person would ask it.

		Only genuinely missing facts are asked for. Anything that can be derived -- the region,
		a known route, the only vehicle -- is derived and shown in the preview instead.
		"""
		questions = []

		if not self.employee:
			if getattr(self, "_missing_employee_for_company", False):
				question = _("Who travelled for {0}? There is no employee record for them there.")
				questions.append({"field": "employee", "question": question.format(self.company)})
			else:
				questions.append(
					{"field": "employee", "question": _("Who travelled? No employee is linked to this user.")}
				)

		if not self.company:
			questions.append({"field": "company", "question": _("Which company is this trip for?")})

		if not self.purpose:
			questions.append(
				{
					"field": "purpose",
					"question": _("What was the reason for the trip? Required for tax purposes."),
				}
			)

		if not self.start_datetime or not self.end_datetime:
			questions.append(
				{
					"field": "start_datetime",
					"question": _("When exactly did the trip start and end, including the time of day?"),
				}
			)

		if not self.destination:
			questions.append({"field": "destination", "question": _("Where did the trip go?")})
		elif not self.region:
			questions.append(
				{
					"field": "region",
					"question": _(
						"Which region applies to {0}? Set a default region in Business Trip Settings for "
						"domestic travel."
					).format(self.destination),
				}
			)

		if not self.origin:
			questions.append({"field": "origin", "question": _("Where did the trip start?")})

		if not self.mode_of_transport:
			questions.append(
				{
					"field": "mode_of_transport",
					"question": _(
						"Own car, company car or train? A mileage allowance is only paid for a private car."
					),
				}
			)
		elif self.mode_of_transport in CAR_MODES and not self.distance:
			questions.append(
				{"field": "distance", "question": _("How many kilometers is the route, one way?")}
			)

		questions.extend(self.get_vehicle_question())

		if not self.meals_confirmed:
			questions.append(
				{
					"field": "meals_confirmed",
					"question": _(
						"Were any meals provided (hotel breakfast, business lunch)? Tick Meals Confirmed "
						"once answered."
					),
				}
			)

		questions.extend(self.get_duplicate_question())

		return questions

	def get_vehicle_question(self) -> list[dict]:
		"""Ask which car was driven -- but only if `resolve_vehicle` could not decide."""
		if self.employee_vehicle or self.mode_of_transport != PRIVATE_CAR or not self.employee:
			return []

		if not self._private_vehicles:
			return [
				{
					"field": "employee_vehicle",
					"question": _(
						"Which private vehicle was driven? None is recorded for this employee yet."
					),
				}
			]

		return [{"field": "employee_vehicle", "question": _("Which of your vehicles did you drive?")}]

	def get_duplicate_question(self) -> list[dict]:
		"""Warn about a trip that already covers these days, so no allowance is claimed twice."""
		if not (self.employee and self.start_datetime and self.end_datetime):
			return []

		overlapping = frappe.get_all(
			"Business Trip",
			filters={
				"employee": self.employee,
				"docstatus": ("<", 2),
				"from_date": ("<=", getdate(self.end_datetime)),
				"to_date": (">=", getdate(self.start_datetime)),
			},
			pluck="name",
			limit=1,
		)

		if not overlapping:
			return []

		return [
			{
				"field": "business_trip",
				"question": _("{0} already covers these days. Add to it, or is this a separate trip?").format(
					overlapping[0]
				),
			}
		]

	def set_preview(self):
		"""Show what the server would calculate -- run on an unsaved Business Trip."""
		if not self.can_build_trip():
			self.calculation_preview = None
			return

		trip = self.build_business_trip()
		trip.before_save()

		currency = frappe.get_cached_value("Company", self.company, "default_currency")
		lines = [
			_("Meal allowance: {0}").format(fmt_money(trip.total_allowance, currency=currency)),
			_("Mileage allowance: {0}").format(fmt_money(trip.total_mileage_allowance, currency=currency)),
			_("Total: {0}").format(
				fmt_money(trip.total_allowance + trip.total_mileage_allowance, currency=currency)
			),
		]
		lines.extend(self.get_preview_notes(trip))

		self.calculation_preview = "\n".join(lines)

	def get_preview_notes(self, trip) -> list[str]:
		notes = []

		if trip.from_date == trip.to_date and trip.allowances:
			if not trip.allowances[0].is_longer_than(ONE_DAY_TRIP_MINIMUM_HOURS):
				notes.append(
					_("No meal allowance: a one-day trip has to be longer than {0} hours.").format(
						ONE_DAY_TRIP_MINIMUM_HOURS
					)
				)

		if self.mode_of_transport in CAR_MODES and self.mode_of_transport != PRIVATE_CAR:
			notes.append(_("No mileage allowance: it is only paid for a private car."))

		if self.region and self.region == get_default_region() and self.destination:
			region_title = frappe.get_cached_value("Business Trip Region", self.region, "title")
			notes.append(_("Region {0} was assumed. Change it for a trip abroad.").format(region_title))

		return notes

	def can_build_trip(self) -> bool:
		return bool(
			self.employee and self.company and self.region and self.start_datetime and self.end_datetime
		)

	def build_business_trip(self):
		"""Build the Business Trip in memory, without saving it."""
		trip = frappe.new_doc("Business Trip")
		trip.update(
			{
				"employee": self.employee,
				"company": self.company,
				"title": self.purpose or self.destination,
				"from_date": getdate(self.start_datetime),
				"to_date": getdate(self.end_datetime),
				"region": self.region,
				"project": self.project,
				"cost_center": self.cost_center,
				"customer": self.customer,
			}
		)

		for row in build_allowance_rows(
			self.start_datetime, self.end_datetime, {field: self.get(field) for field in MEAL_FIELDS}
		):
			trip.append("allowances", row)

		for row in build_journey_rows(
			start=self.start_datetime,
			end=self.end_datetime,
			origin=self.origin,
			destination=self.destination,
			mode_of_transport=self.mode_of_transport,
			distance=self.distance,
			employee_vehicle=self.employee_vehicle,
			return_journey=self.return_journey,
		):
			trip.append("journeys", row)

		return trip

	@frappe.whitelist()
	def create_business_trip(self) -> str:
		"""Create the Business Trip as a draft. Never submits -- that stays with a person."""
		if self.business_trip:
			frappe.throw(
				_("{0} was already created from this intake.").format(self.business_trip),
				title=_("Already Transferred"),
			)

		if self.status == QUESTIONS_OPEN:
			frappe.throw(
				questions_open_message(self.open_questions),
				title=_("Questions Open"),
			)

		if not self.can_build_trip():
			frappe.throw(_("The trip is still incomplete."))

		trip = self.build_business_trip()
		trip.insert()

		self.db_set({"business_trip": trip.name, "status": TRANSFERRED, "create_trip": 0})

		return trip.name


@frappe.whitelist()
def create_business_trip_from_intake(intake: str) -> str:
	"""Create the Business Trip of an intake. The entry point for callers outside the Desk."""
	doc = frappe.get_doc("Business Trip Intake", intake)
	doc.check_permission("write")

	return doc.create_business_trip()


def questions_open_message(open_questions: str) -> str:
	"""Build the message outside the translation, so the list is not part of the msgid."""
	return f"{_('Please answer the open questions first:')}<br>{open_questions}"


def get_default_region() -> str | None:
	"""The region used when the destination does not name one, e.g. domestic travel."""
	return frappe.get_cached_doc("Business Trip Settings").default_region


def build_allowance_rows(start, end, meals: dict) -> list[dict]:
	"""Return one row per calendar day of the trip.

	Every meal flag is set explicitly: the child table defaults breakfast and accommodation to
	"provided", which would quietly cut the allowance for anyone who leaves them untouched.
	"""
	start = get_datetime(start)
	end = get_datetime(end)
	first_day = getdate(start)
	last_day = getdate(end)

	rows = []
	day = first_day
	while day <= last_day:
		row = {"date": day, **{field: int(bool(meals.get(field))) for field in MEAL_FIELDS}}

		if day == first_day and day == last_day:
			row.update({"whole_day": 0, "from_time": start.time(), "to_time": end.time()})
		elif day == first_day:
			row.update({"whole_day": 0, "from_time": start.time(), "to_time": DAY_END})
		elif day == last_day:
			row.update({"whole_day": 0, "from_time": DAY_START, "to_time": end.time()})
		else:
			row.update({"whole_day": 1, "from_time": DAY_START, "to_time": DAY_END})

		rows.append(row)
		day = add_days(day, 1)

	return rows


def build_journey_rows(
	start,
	end,
	origin: str | None,
	destination: str | None,
	mode_of_transport: str | None,
	distance: int,
	employee_vehicle: str | None,
	return_journey: bool,
) -> list[dict]:
	"""Return the journey there and, unless it was a one-way trip, the journey back."""
	if not (origin and destination and mode_of_transport):
		return []

	shared = {
		"mode_of_transport": mode_of_transport,
		"distance": distance or 0,
		"employee_vehicle": employee_vehicle,
	}

	rows = [{"date": getdate(start), "from": origin, "to": destination, **shared}]

	if return_journey:
		rows.append({"date": getdate(end), "from": destination, "to": origin, **shared})

	return rows
