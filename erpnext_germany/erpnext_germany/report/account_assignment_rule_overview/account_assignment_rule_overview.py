# Copyright (c) 2026, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext_germany.erpnext_germany.doctype.account_assignment_rule.account_assignment_rule import (
	TARGET_FIELDS,
	get_applicable_rules,
	get_criteria,
	get_matching_rules,
	get_side,
)


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_data(filters: frappe._dict) -> list[dict]:
	"""List the rules matching the first row of `item` in the document, applied rule per Rule Type first."""
	if not (filters.document_type and filters.document_name and filters.item):
		return []

	doc = frappe.get_doc(filters.document_type, filters.document_name)
	doc.check_permission()

	side = get_side(type(doc))
	if not side:
		frappe.throw(_("{0} is neither a selling nor a buying document.").format(_(doc.doctype)))

	row = next((row for row in doc.get("items", []) if row.item_code == filters.item), None)
	if not row:
		frappe.throw(_("Item {0} is not in {1}.").format(filters.item, doc.name))

	matching_rules = get_matching_rules(get_applicable_rules(doc, side), get_criteria(doc, row))

	data = []
	applied_fields = set()
	for rule in matching_rules:
		target_field = TARGET_FIELDS[rule.rule_type]
		data.append(
			{
				"rule": rule.name,
				"title": rule.title,
				"rule_type": rule.rule_type,
				"account": rule.account,
				"cost_center": rule.cost_center,
				"priority": rule.priority,
				"specificity": rule.specificity,
				# ERPNext may still override a value, e.g. the expense account of stock items
				"applied": target_field not in applied_fields
				and row.get(target_field) == (rule.account or rule.cost_center),
			}
		)
		applied_fields.add(target_field)

	return sorted(data, key=lambda row: row["rule_type"])  # stable, keeps the ranking within a Rule Type


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Rule"),
			"fieldname": "rule",
			"fieldtype": "Link",
			"options": "Account Assignment Rule",
			"width": 180,
		},
		{"label": _("Title"), "fieldname": "title", "fieldtype": "Data", "width": 200},
		{"label": _("Rule Type"), "fieldname": "rule_type", "fieldtype": "Data", "width": 150},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 250,
		},
		{
			"label": _("Cost Center"),
			"fieldname": "cost_center",
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": 200,
		},
		{"label": _("Priority"), "fieldname": "priority", "fieldtype": "Int", "width": 90},
		{"label": _("Specificity"), "fieldname": "specificity", "fieldtype": "Int", "width": 100},
		{"label": _("Applied"), "fieldname": "applied", "fieldtype": "Check", "width": 90},
	]
