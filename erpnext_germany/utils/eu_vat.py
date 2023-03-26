from zeep import Client
import re

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


def check_vat_approx(
	country_code, vat_number, requester_country_code=None, requester_vat_number=None
):
	return Client(WSDL_URL).service.checkVatApprox(
		countryCode=country_code,
		vatNumber=vat_number,
		requesterCountryCode=requester_country_code,
		requesterVatNumber=requester_vat_number,
	)
