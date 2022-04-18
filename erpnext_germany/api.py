from frappe import whitelist


@whitelist()
def validate_vat_id(vat_id: str) -> bool:
	"""Use the EU VAT checker to validate a VAT ID."""
	from .utils.eu_vat import is_valid_eu_vat_id

	return is_valid_eu_vat_id(vat_id)
