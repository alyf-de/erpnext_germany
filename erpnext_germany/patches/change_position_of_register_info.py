import frappe


def execute():
	"""Update the position of the Register Information section in Customer and Supplier."""
	for dt in ("Customer", "Supplier"):
		cf = frappe.db.exists("Custom Field", {"fieldname": "register_sb_1", "dt": dt})
		if not cf:
			continue

		frappe.db.set_value("Custom Field", cf, "insert_after", "companies")
