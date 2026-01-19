import frappe


def execute():
	"""
	Move the data from the old fields (on doc level) to the new child table.
	"""
	regions = frappe.get_all("Business Trip Region", pluck="name")
	for business_trip_region_id in regions:
		doc = frappe.get_doc("Business Trip Region", business_trip_region_id)

		# Step 1: Move the data to the child table.
		doc.append(
			"allowances",
			{
				"valid_from": doc.get("valid_from") or "2000-01-01",
				"whole_day": doc.get("whole_day") or 0.0,
				"arrival_or_departure": doc.get("arrival_or_departure") or 0.0,
				"accommodation": doc.get("accommodation") or 0.0,
			},
		)
		doc.save()
