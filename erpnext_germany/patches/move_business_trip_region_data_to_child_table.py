import frappe


def execute():
	"""
	Move the data from the old fields (on doc level) to the new child table.
	And rename the documents.
	"""
	regions = frappe.get_all("Business Trip Region", filters={"disabled": 0}, pluck="name")
	for business_trip_region_id in regions:
		doc = frappe.get_doc("Business Trip Region", business_trip_region_id)

		# Step 1: Move the data to the child table.
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

		# Step 2: Rename documents.
		# Since the valid_from field based on the child table, there is no more need for several documents with the same title.
		# Therefore, the title should be used as the new name.
		try:
			frappe.rename_doc("Business Trip Region", business_trip_region_id, doc.title, force=True)
		except Exception as e:
			frappe.log_error(e)
