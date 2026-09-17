# Copyright (c) 2024, ALYF GmbH and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase

# Customer and Project reach Payment Gateway (payments app), which CI does not install.
test_ignore = ["Customer", "Project"]


class TestBusinessTrip(FrappeTestCase):
	pass
