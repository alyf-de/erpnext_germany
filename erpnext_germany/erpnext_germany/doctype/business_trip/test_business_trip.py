# Copyright (c) 2024, ALYF GmbH and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_germany.erpnext_germany.doctype.business_trip.business_trip import get_cost_center


class TestBusinessTrip(FrappeTestCase):
	def test_cost_center_of_the_trip_wins(self):
		trip = frappe.get_doc(
			{"doctype": "Business Trip", "company": "_Test Company", "cost_center": "Project X - _TC"}
		)
		self.assertEqual(get_cost_center(trip), "Project X - _TC")

	def test_company_default_fills_in(self):
		"""Without a cost center no row of the expense claim can be submitted."""
		trip = frappe.get_doc({"doctype": "Business Trip", "company": "_Test Company"})

		with patch.object(frappe, "get_cached_value", return_value="Main - _TC") as cached:
			self.assertEqual(get_cost_center(trip), "Main - _TC")

		cached.assert_called_once_with("Company", "_Test Company", "cost_center")
