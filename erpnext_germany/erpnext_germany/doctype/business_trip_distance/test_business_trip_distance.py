# Copyright (c) 2026, ALYF GmbH and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_germany.erpnext_germany.doctype.business_trip_distance.business_trip_distance import (
	get_distance,
)


def create_distance(**kwargs) -> "frappe.Document":
	doc = frappe.get_doc(
		{
			"doctype": "Business Trip Distance",
			"from_location": "Heidelberg, Büro",
			"to_location": "Baden-Baden",
			"distance": 90,
			**kwargs,
		}
	)
	doc.insert()
	return doc


class TestBusinessTripDistance(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Business Trip Distance")

	def test_exact_match(self):
		create_distance()

		result = get_distance("Heidelberg, Büro", "Baden-Baden")

		self.assertEqual(result["distance"], 90)

	def test_match_ignores_case_and_extra_spaces(self):
		create_distance()

		result = get_distance("  heidelberg,   BÜRO ", "baden-baden")

		self.assertEqual(result["distance"], 90)

	def test_reverse_direction(self):
		create_distance(is_bidirectional=1)

		result = get_distance("Baden-Baden", "Heidelberg, Büro")

		self.assertEqual(result["distance"], 90)

	def test_reverse_direction_only_if_bidirectional(self):
		create_distance(is_bidirectional=0)

		self.assertIsNone(get_distance("Baden-Baden", "Heidelberg, Büro"))

	def test_unknown_route(self):
		create_distance()

		self.assertIsNone(get_distance("Heidelberg, Büro", "Hamburg"))

	def test_disabled_route_is_ignored(self):
		create_distance(disabled=1)

		self.assertIsNone(get_distance("Heidelberg, Büro", "Baden-Baden"))

	def test_company_specific_wins_over_shared(self):
		company = frappe.db.get_value("Company", {}, "name")
		if not company:
			self.skipTest("No Company in the test site")

		create_distance(distance=90)
		create_distance(distance=95, company=company)

		self.assertEqual(get_distance("Heidelberg, Büro", "Baden-Baden", company)["distance"], 95)
		self.assertEqual(get_distance("Heidelberg, Büro", "Baden-Baden")["distance"], 90)

	def test_duplicate_route_is_rejected(self):
		create_distance()

		self.assertRaises(frappe.ValidationError, create_distance, distance=95)

	def test_duplicate_in_opposite_direction_is_rejected(self):
		create_distance(is_bidirectional=1)

		self.assertRaises(
			frappe.ValidationError,
			create_distance,
			from_location="Baden-Baden",
			to_location="Heidelberg, Büro",
		)

	def test_new_bidirectional_route_cannot_shadow_a_one_way_route(self):
		create_distance(is_bidirectional=0)

		self.assertRaises(
			frappe.ValidationError,
			create_distance,
			from_location="Baden-Baden",
			to_location="Heidelberg, Büro",
			is_bidirectional=1,
		)

	def test_opposite_one_way_routes_may_coexist(self):
		create_distance(is_bidirectional=0, distance=90)

		back = create_distance(
			from_location="Baden-Baden",
			to_location="Heidelberg, Büro",
			is_bidirectional=0,
			distance=95,
		)

		self.assertEqual(get_distance("Baden-Baden", "Heidelberg, Büro")["name"], back.name)
		self.assertEqual(get_distance("Heidelberg, Büro", "Baden-Baden")["distance"], 90)

	def test_unrelated_route_is_not_a_duplicate(self):
		create_distance()

		other = create_distance(to_location="Hamburg", distance=600)

		self.assertEqual(other.distance, 600)

	def test_same_from_and_to_is_rejected(self):
		self.assertRaises(frappe.ValidationError, create_distance, to_location="Heidelberg, Büro")

	def test_title_is_generated(self):
		doc = create_distance(is_bidirectional=1)

		self.assertEqual(doc.title, "Heidelberg, Büro ↔ Baden-Baden (90 km)")
