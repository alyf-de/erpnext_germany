# Copyright (c) 2026, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from erpnext.controllers.buying_controller import BuyingController
from erpnext.controllers.selling_controller import SellingController
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form

# Rule Type -> item row field it sets
TARGET_FIELDS = {
	"Income Account": "income_account",
	"Expense Account": "expense_account",
	"Discount Account": "discount_account",
	"Provisional Account": "provisional_expense_account",
	"Cost Center": "cost_center",
}

# Row-level filters and their weight. The weight only breaks ties between rules with the same priority.
# The `filter_` prefix keeps Frappe from pre-filling new rules with global defaults of the same fieldname
# (e.g. `item_group` or `customer_group`), which would silently narrow a rule.
FILTER_WEIGHTS = {
	"filter_item": 2,
	"filter_item_group": 1,
	"filter_item_tax_template": 1,
	"filter_customer": 2,
	"filter_customer_group": 1,
	"filter_sales_taxes_and_charges_template": 1,
	"filter_supplier": 2,
	"filter_supplier_group": 1,
	"filter_purchase_taxes_and_charges_template": 1,
	"filter_tax_category": 1,
}

SIDE_FIELDS = {
	"Selling": ("filter_customer", "filter_customer_group", "filter_sales_taxes_and_charges_template"),
	"Buying": ("filter_supplier", "filter_supplier_group", "filter_purchase_taxes_and_charges_template"),
}


class ConflictingRuleError(frappe.ValidationError):
	pass


class AccountAssignmentRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		company: DF.Link
		conditions: DF.Code | None
		cost_center: DF.Link | None
		filter_customer: DF.Link | None
		filter_customer_group: DF.Link | None
		filter_item: DF.Link | None
		filter_item_group: DF.Link | None
		filter_item_tax_template: DF.Link | None
		filter_purchase_taxes_and_charges_template: DF.Link | None
		filter_sales_taxes_and_charges_template: DF.Link | None
		filter_supplier: DF.Link | None
		filter_supplier_group: DF.Link | None
		filter_tax_category: DF.Link | None
		for_doctype: DF.Link | None
		priority: DF.Int
		rule_type: DF.Literal[
			"Income Account", "Expense Account", "Discount Account", "Provisional Account", "Cost Center"
		]
		selling_or_buying: DF.Literal["Selling", "Buying"]
		title: DF.Data | None
	# end: auto-generated types

	def before_validate(self):
		if self.rule_type == "Cost Center":
			self.account = None
		else:
			self.cost_center = None

		other_side = "Buying" if self.selling_or_buying == "Selling" else "Selling"
		for fieldname in SIDE_FIELDS[other_side]:
			self.set(fieldname, None)

	def validate(self):
		self.validate_rule_type()
		self.validate_value()
		self.validate_conditions()
		self.validate_conflicting_rules()

	def validate_rule_type(self):
		required_side = {"Discount Account": "Selling", "Provisional Account": "Buying"}.get(self.rule_type)
		if required_side and required_side != self.selling_or_buying:
			frappe.throw(
				_("Rule Type {0} can only be used for {1}.").format(
					frappe.bold(_(self.rule_type)), frappe.bold(_(required_side))
				)
			)

	def validate_value(self):
		doctype = "Cost Center" if self.rule_type == "Cost Center" else "Account"
		value = self.get(frappe.scrub(doctype))
		if not value:  # Frappe does not enforce `mandatory_depends_on` on the server
			frappe.throw(_("Please set the {0}.").format(_(doctype)))

		company, is_group = frappe.get_cached_value(doctype, value, ["company", "is_group"])
		if company != self.company:
			frappe.throw(_("{0} {1} does not belong to company {2}.").format(_(doctype), value, self.company))

		if is_group:
			frappe.throw(_("{0} {1} is a group.").format(_(doctype), value))

		if self.rule_type in ("Income Account", "Expense Account"):
			expected_root_type = self.rule_type.split(" ")[0]
			if frappe.get_cached_value("Account", value, "root_type") != expected_root_type:
				frappe.throw(_("Account must have root type {0}.").format(frappe.bold(_(expected_root_type))))

	def validate_conditions(self):
		if not self.conditions:
			return

		try:
			frappe.safe_eval(self.conditions, None, {})  # same restricted compiler as at runtime
		except SyntaxError:
			frappe.throw(_("Conditions must be a valid Python expression."), title=_("Invalid Conditions"))
		except Exception:
			pass  # e.g. NameError: field names are only known per document

	def validate_conflicting_rules(self):
		"""Rules with the same filters and priority would make the result arbitrary."""
		filters = {
			fieldname: self.get(fieldname) or ["is", "not set"]
			for fieldname in (*FILTER_WEIGHTS, "for_doctype", "conditions")
		}
		filters.update(
			company=self.company,
			selling_or_buying=self.selling_or_buying,
			rule_type=self.rule_type,
			priority=self.priority,
			name=["!=", self.name],
		)

		conflicting_rules = frappe.get_all("Account Assignment Rule", filters=filters, pluck="name")
		if conflicting_rules:
			frappe.throw(
				_("Conflicting rules found with the same filters and priority: {0}").format(
					", ".join(get_link_to_form("Account Assignment Rule", name) for name in conflicting_rules)
				),
				title=_("Conflicting Rules"),
				exc=ConflictingRuleError,
			)


