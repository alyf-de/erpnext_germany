# Copyright (c) 2025, ALYF GmbH and Contributors
# See license.txt


def before_validate(doc, event):
	if not doc.business_trip:
		doc.business_trip_employee = None
		doc.pay_to_employee = 0
