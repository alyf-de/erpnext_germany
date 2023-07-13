from .holidays import create_or_update_holiday_lists
from datetime import datetime


def update_holiday_list_for_next_year():
	next_year = datetime.now().year + 1
	create_or_update_holiday_lists(next_year)
