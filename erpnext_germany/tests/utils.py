# Copyright (c) 2026, ALYF GmbH and Contributors
# See license.txt

# Importing ERPNextTestSuite seeds ERPNext's master data (company, accounts, items, ...),
# because erpnext.tests.utils instantiates BootStrapTestData on import.
from erpnext.tests.utils import ERPNextTestSuite


class ERPNextGermanyTestSuite(ERPNextTestSuite):
	pass
