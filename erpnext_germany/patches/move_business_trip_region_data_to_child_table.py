import frappe


def execute():
	"""
	Move the data from the old fields (on doc level) to the new child table.
	And rename the documents.
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

		# Step 2: Rename documents.
		# Since the valid_from field is based on the child table, there is no more need
		# for several documents with the same title.
		# Therefore, the title should be used as the new name.
		try:
			frappe.rename_doc("Business Trip Region", business_trip_region_id, doc.title, force=True, merge=True)
		except frappe.DuplicateEntryError as e:
			# Duplicate titles are expected in some cases; log with context and continue.
			frappe.log_error(
				message=f"Duplicate title while renaming Business Trip Region '{business_trip_region_id}' to '{doc.title}': {e}",
				title="Business Trip Region rename skipped due to duplicate title",
			)
		except Exception as e:
			# Unexpected errors should be logged with context and re-raised.
			frappe.log_error(
				message=f"Unexpected error while renaming Business Trip Region '{business_trip_region_id}' to '{doc.title}': {e}",
				title="Business Trip Region rename failed",
			)
			raise
