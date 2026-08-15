# Copyright (c) 2026, ALYF GmbH and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_germany.erpnext_germany.doctype.business_trip_intake.business_trip_intake import (
	build_allowance_rows,
	build_journey_rows,
)

NO_MEALS = {
	"breakfast_was_provided": 0,
	"lunch_was_provided": 0,
	"dinner_was_provided": 0,
	"accommodation_was_provided": 0,
}


class TestBuildAllowanceRows(FrappeTestCase):
	def test_one_day_trip_keeps_the_actual_times(self):
		rows = build_allowance_rows("2026-08-13 08:00:00", "2026-08-13 17:00:00", NO_MEALS)

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["whole_day"], 0)
		self.assertEqual(str(rows[0]["from_time"]), "08:00:00")
		self.assertEqual(str(rows[0]["to_time"]), "17:00:00")

	def test_two_day_trip_has_arrival_and_departure_only(self):
		rows = build_allowance_rows("2026-08-13 08:00:00", "2026-08-14 17:00:00", NO_MEALS)

		self.assertEqual(len(rows), 2)
		self.assertEqual([row["whole_day"] for row in rows], [0, 0])
		self.assertEqual(str(rows[0]["from_time"]), "08:00:00")
		self.assertEqual(rows[0]["to_time"], "23:59:00")
		self.assertEqual(rows[1]["from_time"], "00:00:00")
		self.assertEqual(str(rows[1]["to_time"]), "17:00:00")

	def test_middle_days_are_whole_days(self):
		rows = build_allowance_rows("2026-08-13 08:00:00", "2026-08-16 17:00:00", NO_MEALS)

		self.assertEqual(len(rows), 4)
		self.assertEqual([row["whole_day"] for row in rows], [0, 1, 1, 0])

	def test_every_meal_flag_is_set_explicitly(self):
		# The child table defaults breakfast and accommodation to 1; leaving them out would
		# silently cut the allowance.
		rows = build_allowance_rows("2026-08-13 08:00:00", "2026-08-13 17:00:00", {})

		for field in NO_MEALS:
			self.assertEqual(rows[0][field], 0, field)

	def test_provided_meals_are_carried_to_every_day(self):
		rows = build_allowance_rows(
			"2026-08-13 08:00:00", "2026-08-14 17:00:00", {**NO_MEALS, "breakfast_was_provided": 1}
		)

		self.assertEqual([row["breakfast_was_provided"] for row in rows], [1, 1])

	def test_dates_are_consecutive(self):
		rows = build_allowance_rows("2026-08-13 08:00:00", "2026-08-15 17:00:00", NO_MEALS)

		self.assertEqual([str(row["date"]) for row in rows], ["2026-08-13", "2026-08-14", "2026-08-15"])


class TestBuildJourneyRows(FrappeTestCase):
	def test_there_and_back(self):
		rows = build_journey_rows(
			start="2026-08-13 08:00:00",
			end="2026-08-13 17:00:00",
			origin="Heidelberg, Büro",
			destination="Baden-Baden",
			mode_of_transport="Car (private)",
			distance=90,
			employee_vehicle=None,
			return_journey=1,
		)

		self.assertEqual(len(rows), 2)
		self.assertEqual(rows[0]["from"], "Heidelberg, Büro")
		self.assertEqual(rows[0]["to"], "Baden-Baden")
		self.assertEqual(rows[1]["from"], "Baden-Baden")
		self.assertEqual(rows[1]["to"], "Heidelberg, Büro")
		# One way is stored per row, the trip adds them up.
		self.assertEqual([row["distance"] for row in rows], [90, 90])

	def test_one_way_only(self):
		rows = build_journey_rows(
			start="2026-08-13 08:00:00",
			end="2026-08-13 17:00:00",
			origin="Heidelberg",
			destination="Baden-Baden",
			mode_of_transport="Train",
			distance=0,
			employee_vehicle=None,
			return_journey=0,
		)

		self.assertEqual(len(rows), 1)

	def test_return_journey_is_dated_on_the_last_day(self):
		rows = build_journey_rows(
			start="2026-08-13 08:00:00",
			end="2026-08-15 17:00:00",
			origin="Heidelberg",
			destination="Berlin",
			mode_of_transport="Train",
			distance=0,
			employee_vehicle=None,
			return_journey=1,
		)

		self.assertEqual(str(rows[0]["date"]), "2026-08-13")
		self.assertEqual(str(rows[1]["date"]), "2026-08-15")

	def test_nothing_without_a_route(self):
		rows = build_journey_rows(
			start="2026-08-13 08:00:00",
			end="2026-08-13 17:00:00",
			origin=None,
			destination="Baden-Baden",
			mode_of_transport="Train",
			distance=0,
			employee_vehicle=None,
			return_journey=1,
		)

		self.assertEqual(rows, [])


class TestBusinessTripIntake(FrappeTestCase):
	def setUp(self):
		self.company = frappe.db.get_value("Company", {}, "name")
		if not self.company:
			self.skipTest("No Company in the test site")

	def make_intake(self, **kwargs) -> "frappe.Document":
		doc = frappe.get_doc(
			{
				"doctype": "Business Trip Intake",
				"company": self.company,
				"purpose": "Bauvorhaben Baden-Baden",
				"start_datetime": "2026-08-13 08:00:00",
				"end_datetime": "2026-08-13 17:00:00",
				"origin": "Heidelberg, Büro",
				"destination": "Baden-Baden",
				"mode_of_transport": "Train",
				"meals_confirmed": 1,
				**kwargs,
			}
		)
		doc.insert()
		return doc

	def test_missing_purpose_is_asked_for(self):
		intake = self.make_intake(purpose=None)

		self.assertEqual(intake.status, "Questions Open")
		self.assertIn("purpose", intake.open_questions)

	def test_unanswered_meals_are_asked_for(self):
		intake = self.make_intake(meals_confirmed=0)

		self.assertIn("meals_confirmed", intake.open_questions)

	def test_distance_is_asked_for_when_driving(self):
		intake = self.make_intake(mode_of_transport="Car (private)")

		self.assertIn("distance", intake.open_questions)

	def test_distance_is_not_asked_for_when_taking_the_train(self):
		intake = self.make_intake(mode_of_transport="Train")

		self.assertNotIn("distance:", intake.open_questions or "")

	def test_return_before_departure_is_rejected(self):
		self.assertRaises(
			frappe.ValidationError,
			self.make_intake,
			end_datetime="2026-08-12 17:00:00",
		)

	def test_transfer_is_refused_while_questions_are_open(self):
		intake = self.make_intake(purpose=None)

		self.assertRaises(frappe.ValidationError, intake.create_business_trip)
