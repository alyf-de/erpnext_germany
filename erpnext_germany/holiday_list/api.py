import frappe
import requests
from requests.adapters import HTTPAdapter


class FeiertageApiClient:
	def __init__(self):
		self.server_url = "https://feiertage-api.de/api/"
		self.adapter = HTTPAdapter(max_retries=3)
		self.session = requests.Session()
		self.session.mount(self.server_url, self.adapter)

	def request(self, method: str, params: dict = None) -> dict | None:
		try:
			response = self.session.request(
				method=method,
				url=self.server_url,
				params=params,
				timeout=3,
			)
			response.raise_for_status()  # raise error for failed requests
			return response.json()
		except Exception:
			frappe.log_error(frappe.get_traceback())

	def get_holidays(self, year: int) -> tuple[tuple[str, str, str]] | None:
		resp = self.request("GET", params={"jahr": year})
		if not resp:
			return None

		return {
			state: tuple(
				(holiday_name, data.get("datum"))
				for holiday_name, data in holidays.items()
			) for state, holidays in resp.items()
		}
