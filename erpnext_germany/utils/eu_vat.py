import re

from requests.exceptions import ConnectionError
from tenacity import (
	retry,
	retry_any,
	retry_if_exception_message,
	retry_if_exception_type,
	stop_after_attempt,
	wait_exponential,
)
from zeep import Client

WSDL_URL = "https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl"
COUNTRY_CODE_REGEX = r"^[A-Z]{2}$"
VAT_NUMBER_REGEX = r"^[0-9A-Za-z\+\*\.]{2,12}$"


def parse_vat_id(vat_id: str) -> tuple[str, str]:
	country_code = vat_id[:2].upper()
	vat_number = vat_id[2:].replace(" ", "")

	# check vat_number and country_code with regex
	if not re.match(COUNTRY_CODE_REGEX, country_code):
		raise ValueError("Invalid country code")

	if not re.match(VAT_NUMBER_REGEX, vat_number):
		raise ValueError("Invalid VAT number")

	return country_code, vat_number


def check_vat(country_code: str, vat_number: str):
	"""Use the EU VAT checker to validate a VAT ID."""
	return Client(WSDL_URL).service.checkVat(
		vatNumber=vat_number, countryCode=country_code
	)


@retry(
	retry=retry_any(
		retry_if_exception_message(message="GLOBAL_MAX_CONCURRENT_REQ"),
		retry_if_exception_message(message="MS_MAX_CONCURRENT_REQ"),
		retry_if_exception_message(message="SERVICE_UNAVAILABLE"),
		retry_if_exception_message(message="MS_UNAVAILABLE"),
		retry_if_exception_message(message="TIMEOUT"),
		retry_if_exception_type(ConnectionError),
	),
	stop=stop_after_attempt(3),
	wait=wait_exponential(multiplier=1, min=2, max=64),
)
def check_vat_approx(
	country_code: str,
	vat_number: str,
	trader_name: str | None = None,
	trader_street: str | None = None,
	trader_postcode: str | None = None,
	trader_city: str | None = None,
	requester_country_code: str | None = None,
	requester_vat_number: str | None = None,
):
	return Client(WSDL_URL).service.checkVatApprox(
		countryCode=country_code,
		vatNumber=vat_number,
		traderName=trader_name,
		traderStreet=trader_street,
		traderPostcode=trader_postcode,
		traderCity=trader_city,
		requesterCountryCode=requester_country_code,
		requesterVatNumber=requester_vat_number,
	)
