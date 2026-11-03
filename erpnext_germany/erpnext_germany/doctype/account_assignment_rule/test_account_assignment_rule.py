# Copyright (c) 2026, ALYF GmbH and Contributors
# See license.txt

import frappe
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.controllers.sales_and_purchase_return import make_return_doc

from erpnext_germany.erpnext_germany.doctype.account_assignment_rule.account_assignment_rule import (
	FILTER_WEIGHTS,
	ConflictingRuleError,
)
from erpnext_germany.erpnext_germany.report.account_assignment_rule_overview import (
	account_assignment_rule_overview as overview_report,
)
from erpnext_germany.tests.utils import ERPNextGermanyTestSuite

COMPANY = "_Test Company"
DEFAULT_INCOME = "Sales - _TC"
INCOME_A = "Service - _TC"
INCOME_B = "Interest Income - _TC"


def make_rule(**kwargs):
	return frappe.get_doc(
		{
			"doctype": "Account Assignment Rule",
			"company": COMPANY,
			"selling_or_buying": "Selling",
			"rule_type": "Income Account",
			**kwargs,
		}
	).insert()


def income_accounts(doc) -> list[str]:
	return [row.income_account for row in doc.items]


class TestAccountAssignmentRule(ERPNextGermanyTestSuite):
	def test_without_rules_erpnext_default_stays(self):
		si = create_sales_invoice()
		self.assertEqual(income_accounts(si), [DEFAULT_INCOME])

	def test_global_defaults_do_not_narrow_new_rules(self):
		previous = frappe.db.get_default("customer_group")
		self.addCleanup(frappe.db.set_default, "customer_group", previous)
		frappe.db.set_default("customer_group", "_Test Customer Group")

		rule = make_rule(account=INCOME_A)
		self.assertFalse([fieldname for fieldname in FILTER_WEIGHTS if rule.get(fieldname)])

	def test_more_specific_rule_wins_at_same_priority(self):
		make_rule(account=INCOME_A, filter_customer_group="_Test Customer Group")
		make_rule(account=INCOME_B, filter_customer="_Test Customer")

		si = create_sales_invoice()
		self.assertEqual(income_accounts(si), [INCOME_B])

	def test_priority_beats_specificity(self):
		make_rule(account=INCOME_A, filter_item="_Test Item", filter_customer="_Test Customer")
		make_rule(account=INCOME_B, priority=1)

		si = create_sales_invoice()
		self.assertEqual(income_accounts(si), [INCOME_B])

	def test_filters_must_all_match(self):
		make_rule(account=INCOME_A, filter_customer="_Test Customer", filter_item="_Test Item 2")
		make_rule(account=INCOME_B, for_doctype="Sales Order")

		si = create_sales_invoice()
		self.assertEqual(income_accounts(si), [DEFAULT_INCOME])

	def test_for_doctype(self):
		make_rule(account=INCOME_A, for_doctype="Sales Invoice")
		make_rule(account=INCOME_B)

		si = create_sales_invoice()
		self.assertEqual(income_accounts(si), [INCOME_A])

	def test_conditions_on_missing_field_do_not_match_or_log(self):
		make_rule(account=INCOME_A, conditions="field_that_does_not_exist == 1")
		error_logs = frappe.db.count("Error Log")

		si = create_sales_invoice()
		self.assertEqual(income_accounts(si), [DEFAULT_INCOME])
		self.assertEqual(frappe.db.count("Error Log"), error_logs)

	def test_conditions(self):
		make_rule(account=INCOME_A, conditions="po_no == 'SPECIAL'")

		si = create_sales_invoice(do_not_save=True)
		si.insert()
		self.assertEqual(income_accounts(si), [DEFAULT_INCOME])

		si.po_no = "SPECIAL"
		si.save()
		self.assertEqual(income_accounts(si), [INCOME_A])

	def test_item_tax_template_filter(self):
		make_rule(account=INCOME_A, filter_item_tax_template="_Test Item Tax Template 1 - _TC")

		si = create_sales_invoice(do_not_save=True)
		si.append(
			"items",
			{
				**si.items[0].as_dict(),
				"name": None,
				"item_code": "_Test Item 2",  # a different item, duplicates may be disallowed
				"item_tax_template": "_Test Item Tax Template 1 - _TC",
			},
		)
		si.insert()
		self.assertEqual(income_accounts(si), [DEFAULT_INCOME, INCOME_A])

	def test_rule_wins_over_manual_edit(self):
		make_rule(account=INCOME_A)

		si = create_sales_invoice(do_not_submit=True)
		si.items[0].income_account = INCOME_B
		si.save()
		self.assertEqual(income_accounts(si), [INCOME_A])

	def test_returns_keep_original_accounts_unless_enabled(self):
		rule = make_rule(account=INCOME_A)
		si = create_sales_invoice()
		rule.db_set("account", INCOME_B)

		credit_note = make_return_doc("Sales Invoice", si.name)
		credit_note.insert()
		self.assertEqual(income_accounts(credit_note), [INCOME_A])

		frappe.db.set_single_value("ERPNext Germany Settings", "apply_account_assignment_rules_to_returns", 1)
		credit_note.save()
		self.assertEqual(income_accounts(credit_note), [INCOME_B])

	def test_buying_cost_center(self):
		make_rule(
			selling_or_buying="Buying",
			rule_type="Cost Center",
			cost_center="_Test Cost Center 2 - _TC",
			filter_supplier="_Test Supplier",
		)
		make_rule(rule_type="Cost Center", cost_center="Main - _TC")  # selling rule, ignored for buying

		pi = make_purchase_invoice(do_not_submit=True)
		self.assertEqual([row.cost_center for row in pi.items], ["_Test Cost Center 2 - _TC"])

	def test_item_selection_in_form(self):
		"""The form calls `process_item_selection` when an item is picked, the rule must apply right away."""
		make_rule(account=INCOME_A)

		si = create_sales_invoice(do_not_save=True)
		si.items[0].income_account = None
		si.run_method("process_item_selection", item_idx=1, reset_item_details=True, parentfield="items")
		self.assertEqual(income_accounts(si), [INCOME_A])

	def test_overview_report(self):
		make_rule(account=INCOME_A)
		make_rule(account=INCOME_B, priority=1)
		si = create_sales_invoice(do_not_submit=True)

		_columns, data = overview_report.execute(
			{"document_type": "Sales Invoice", "document_name": si.name, "row": "1"}
		)
		self.assertEqual(
			[(row["account"], row["applied"]) for row in data], [(INCOME_B, True), (INCOME_A, False)]
		)

	def test_validation(self):
		make_rule(account=INCOME_A, filter_customer="_Test Customer")
		self.assertRaises(ConflictingRuleError, make_rule, account=INCOME_B, filter_customer="_Test Customer")
		self.assertRaises(
			frappe.ValidationError,
			make_rule,
			selling_or_buying="Buying",
			rule_type="Discount Account",
			account="_Test Account Discount - _TC",
		)
		self.assertRaises(
			frappe.ValidationError, make_rule, rule_type="Income Account", account="Office Rent - _TC"
		)
		self.assertRaises(frappe.ValidationError, make_rule, account=INCOME_A, conditions="po_no ==")
		self.assertRaises(frappe.ValidationError, make_rule, rule_type="Income Account")
