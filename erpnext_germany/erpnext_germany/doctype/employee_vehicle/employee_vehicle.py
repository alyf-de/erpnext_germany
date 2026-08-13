# Copyright (c) 2026, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import flt

PRIVATE = "Private"
LOWER_RATE_CLASSES = ("Motorcycle", "Other Motor Vehicle")


class EmployeeVehicle(Document):
	"""A vehicle an employee uses for business trips, e.g. one of several private cars.

	The vehicle records which car was actually driven and, through its class, at which
	rate the mileage is reimbursed.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		disabled: DF.Check
		employee: DF.Link
		employee_name: DF.Data | None
		fleet_vehicle: DF.Link | None
		is_default: DF.Check
		license_plate: DF.Data | None
		notes: DF.SmallText | None
		ownership: DF.Literal["Private", "Company Car", "Rental"]
		title: DF.Data | None
		vehicle_class: DF.Literal["Car", "Motorcycle", "Other Motor Vehicle"]
		vehicle_name: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.vehicle_name = " ".join((self.vehicle_name or "").split())
		self.license_plate = " ".join((self.license_plate or "").split())
		self.validate_single_default()
		self.set_title()

	def validate_single_default(self):
		"""Keep at most one default per employee, so the proposal is unambiguous."""
		if not self.is_default or self.disabled:
			return

		other_default = frappe.db.exists(
			"Employee Vehicle",
			{
				"employee": self.employee,
				"is_default": 1,
				"disabled": 0,
				"name": ("!=", self.name),
			},
		)

		if other_default:
			frappe.throw(
				_("{0} is already the default vehicle of this employee.").format(
					frappe.utils.get_link_to_form("Employee Vehicle", other_default)
				),
				title=_("Duplicate Default Vehicle"),
			)

	def set_title(self):
		parts = [self.vehicle_name]
		if self.license_plate:
			parts.append(f"({self.license_plate})")

		self.title = " ".join(part for part in parts if part)


def get_mileage_rate(vehicle: str | None, default_rate: float) -> float:
	"""Return the rate per kilometer for a vehicle.

	Cars are reimbursed at the standard rate, motorcycles and other motor vehicles at the
	lower rate from Business Trip Settings. If that lower rate is not configured, the
	standard rate applies.
	"""
	if not vehicle:
		return default_rate

	vehicle_class = frappe.db.get_value("Employee Vehicle", vehicle, "vehicle_class")
	if vehicle_class not in LOWER_RATE_CLASSES:
		return default_rate

	lower_rate = flt(
		frappe.db.get_single_value("Business Trip Settings", "mileage_allowance_other_motor_vehicle")
	)

	return lower_rate or default_rate


@frappe.whitelist()
def get_default_vehicle(employee: str) -> str | None:
	"""Return the employee's default vehicle, or their only one."""
	frappe.has_permission("Employee Vehicle", throw=True)

	vehicles = frappe.get_all(
		"Employee Vehicle",
		filters={"employee": employee, "disabled": 0},
		fields=["name", "is_default"],
		limit=2,
		order_by="is_default desc",
	)

	if not vehicles:
		return None

	if vehicles[0].is_default or len(vehicles) == 1:
		return vehicles[0].name

	return None
