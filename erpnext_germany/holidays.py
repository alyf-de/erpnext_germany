from datetime import date, datetime, timedelta

import frappe
from frappe.utils.data import getdate
import holidays


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


def get_weekday_dates(year: int, weekday: int):
	my_date = date(year, 1, 1)
	if my_date.weekday() != weekday:
		my_date += timedelta(days=7 - (my_date.weekday() - weekday))

	while my_date.year == year:
		yield my_date
		my_date += timedelta(days=7)


def append_holidays(doc, holidays):
	for date, description in sorted(holidays):
		if date in [holiday.holiday_date for holiday in doc.holidays]:
			continue

		doc.append(
			"holidays",
			{
				"holiday_date": date,
				"description": description,
			},
		)


def create_holiday_list(year: int, holidays: dict, name: str):
	doc = frappe.new_doc("Holiday List")
	doc.holiday_list_name = name
	doc.from_date = f"{year}-01-01"
	doc.to_date = f"{year}-12-31"

	append_holidays(doc, holidays)
	doc.insert()


def update_holiday_list(year: int, holidays: dict, name: str):
	doc = frappe.get_doc("Holiday List", name)

	if getdate(doc.to_date) > getdate(f"{year}-12-31"):
		return

	doc.to_date = f"{year}-12-31"
	append_holidays(doc, holidays)
	doc.save()


def create_or_update_holiday_lists(year: int | None = None) -> None:
	if not frappe.db.exists("DocType", "Holiday List"):
		return

	year = year or datetime.now().year
	sundays = [
		(sunday, "Sonntag") for sunday in get_weekday_dates(year, 6)
	]
	saturdays = [
		(saturday, "Samstag") for saturday in get_weekday_dates(year, 5)
	]

	for state_short, state_long in GERMAN_STATES:
		state_holidays = list(holidays.country_holidays("DE", subdiv=state_short, years=year, language="de").items())

		for week_len in (5, 6):
			list_name = f"{state_long} {week_len}-Tage-Woche"
			holiday_list = state_holidays + sundays
			if week_len == 5:
				holiday_list += saturdays

			if frappe.db.exists("Holiday List", list_name):
				update_holiday_list(year, holiday_list, list_name)
			else:
				create_holiday_list(year, holiday_list, list_name)
