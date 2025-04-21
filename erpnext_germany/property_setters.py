def get_property_setters():
	return {
		"Employee": [
			("salary_currency", "default", "EUR"),
			("bank_ac_no", "label", "IBAN"),
			("ctc", "hidden", 1),
			("salary_mode", "default", "Bank"),
			("permanent_accommodation_type", "hidden", 1),
			("current_accommodation_type", "hidden", 1),
		],
	}
