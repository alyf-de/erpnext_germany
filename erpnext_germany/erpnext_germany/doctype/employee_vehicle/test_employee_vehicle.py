# Copyright (c) 2026, ALYF GmbH and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_germany.erpnext_germany.doctype.employee_vehicle.employee_vehicle import (
	get_default_vehicle,
	get_mileage_rate,
)


def create_employee(employee_name: str = "_Test Traveller") -> str:
	existing = frappe.db.exists("Employee", {"employee_name": employee_name})
	if existing:
		return existing

	company = frappe.db.get_value("Company", {}, "name")
	employee = frappe.get_doc(
		{
			"doctype": "Employee",
			"employee_name": employee_name,
			"first_name": employee_name,
			"company": company,
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2020-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name"),
			"status": "Active",
		}
	)
	employee.insert()
	return employee.name


def create_vehicle(employee: str, **kwargs) -> "frappe.Document":
	doc = frappe.get_doc(
		{
			"doctype": "Employee Vehicle",
			"employee": employee,
			"vehicle_name": "VW Passat",
			"ownership": "Private",
			"vehicle_class": "Car",
			**kwargs,
		}
	)
	doc.insert()
	return doc


class TestEmployeeVehicle(FrappeTestCase):
	def setUp(self):
		self.employee = create_employee()
		frappe.db.delete("Employee Vehicle", {"employee": self.employee})

	def test_title_contains_license_plate(self):
		vehicle = create_vehicle(self.employee, license_plate="HD-AF 123")

		self.assertEqual(vehicle.title, "VW Passat (HD-AF 123)")

	def test_title_without_license_plate(self):
		vehicle = create_vehicle(self.employee)

		self.assertEqual(vehicle.title, "VW Passat")

	def test_only_one_default_per_employee(self):
		create_vehicle(self.employee, is_default=1)

		self.assertRaises(
			frappe.ValidationError,
			create_vehicle,
			self.employee,
			vehicle_name="Audi A4",
			is_default=1,
		)

	def test_disabled_default_does_not_block(self):
		create_vehicle(self.employee, is_default=1, disabled=1)

		second = create_vehicle(self.employee, vehicle_name="Audi A4", is_default=1)

		self.assertEqual(second.is_default, 1)

	def test_single_vehicle_is_proposed_without_default_flag(self):
		vehicle = create_vehicle(self.employee)

		self.assertEqual(get_default_vehicle(self.employee), vehicle.name)

	def test_no_proposal_if_several_vehicles_and_no_default(self):
		create_vehicle(self.employee)
		create_vehicle(self.employee, vehicle_name="Audi A4")

		self.assertIsNone(get_default_vehicle(self.employee))

	def test_default_wins_over_other_vehicles(self):
		create_vehicle(self.employee)
		default = create_vehicle(self.employee, vehicle_name="Audi A4", is_default=1)

		self.assertEqual(get_default_vehicle(self.employee), default.name)

	def test_disabled_vehicle_is_not_proposed(self):
		create_vehicle(self.employee, disabled=1)

		self.assertIsNone(get_default_vehicle(self.employee))

	def test_car_uses_standard_rate(self):
		vehicle = create_vehicle(self.employee)

		self.assertEqual(get_mileage_rate(vehicle.name, 0.30), 0.30)

	def test_motorcycle_uses_lower_rate(self):
		vehicle = create_vehicle(self.employee, vehicle_name="BMW R", vehicle_class="Motorcycle")
		frappe.db.set_single_value("Business Trip Settings", "mileage_allowance_other_motor_vehicle", 0.20)

		self.assertEqual(get_mileage_rate(vehicle.name, 0.30), 0.20)

	def test_motorcycle_falls_back_to_standard_rate_if_unconfigured(self):
		vehicle = create_vehicle(self.employee, vehicle_name="BMW R", vehicle_class="Motorcycle")
		frappe.db.set_single_value("Business Trip Settings", "mileage_allowance_other_motor_vehicle", 0)

		self.assertEqual(get_mileage_rate(vehicle.name, 0.30), 0.30)

	def test_no_vehicle_uses_standard_rate(self):
		self.assertEqual(get_mileage_rate(None, 0.30), 0.30)
