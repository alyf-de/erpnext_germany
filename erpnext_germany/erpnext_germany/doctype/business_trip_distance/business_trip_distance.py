# Copyright (c) 2026, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BusinessTripDistance(Document):
	"""A recurring route with a known distance, e.g. office to a construction site.

	Used to propose the distance of a Business Trip Journey instead of asking for it
	every single time.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link | None
		disabled: DF.Check
		distance: DF.Int
		from_location: DF.Data
		is_bidirectional: DF.Check
		notes: DF.SmallText | None
		title: DF.Data | None
		to_location: DF.Data
	# end: auto-generated types

	def validate(self):
		self.strip_locations()
		self.validate_distance()
		self.validate_duplicate()
		self.set_title()

	def strip_locations(self):
		self.from_location = collapse_whitespace(self.from_location)
		self.to_location = collapse_whitespace(self.to_location)

	def validate_distance(self):
		if self.distance <= 0:
			frappe.throw(_("Distance must be greater than zero."))

		if normalize(self.from_location) == normalize(self.to_location):
			frappe.throw(_("From and To must be different."))

	def validate_duplicate(self):
		"""Prevent two rows that would match the same journey, so the proposal stays predictable.

		Only routes of the same company are compared: a company specific distance is meant to
		override a shared one, not to collide with it.
		"""
		if self.disabled:
			return

		candidates = get_candidates(self.from_location, self.to_location, all_companies=True)

		for existing in candidates:
			if existing.name == self.name or (existing.company or "") != (self.company or ""):
				continue

			if routes_overlap(existing, self):
				frappe.throw(
					_("{0} already covers this route.").format(
						frappe.utils.get_link_to_form("Business Trip Distance", existing.name)
					),
					title=_("Duplicate Distance"),
				)

	def set_title(self):
		arrow = "↔" if self.is_bidirectional else "→"
		self.title = f"{self.from_location} {arrow} {self.to_location} ({self.distance} km)"


def collapse_whitespace(value: str | None) -> str:
	return " ".join((value or "").split())


def normalize(value: str | None) -> str:
	return collapse_whitespace(value).casefold()


def matches(distance, from_location: str, to_location: str) -> bool:
	"""Return True if the stored route describes the given journey, in either direction."""
	stored_from = normalize(distance.from_location)
	stored_to = normalize(distance.to_location)
	wanted_from = normalize(from_location)
	wanted_to = normalize(to_location)

	if stored_from == wanted_from and stored_to == wanted_to:
		return True

	return bool(distance.is_bidirectional) and stored_from == wanted_to and stored_to == wanted_from


def routes_overlap(first, second) -> bool:
	"""Return True if a single journey could match both routes.

	The reverse direction collides as soon as *either* route is bidirectional -- checking only
	one of them would let a new two-way route slip in behind an existing one-way route.
	"""
	first_from, first_to = normalize(first.from_location), normalize(first.to_location)
	second_from, second_to = normalize(second.from_location), normalize(second.to_location)

	if (first_from, first_to) == (second_from, second_to):
		return True

	if (first_from, first_to) == (second_to, second_from):
		return bool(first.is_bidirectional or second.is_bidirectional)

	return False


def get_candidates(
	from_location: str, to_location: str, company: str | None = None, all_companies: bool = False
) -> list:
	"""Return enabled routes that could describe this journey.

	The query narrows down to rows that mention one of the two places, in either column; the
	final decision is made by `matches` / `routes_overlap`. `get_list` is used on purpose, so
	the caller only ever sees routes they are allowed to read.
	"""
	places = [collapse_whitespace(from_location), collapse_whitespace(to_location)]
	if not all(places):
		return []

	rows = frappe.get_list(
		"Business Trip Distance",
		filters={"disabled": 0},
		or_filters=[
			["from_location", "in", places],
			["to_location", "in", places],
		],
		fields=["name", "from_location", "to_location", "distance", "is_bidirectional", "company"],
	)

	if all_companies:
		return rows

	return [row for row in rows if not row.company or row.company == company]


@frappe.whitelist()
def get_distance(from_location: str, to_location: str, company: str | None = None) -> dict | None:
	"""Return the stored distance for a route, or None if it is unknown.

	A distance of the given company wins over one that is shared by all companies.
	"""
	frappe.has_permission("Business Trip Distance", throw=True)

	if not (from_location and to_location):
		return None

	best = None
	for candidate in get_candidates(from_location, to_location, company):
		if not matches(candidate, from_location, to_location):
			continue

		# A company specific route beats the shared one.
		if best is None or (candidate.company and not best.company):
			best = candidate

	if not best:
		return None

	return {
		"name": best.name,
		"distance": best.distance,
		"from_location": best.from_location,
		"to_location": best.to_location,
	}
