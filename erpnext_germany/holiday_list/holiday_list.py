from datetime import date, datetime, timedelta
from time import sleep

import frappe
from frappe.utils.data import getdate
from frappe.utils import update_progress_bar

from .api import FeiertageApiClient

GERMAN_STATES = (
	("BW", "Baden-Württemberg"),
	("BY", "Bayern"),
	("BE", "Berlin"),
	("BB", "Brandenburg"),
	("HB", "Bremen"),
	("HH", "Hamburg"),
	("HE", "Hessen"),
	("MV", "Mecklenburg-Vorpommern"),
	("NI", "Niedersachsen"),
	("NW", "Nordrhein-Westfalen"),
	("RP", "Rheinland Pfalz"),
	("SL", "Saarland"),
	("SN", "Sachsen"),
	("ST", "Sachen-Anhalt"),
	("SH", "Schleswig Holstein"),
	("TH", "Thüringen"),
)


def get_all_occurring_days(year, weekday):
	days = []
	my_date = date(year, 1, 1)

	while my_date.year == year:
		if my_date.weekday() == weekday:
			days.append(my_date)

		my_date += timedelta(days=1)

	return days


def append_holidays(doc, year, holidays, weekdays):
	all_holidays = {}

	for holiday_name, holday_date in holidays:
		date = getdate(holday_date)
		all_holidays[date] = holiday_name

	for date in get_all_occurring_days(year, 6):
		if date not in all_holidays:
			all_holidays[date] = "Sonntag"

	if weekdays == 5:
		for date in get_all_occurring_days(year, 5):
			if date not in all_holidays:
				all_holidays[date] = "Samstag"

	for date, description in sorted(all_holidays.items()):
		doc.append(
			"holidays",
			{
				"holiday_date": date,
				"description": description,
			},
		)


def new_holiday_list(year: int, holidays: dict, name: str, weekdays: int):
	doc = frappe.new_doc("Holiday List")
	doc.holiday_list_name = name
	doc.from_date = f"{year}-01-01"
	doc.to_date = f"{year}-12-31"

	append_holidays(doc, year, holidays, weekdays)
	doc.insert()


def update_local_holiday_list(year: int, holidays: dict, name: str, week_len: int):
	doc = frappe.get_doc("Holiday List", name)

	if getdate(doc.to_date) < getdate(f"{year}-12-31"):
		doc.update({"to_date": f"{year}-12-31"})
		append_holidays(doc, year, holidays, week_len)
		doc.save()


def update_holiday_lists(year: int | None = None) -> None:
	if not frappe.db.exists("DocType", "Holiday List"):
		return

	client = FeiertageApiClient()
	year = year or datetime.now().year
	l = len(GERMAN_STATES) + 2

	update_progress_bar("Creating holiday lists", 0, l)
	holidays_this_year = client.get_holidays(year)
	sleep(.25)

	update_progress_bar("Creating holiday lists", 1, l)
	holidays_next_year = client.get_holidays(year + 1)
	sleep(.25)

	for i, (state_short, state_long) in enumerate(GERMAN_STATES):
		if (
			frappe.flags.in_patch
			or frappe.flags.in_install
			or frappe.flags.in_migrate
		):
			update_progress_bar(f"Creating holiday lists", i + 2, l)

		for week_len in (5, 6):
			list_name = f"{state_long} {week_len}-Tage-Woche"
			if not frappe.db.exists("Holiday List", list_name):
				new_holiday_list(year, holidays_this_year[state_short], list_name, week_len)

			update_local_holiday_list(year + 1, holidays_next_year[state_short], list_name, week_len)
