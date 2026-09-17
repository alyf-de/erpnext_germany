# Copyright (c) 2025, ALYF GmbH and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase

# Expense Claim Type belongs to hrms, which CI does not install.
test_ignore = ["Expense Claim Type"]


class TestBusinessTripSettings(FrappeTestCase):
	pass
