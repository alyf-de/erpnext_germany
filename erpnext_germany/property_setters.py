def get_property_setters():
	return {
		"Employee": [
			("salary_currency", "default", "EUR"),
			("salary_mode", "default", "Bank"),
			("permanent_accommodation_type", "hidden", 1),
			("current_accommodation_type", "hidden", 1),
		],
	}
