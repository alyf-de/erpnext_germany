import zeep


def is_valid_eu_vat_id(vat_id) -> bool:
	"""Use the EU VAT checker to validate a VAT ID."""
	country_code = vat_id[:2].upper()
	vat_number = vat_id[2:].replace(" ", "")

	client = zeep.Client("https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl")
	result = client.service.checkVat(vatNumber=vat_number, countryCode=country_code)

	return result.valid
