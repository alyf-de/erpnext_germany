import frappe


def execute():
	"""
	Move the data from the old fields (on doc level) to the new child table.
	"""
	for business_trip_region_id in frappe.get_all("Business Trip Region", filters={"disabled": 0}, pluck="name"):
		doc = frappe.get_doc("Business Trip Region", business_trip_region_id)
		if doc.allowances:
			continue

		doc.append(
			"allowances",
			{
				"valid_from": doc.valid_from or "2000-01-01",
				"whole_day": doc.whole_day or 0.0,
				"arrival_or_departure": doc.arrival_or_departure or 0.0,
				"accommodation": doc.accommodation or 0.0,
			}
		)
		doc.save()
