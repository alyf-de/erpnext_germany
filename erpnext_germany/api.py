import frappe
from .utils.eu_vat import check_vat, parse_vat_id


@frappe.whitelist()
def validate_vat_id(vat_id: str) -> bool:
	"""Use the EU VAT checker to validate a VAT ID."""
	is_valid = frappe.cache().hget("eu_vat_validation", vat_id, shared=True)
	if is_valid is not None:
		return is_valid

	try:
		country_code, vat_number = parse_vat_id(vat_id)
		result = check_vat(country_code, vat_number)
		is_valid = result.valid
		frappe.cache().hset("eu_vat_validation", vat_id, is_valid, shared=True)
	except Exception:
		frappe.response["status_code"] = 501
		is_valid = None

	return is_valid
