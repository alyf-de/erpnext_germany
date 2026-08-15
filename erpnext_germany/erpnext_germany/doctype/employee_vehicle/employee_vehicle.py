# Copyright (c) 2026, ALYF GmbH and contributors
# For license information, please see license.txt

from collections.abc import Iterable

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import flt

PRIVATE = "Private"
LOWER_RATE_CLASSES = ("Motorcycle", "Other Motor Vehicle")
MANAGING_ROLES = ("HR Manager", "System Manager", "Administrator")


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
		self.validate_employee()
		self.validate_single_default()
		self.set_title()

	def validate_employee(self):
		"""Everyone keeps their own vehicles; only HR maintains them for others.

		Without this, anyone could add a vehicle to a colleague and take away their default.
		"""
		if set(MANAGING_ROLES) & set(frappe.get_roles()):
			return

		own_employee = frappe.get_all(
			"Employee",
			filters={"user_id": frappe.session.user},
			pluck="name",
			limit=1,
		)

		if not own_employee or self.employee != own_employee[0]:
			frappe.throw(
				_("You can only maintain your own vehicles."),
				frappe.PermissionError,
				title=_("Not Your Employee"),
			)

	def validate_single_default(self):
		"""Keep at most one default per person, so the proposal is unambiguous.

		Read the name from the employee record rather than from `employee_name`: the fetched
		value is not filled in yet while this runs on a new document.
		"""
		if not self.is_default or self.disabled:
			return

		other_defaults = frappe.get_all(
			"Employee Vehicle",
			filters={
				"employee_name": get_person(self.employee),
				"is_default": 1,
				"disabled": 0,
				"name": ("!=", self.name),
			},
			pluck="name",
			limit=1,
		)

		if other_defaults:
			other_default = other_defaults[0]
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


def get_person(employee: str | None) -> str | None:
	"""Return the name of the person behind an employee record.

	Someone who works for several companies has one employee record per company. Vehicles
	belong to the person, not to the record, so everything about vehicles is keyed on the
	employee name rather than on the record.
	"""
	if not employee:
		return None

	return frappe.get_cached_value("Employee", employee, "employee_name")


def get_person_vehicles(employee: str | None, ownership: str | None = None, limit: int = 20) -> list:
	"""Return the enabled vehicles of the person behind an employee record."""
	person = get_person(employee)
	if not person:
		return []

	filters = {"employee_name": person, "disabled": 0}
	if ownership:
		filters["ownership"] = ownership

	return frappe.get_list(
		"Employee Vehicle",
		filters=filters,
		fields=["name", "is_default"],
		limit=limit,
		order_by="is_default desc",
	)


def get_vehicles(names: Iterable[str]) -> dict[str, "frappe._dict"]:
	"""Return the vehicles by name, in a single query.

	Deliberately not permission filtered: this feeds the integrity checks and the amount
	calculation of a Business Trip, which an approver or accountant must be able to save even
	though the vehicle belongs to someone else. Nothing from here is shown to the user beyond
	the vehicle they picked themselves.

	Missing names are simply absent from the result, so callers must use `.get()`.
	"""
	names = {name for name in names if name}
	if not names:
		return {}

	rows = frappe.get_all(
		"Employee Vehicle",
		filters={"name": ("in", list(names))},
		fields=["name", "employee", "employee_name", "ownership", "vehicle_class", "disabled", "title"],
	)

	return {row.name: row for row in rows}


def get_lower_mileage_rate() -> float:
	"""Return the configured rate for motorcycles and other motor vehicles, 0 if unset."""
	settings = frappe.get_cached_doc("Business Trip Settings")

	return flt(settings.mileage_allowance_other_motor_vehicle)


def get_mileage_rate(
	vehicle_class: str | None, default_rate: float, lower_rate: float | None = None
) -> float:
	"""Return the rate per kilometer for a vehicle class.

	Cars are reimbursed at the standard rate, motorcycles and other motor vehicles at the
	lower rate from Business Trip Settings. If that lower rate is not configured, the
	standard rate applies, so an incomplete setup never pays less than before.

	Pass `lower_rate` to avoid one query per journey.
	"""
	if vehicle_class not in LOWER_RATE_CLASSES:
		return default_rate

	if lower_rate is None:
		lower_rate = get_lower_mileage_rate()

	return lower_rate or default_rate


@frappe.whitelist()
def get_default_vehicle(employee: str, ownership: str | None = None) -> str | None:
	"""Return the employee's default vehicle, or their only one.

	`ownership` narrows the proposal to e.g. private vehicles, so a company car is never
	suggested for a journey that claims a mileage allowance.

	Uses `get_list`, so a caller only ever gets a vehicle they are allowed to read.
	"""
	frappe.has_permission("Employee Vehicle", throw=True)

	vehicles = get_person_vehicles(employee, ownership, limit=2)

	if not vehicles:
		return None

	if vehicles[0].is_default or len(vehicles) == 1:
		return vehicles[0].name

	return None
