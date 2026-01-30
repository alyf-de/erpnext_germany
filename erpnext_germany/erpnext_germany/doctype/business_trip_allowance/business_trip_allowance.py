# Copyright (c) 2024, ALYF GmbH and contributors
# For license information, please see license.txt

# import frappe
from datetime import datetime

from frappe.model.document import Document
from frappe.utils.data import get_time, getdate


class BusinessTripAllowance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accommodation_was_provided: DF.Check
		amount: DF.Currency
		breakfast_was_provided: DF.Check
		date: DF.Date
		dinner_was_provided: DF.Check
		from_time: DF.Time | None
		lunch_was_provided: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		to_time: DF.Time | None
		whole_day: DF.Check
	# end: auto-generated types

	def is_longer_than(self, hours: float) -> bool:
		if self.whole_day:
			duration_hours = 24
		else:
			cur_date = getdate(self.date)
			duration_hours = get_duration_hours(
				from_datetime=datetime.combine(cur_date, get_time(self.from_time)),
				to_datetime=datetime.combine(cur_date, get_time(self.to_time)),
			)

		return duration_hours > hours


def get_duration_hours(from_datetime: datetime, to_datetime: datetime) -> float:
	return (to_datetime - from_datetime).total_seconds() / 3600
