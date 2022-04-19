import frappe


@frappe.whitelist()
def validate_vat_id(vat_id: str) -> bool:
	"""Use the EU VAT checker to validate a VAT ID."""
	from .utils.eu_vat import is_valid_eu_vat_id

	result = frappe.cache().hget("eu_vat_validation", vat_id, shared=True)
	if result is not None:
		return result

	try:
		result = is_valid_eu_vat_id(vat_id)
		frappe.cache().hset("eu_vat_validation", vat_id, result, shared=True)
	except Exception:
		frappe.response["status_code"] = 501
		result = None

	return result