def get_side(controller: type) -> str | None:
	if issubclass(controller, SellingController):
		return "Selling"
	if issubclass(controller, BuyingController):
		return "Buying"
	return None


def get_applicable_rules(doc: Document, side: str) -> list[frappe._dict]:
	"""Return the rules whose document-level filters (company, side, DocType, conditions) match `doc`
	and whose target field exists in its item rows."""
	if (
		doc.get("is_return")
		and doc.get("return_against")
		and not frappe.db.get_single_value(
			"ERPNext Germany Settings", "apply_account_assignment_rules_to_returns"
		)
	):
		return []

	rules = frappe.get_all(
		"Account Assignment Rule",
		filters={"company": doc.get("company"), "selling_or_buying": side},
		fields=[
			"name",
			"title",
			"rule_type",
			"account",
			"cost_center",
			"priority",
			"for_doctype",
			"conditions",
			"creation",
			*FILTER_WEIGHTS,
		],
	)
	if not rules:
		return []

	row_meta = frappe.get_meta(frappe.get_meta(doc.get("doctype")).get_field("items").options)
	eval_locals = doc.as_dict()

	applicable_rules = []
	for rule in rules:
		if not row_meta.has_field(TARGET_FIELDS[rule.rule_type]):
			continue

		if rule.for_doctype and rule.for_doctype != doc.get("doctype"):
			continue

		if rule.conditions and not conditions_match(rule, eval_locals):
			continue

		rule.specificity = (
			sum(weight for fieldname, weight in FILTER_WEIGHTS.items() if rule.get(fieldname))
			+ bool(rule.for_doctype)
			+ bool(rule.conditions)
		)
		applicable_rules.append(rule)

	return applicable_rules


def conditions_match(rule: frappe._dict, doc: dict) -> bool:
	try:
		return bool(frappe.safe_eval(rule.conditions, None, doc))
	except NameError:
		return False  # the DocType lacks a field used in the conditions, e.g. a custom field of another one
	except Exception:
		frappe.log_error(
			title=_("Account Assignment Rule {0}: invalid conditions").format(rule.name),
			reference_doctype="Account Assignment Rule",
			reference_name=rule.name,
		)
		return False


def get_criteria(doc: Document, row: Document) -> dict:
	"""Return the values the row-level filters of a rule are compared against."""
	item_code = row.get("item_code")
	customer = doc.get("customer")
	supplier = doc.get("supplier")
	customer_group = frappe.get_cached_value("Customer", customer, "customer_group") if customer else None
	supplier_group = frappe.get_cached_value("Supplier", supplier, "supplier_group") if supplier else None
	taxes_and_charges = doc.get("taxes_and_charges")

	return {
		"filter_item": item_code,
		"filter_item_group": frappe.get_cached_value("Item", item_code, "item_group"),
		"filter_item_tax_template": row.get("item_tax_template"),
		"filter_tax_category": doc.get("tax_category"),
		"filter_customer": customer,
		"filter_customer_group": customer_group,
		"filter_supplier": supplier,
		"filter_supplier_group": supplier_group,
		# A rule only has the template field of its own side filled
		"filter_sales_taxes_and_charges_template": taxes_and_charges,
		"filter_purchase_taxes_and_charges_template": taxes_and_charges,
	}


def get_matching_rules(rules: list[frappe._dict], criteria: dict) -> list[frappe._dict]:
	"""Return the rules whose filled filters all match. Best first: priority, specificity, newest."""
	matching_rules = [
		rule
		for rule in rules
		if all(
			not rule.get(fieldname) or rule.get(fieldname) == criteria[fieldname]
			for fieldname in FILTER_WEIGHTS
		)
	]
	return sorted(
		matching_rules, key=lambda rule: (rule.priority, rule.specificity, rule.creation), reverse=True
	)


def get_rule_values(rules: list[frappe._dict], doc: Document, row: Document) -> dict:
	"""Return {row fieldname: value} of the winning rule per Rule Type."""
	values = {}
	for rule in get_matching_rules(rules, get_criteria(doc, row)):
		values.setdefault(TARGET_FIELDS[rule.rule_type], rule.account or rule.cost_center)

	return values


def apply_account_assignment_rules(doc: Document, method: str | None = None, **kwargs) -> None:
	"""Set accounts and cost centers of the item rows from matching rules.

	Runs for all DocTypes on `before_validate` and after `process_item_selection`, which fills a row
	as soon as an item is picked in the form.
	"""
	side = get_side(type(doc))
	if not side or not doc.get("items"):
		return

	rules = get_applicable_rules(doc, side)
	if not rules:
		return

	for row in doc.items:
		if not row.item_code:
			continue

		# ponytail: a row added via API without `item_tax_template` gets it from ERPNext during validate,
		# so an Item Tax Template rule only applies from the next save on. The form always sends it.
		row.update(get_rule_values(rules, doc, row))
