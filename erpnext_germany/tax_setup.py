"""German VAT setup for one company.

Creates Tax Categories, Sales Taxes and Charges Templates, Item Tax Templates, Tax Rules and
Item Group tax rows. The Item Tax Template is the per-line tax key: rate, e-invoice VAT category
and exemption reason. The Item Group rows pick the key per Tax Category, so one tax class
(e.g. "Ware Standard") resolves to different keys for domestic, EU and non-EU customers.

Small businesses (§ 19 UStG) charge no VAT at all, so the item dimension plays no role. They get
one Sales Taxes and Charges Template without rows instead, see `TaxSetup.run_small_business`.

Create-only: records that already exist are reported and left alone, so users can adapt
everything afterwards and run the setup again to add what is missing.
"""

import frappe
from erpnext.accounts.doctype.tax_rule.tax_rule import ConflictingTaxRule
from erpnext.edi.doctype.code_list.code_list import get_codes_for, resolve_code_list
from frappe import _, _lt
from frappe.utils.nestedset import get_root_of

INLAND = "Inland"
EU_BUSINESS = "EU Unternehmen (Reverse Charge)"
THIRD_COUNTRY = "Drittland"
SMALL_BUSINESS = "Kleinunternehmer"
SMALL_BUSINESS_TEXT = "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet."

# Tax accounts: label and account numbers in SKR03 / SKR04. Several numbers: DATEV's first, then
# the one ERPNext's company setup creates when its chart lacks the account
# (erpnext/setup/setup_wizard/data/country_wise_tax.json).
SALES_ACCOUNTS = {
	"vat_standard_account": {"label": _lt("VAT 19 %"), "SKR03": ["1776"], "SKR04": ["3806"]},
	"vat_reduced_account": {"label": _lt("VAT 7 %"), "SKR03": ["1771"], "SKR04": ["3801"]},
}
# Purchase rows add input VAT and deduct the VAT the buyer owes itself (intra-EU acquisition,
# § 13b), so both cancel out on the invoice but are booked for the VAT return.
PURCHASE_ACCOUNTS = {
	"input_vat_standard_account": {
		"label": _lt("Input VAT 19 %"),
		"SKR03": ["1576"],
		"SKR04": ["1406"],
		"add_deduct_tax": "Add",
	},
	"input_vat_reduced_account": {
		"label": _lt("Input VAT 7 %"),
		"SKR03": ["1571"],
		"SKR04": ["1401"],
		"add_deduct_tax": "Add",
	},
	"ige_vat_standard_account": {
		"label": _lt("VAT on Intra-EU Acquisitions 19 %"),
		"SKR03": ["1774"],
		"SKR04": ["3804"],
		"add_deduct_tax": "Deduct",
	},
	"ige_vat_reduced_account": {
		"label": _lt("VAT on Intra-EU Acquisitions 7 %"),
		"SKR03": ["1772"],
		"SKR04": ["3802"],
		"add_deduct_tax": "Deduct",
	},
	"ige_input_vat_standard_account": {
		"label": _lt("Input VAT on Intra-EU Acquisitions 19 %"),
		"SKR03": ["1574"],
		"SKR04": ["1404"],
		"add_deduct_tax": "Add",
	},
	"ige_input_vat_reduced_account": {
		"label": _lt("Input VAT on Intra-EU Acquisitions 7 %"),
		"SKR03": ["1572"],
		"SKR04": ["1402"],
		"add_deduct_tax": "Add",
	},
	"rc_vat_standard_account": {
		"label": _lt("VAT under § 13b UStG 19 %"),
		"SKR03": ["1787"],
		"SKR04": ["3837"],
		"add_deduct_tax": "Deduct",
	},
	"rc_vat_reduced_account": {
		"label": _lt("VAT under § 13b UStG 7 %"),
		"SKR03": ["1785"],
		"SKR04": ["3835"],
		"add_deduct_tax": "Deduct",
	},
	"rc_input_vat_standard_account": {
		"label": _lt("Input VAT under § 13b UStG 19 %"),
		"SKR03": ["1577", "1540"],
		"SKR04": ["1407", "1540"],
		"add_deduct_tax": "Add",
	},
	"rc_input_vat_reduced_account": {
		"label": _lt("Input VAT under § 13b UStG 7 %"),
		"SKR03": ["1578", "1541"],
		"SKR04": ["1408", "1541"],
		"add_deduct_tax": "Add",
	},
}
ACCOUNTS = SALES_ACCOUNTS | PURCHASE_ACCOUNTS

# Rate on the Sales / Purchase Taxes and Charges Template row. Lines with an Item Tax Template
# take the template's rate (or N/A); a line that got none falls back to this. 19 instead of 0, so
# a gap in the setup shows up as too much VAT instead of silently none. Only the standard
# accounts: a reduced fallback would add up to 26 %.
FALLBACK_RATES = {"vat_standard_account": 19, "input_vat_standard_account": 19}

# Item Tax Templates: rate per account (all other accounts are Not Applicable),
# e-invoice VAT category (UNTDID 5305), exemption reason code (VATEX) and text.
# One template serves sales and purchases: the Taxes and Charges Template of the document picks
# the accounts, so sales rows ignore the purchase accounts and vice versa. Cross-border sales are
# 0 % at any rate, but purchases owe the item's rate, hence one template per rate there.
IGE_TEXT = "Steuerfreie innergemeinschaftliche Lieferung nach § 4 Nr. 1b i. V. m. § 6a UStG"
RC_TEXT = "Steuerschuldnerschaft des Leistungsempfängers (Reverse Charge)"
THIRD_COUNTRY_SERVICE_TEXT = "Im Inland nicht steuerbare Leistung"
ITEM_TAX_TEMPLATES = {
	"Inland Standard": {
		"rates": {"vat_standard_account": 19, "input_vat_standard_account": 19},
		"category": "S",
	},
	"Inland Ermäßigt": {"rates": {"vat_reduced_account": 7, "input_vat_reduced_account": 7}, "category": "S"},
	"Steuerfrei": {"category": "E", "text": "Steuerfreier Umsatz nach § 4 UStG"},
	"Innergemeinschaftliche Lieferung/Erwerb Standard": {
		"rates": {"ige_vat_standard_account": 19, "ige_input_vat_standard_account": 19},
		"category": "K",
		"vatex": "VATEX-EU-IC",
		"text": IGE_TEXT,
	},
	"Innergemeinschaftliche Lieferung/Erwerb Ermäßigt": {
		"rates": {"ige_vat_reduced_account": 7, "ige_input_vat_reduced_account": 7},
		"category": "K",
		"vatex": "VATEX-EU-IC",
		"text": IGE_TEXT,
	},
	"Innergemeinschaftliche Lieferung/Erwerb Steuerfrei": {
		"category": "K",
		"vatex": "VATEX-EU-IC",
		"text": IGE_TEXT,
	},
	"Reverse Charge Leistung EU Standard": {
		"rates": {"rc_vat_standard_account": 19, "rc_input_vat_standard_account": 19},
		"category": "AE",
		"vatex": "VATEX-EU-AE",
		"text": RC_TEXT,
	},
	"Reverse Charge Leistung EU Ermäßigt": {
		"rates": {"rc_vat_reduced_account": 7, "rc_input_vat_reduced_account": 7},
		"category": "AE",
		"vatex": "VATEX-EU-AE",
		"text": RC_TEXT,
	},
	# ponytail: import VAT is paid to customs, not on the supplier's invoice, so no purchase rates
	"Ausfuhrlieferung/Einfuhr": {
		"category": "G",
		"vatex": "VATEX-EU-G",
		"text": "Steuerfreie Ausfuhrlieferung nach § 4 Nr. 1a i. V. m. § 6 UStG",
	},
	"Leistung Drittland Standard": {
		"rates": {"rc_vat_standard_account": 19, "rc_input_vat_standard_account": 19},
		"category": "O",
		"vatex": "VATEX-EU-O",
		"text": THIRD_COUNTRY_SERVICE_TEXT,
	},
	"Leistung Drittland Ermäßigt": {
		"rates": {"rc_vat_reduced_account": 7, "rc_input_vat_reduced_account": 7},
		"category": "O",
		"vatex": "VATEX-EU-O",
		"text": THIRD_COUNTRY_SERVICE_TEXT,
	},
	"Leistung Drittland Steuerfrei": {
		"category": "O",
		"vatex": "VATEX-EU-O",
		"text": THIRD_COUNTRY_SERVICE_TEXT,
	},
}

# Tax class (a set of Item Group rows) -> Item Tax Template per Tax Category.
TAX_CLASSES = {
	"Ware Standard": {
		INLAND: "Inland Standard",
		EU_BUSINESS: "Innergemeinschaftliche Lieferung/Erwerb Standard",
		THIRD_COUNTRY: "Ausfuhrlieferung/Einfuhr",
	},
	"Ware Ermäßigt": {
		INLAND: "Inland Ermäßigt",
		EU_BUSINESS: "Innergemeinschaftliche Lieferung/Erwerb Ermäßigt",
		THIRD_COUNTRY: "Ausfuhrlieferung/Einfuhr",
	},
	"Ware Steuerfrei": {
		INLAND: "Steuerfrei",
		EU_BUSINESS: "Innergemeinschaftliche Lieferung/Erwerb Steuerfrei",
		THIRD_COUNTRY: "Ausfuhrlieferung/Einfuhr",
	},
	"Leistung Standard": {
		INLAND: "Inland Standard",
		EU_BUSINESS: "Reverse Charge Leistung EU Standard",
		THIRD_COUNTRY: "Leistung Drittland Standard",
	},
	"Leistung Ermäßigt": {
		INLAND: "Inland Ermäßigt",
		EU_BUSINESS: "Reverse Charge Leistung EU Ermäßigt",
		THIRD_COUNTRY: "Leistung Drittland Ermäßigt",
	},
	"Leistung Steuerfrei": {
		INLAND: "Steuerfrei",
		EU_BUSINESS: "Steuerfrei",
		THIRD_COUNTRY: "Leistung Drittland Steuerfrei",
	},
}

# Taxes and Charges Template per side: doctype, field on Tax Rule, accounts.
TEMPLATE_TYPES = {
	"Sales": ("Sales Taxes and Charges Template", "sales_tax_template", SALES_ACCOUNTS),
	"Purchase": ("Purchase Taxes and Charges Template", "purchase_tax_template", PURCHASE_ACCOUNTS),
}

VAT_CATEGORY_CODE_LISTS = ["urn:xoev-de:kosit:codeliste:untdid.5305", "urn:cef.eu:names:identifier:5305"]
VATEX_CODE_LISTS = ["urn:xoev-de:kosit:codeliste:vatex", "urn:cef.eu:names:identifier:VATEX"]


@frappe.whitelist()
def get_defaults(company: str | None = None) -> dict:
	"""Prefill the setup dialog: account labels, the company's VAT accounts (by SKR number) and the
	root Item Group."""
	frappe.only_for("System Manager")
	return {
		"sales_accounts": {key: str(account["label"]) for key, account in SALES_ACCOUNTS.items()},
		"purchase_accounts": {key: str(account["label"]) for key, account in PURCHASE_ACCOUNTS.items()},
		"accounts": find_vat_accounts(company) if company else {},
		"root_item_group": get_root_of("Item Group"),
		"tax_classes": list(TAX_CLASSES),
	}


def find_vat_accounts(company: str) -> dict:
	chart_of_accounts = frappe.db.get_value("Company", company, "chart_of_accounts") or ""
	chart = next((skr for skr in ("SKR03", "SKR04") if skr in chart_of_accounts), None)
	if not chart:
		return {key: None for key in ACCOUNTS}

	return {key: find_account(company, account[chart]) for key, account in ACCOUNTS.items()}


def find_account(company: str, numbers: list[str]) -> str | None:
	for number in numbers:
		if account := frappe.db.get_value(
			"Account", {"company": company, "account_number": number, "is_group": 0}
		):
			return account


@frappe.whitelist()
def setup_taxes(
	company: str,
	accounts: str | dict | None = None,
	item_groups: str | list | None = None,
	eu_business: bool = False,
	third_country: bool = False,
	small_business: bool = False,
	dry_run: bool = True,
) -> list[dict]:
	"""Create the tax setup for `company` and return a report of what was (or would be) done.

	`accounts` maps the keys of SALES_ACCOUNTS and PURCHASE_ACCOUNTS to accounts; without purchase
	accounts only sales taxes are set up. `item_groups` is a list of {"item_group": ...,
	"tax_class": ...}. With `small_business`, neither is needed. With `dry_run`, nothing is written.
	"""
	frappe.only_for("System Manager")
	if small_business:
		setup = TaxSetup(company=company, dry_run=dry_run)
		setup.run_small_business()
		return setup.report

	setup = TaxSetup(
		company=company,
		accounts=frappe.parse_json(accounts) or {},
		item_groups=frappe.parse_json(item_groups) or [],
		tax_categories=[INLAND]
		+ ([EU_BUSINESS] if eu_business else [])
		+ ([THIRD_COUNTRY] if third_country else []),
		dry_run=dry_run,
	)
	setup.run()
	return setup.report


class TaxSetup:
	def __init__(
		self,
		company: str,
		accounts: dict | None = None,
		item_groups: list[dict] | None = None,
		tax_categories: list[str] | None = None,
		dry_run: bool = True,
	):
		self.company = company
		self.abbr = frappe.get_cached_value("Company", company, "abbr")
		self.accounts = accounts or {}
		self.item_groups = item_groups or []
		self.tax_categories = tax_categories or []
		self.dry_run = dry_run
		self.report = []
		self.blocked = set()  # (tax_type, Tax Category) whose template another one blocks

	def run(self):
		self.validate()
		self.cells = self.get_cells()
		self.item_tax_templates = sorted(set(self.cells.values()))

		self.make_tax_categories()
		self.set_account_types()
		self.make_item_tax_templates()
		for tax_type in self.tax_types:
			self.make_tax_templates(tax_type)
			self.make_tax_rules(tax_type)
		self.make_item_group_rows()
		self.link_common_codes()
		self.update_settings()

	def run_small_business(self):
		"""§ 19 UStG: one Sales Taxes and Charges Template without rows for customers without Tax Category.

		For e-invoices it carries the VAT category E. Its `tax_exemption_reason` is fetched into the
		invoice, printed, and used by eu_einvoice as the exemption text (BT-120), since no line has an
		Item Tax Template.
		"""
		template = f"{SMALL_BUSINESS} - {self.abbr}"
		if frappe.db.exists("Sales Taxes and Charges Template", template):
			self.add("exists", "Sales Taxes and Charges Template", template)
		else:
			self.add("create", "Sales Taxes and Charges Template", template)
			self.insert(
				{
					"doctype": "Sales Taxes and Charges Template",
					"title": SMALL_BUSINESS,
					"company": self.company,
					"tax_exemption_reason": SMALL_BUSINESS_TEXT,
				}
			)

		self.make_tax_rule(template)
		if code_list := self.get_code_list(VAT_CATEGORY_CODE_LISTS):
			self.link_common_code(code_list, "E", "Sales Taxes and Charges Template", template)

	def validate(self):
		for key, account in SALES_ACCOUNTS.items():
			if not self.accounts.get(key):
				frappe.throw(_("Please select the account {0}.").format(account["label"]))

		purchase_accounts = [self.accounts.get(key) for key in PURCHASE_ACCOUNTS]
		if any(purchase_accounts) and not all(purchase_accounts):
			frappe.throw(_("Please select all purchase accounts, or none to set up sales taxes only."))

		self.accounts = {key: account for key, account in self.accounts.items() if account}
		self.tax_types = ["Sales", "Purchase"] if all(purchase_accounts) else ["Sales"]
		for account in self.accounts.values():
			if frappe.db.get_value("Account", account, "company") != self.company:
				frappe.throw(_("Account {0} does not belong to company {1}.").format(account, self.company))

		if len(set(self.accounts.values())) < len(self.accounts):
			frappe.throw(_("Please select a different account for each tax."))

		item_groups = [row["item_group"] for row in self.item_groups]
		for row in self.item_groups:
			if row.get("tax_class") not in TAX_CLASSES:
				frappe.throw(_("Unknown tax class: {0}").format(row.get("tax_class")))
			if item_groups.count(row["item_group"]) > 1:
				frappe.throw(_("Item Group {0} is listed more than once.").format(row["item_group"]))

	def get_cells(self) -> dict[tuple[str, str], str]:
		"""(item_group, tax_category) -> Item Tax Template title."""
		cells = {}
		for row in self.item_groups:
			for category in self.tax_categories:
				cells[(row["item_group"], category)] = TAX_CLASSES[row["tax_class"]][category]
		return cells

	def add(self, action: str, doctype: str, name: str, message: str = ""):
		self.report.append({"action": action, "doctype": doctype, "name": name, "message": message})

	def insert(self, doc: dict):
		if not self.dry_run:
			frappe.get_doc(doc).insert()

	def make_tax_categories(self):
		for category in self.tax_categories:
			if frappe.db.exists("Tax Category", category):
				self.add("exists", "Tax Category", category)
				continue

			self.add("create", "Tax Category", category)
			self.insert({"doctype": "Tax Category", "title": category})

	def set_account_types(self):
		"""Item Tax Templates need accounts of type Tax. ERPNext's company setup creates some German
		VAT accounts (e.g. intra-EU acquisition, § 13b) without a type."""
		for account in self.accounts.values():
			if frappe.db.get_value("Account", account, "account_type"):
				continue

			self.add("change", "Account", account, _("Account Type: Tax"))
			if not self.dry_run:
				doc = frappe.get_doc("Account", account)
				doc.account_type = "Tax"
				doc.save()

	def make_item_tax_templates(self):
		has_text_field = frappe.get_meta("Item Tax Template").has_field("vat_exemption_reason_text")
		for title in self.item_tax_templates:
			name = f"{title} - {self.abbr}"
			if frappe.db.exists("Item Tax Template", name):
				existing = frappe.get_all("Item Tax Template Detail", {"parent": name}, pluck="tax_type")
				self.add_exists_or_missing_rows("Item Tax Template", name, self.accounts.values(), existing)
				continue

			self.add("create", "Item Tax Template", name)
			definition = ITEM_TAX_TEMPLATES[title]
			rates = definition.get("rates", {})
			doc = {
				"doctype": "Item Tax Template",
				"title": title,
				"company": self.company,
				"taxes": [
					{
						"tax_type": account,
						"tax_rate": rates.get(key, 0),
						"not_applicable": key not in rates,
					}
					for key, account in self.accounts.items()
				],
			}
			if has_text_field and definition.get("text"):
				doc["vat_exemption_reason_text"] = definition["text"]
			self.insert(doc)

	def add_exists_or_missing_rows(self, doctype: str, name: str, accounts, existing: list[str]):
		if missing := [account for account in accounts if account not in existing]:
			self.add("conflict", doctype, name, _("Missing tax rows: {0}").format(", ".join(missing)))
		else:
			self.add("exists", doctype, name)

	def make_tax_templates(self, tax_type: str):
		doctype, _rule_field, account_definitions = TEMPLATE_TYPES[tax_type]
		for category in self.tax_categories:
			name = f"{category} - {self.abbr}"
			accounts = self.get_taxed_accounts(category, account_definitions)
			if frappe.db.exists(doctype, name):
				# Without the row, lines with that rate get no tax (add_taxes_from_item_tax_template = 0)
				existing = frappe.get_all(
					f"{tax_type} Taxes and Charges",
					{"parent": name, "parenttype": doctype},
					pluck="account_head",
				)
				self.add_exists_or_missing_rows(doctype, name, accounts.values(), existing)
				continue

			# ERPNext allows only one enabled template per company and Tax Category
			if other := frappe.db.get_value(
				doctype, {"company": self.company, "tax_category": category, "disabled": 0}
			):
				self.blocked.add((tax_type, category))
				self.add(
					"conflict",
					doctype,
					name,
					_("Not created: {0} already uses Tax Category {1}.").format(other, category),
				)
				continue

			self.add("create", doctype, name)
			self.insert(
				{
					"doctype": doctype,
					"title": category,
					"company": self.company,
					"tax_category": category,
					"taxes": [
						{
							"charge_type": "On Net Total",
							"account_head": account,
							"description": frappe.db.get_value("Account", account, "account_name"),
							"rate": FALLBACK_RATES.get(key, 0),
							# Purchase rows only (input VAT adds, self-assessed VAT deducts)
							"add_deduct_tax": account_definitions[key].get("add_deduct_tax"),
						}
						for key, account in accounts.items()
					],
				}
			)

	def get_taxed_accounts(self, category: str, account_definitions: dict) -> dict[str, str]:
		"""Accounts of one side that any tax class can charge a rate on for `category`.

		Independent of this run's Item Groups, so a class added in a later run finds its row.
		"""
		keys = {
			key
			for templates in TAX_CLASSES.values()
			for key in ITEM_TAX_TEMPLATES[templates[category]].get("rates", {})
			if key in account_definitions
		}
		return {key: account for key, account in self.accounts.items() if key in keys}

	def make_tax_rules(self, tax_type: str):
		for category in self.tax_categories:
			if (tax_type, category) not in self.blocked:
				self.make_tax_rule(f"{category} - {self.abbr}", category, tax_type)

	def make_tax_rule(self, template: str, category: str | None = None, tax_type: str = "Sales"):
		"""Without `category`, the rule matches only documents without a Tax Category."""
		template_field = TEMPLATE_TYPES[tax_type][1]
		label = f"{tax_type}: {category or template}"
		rules = frappe.get_all(
			"Tax Rule",
			filters={
				"company": self.company,
				"tax_type": tax_type,
				"tax_category": category or ("is", "not set"),
			},
			fields=["name", template_field],
		)
		if any(rule[template_field] == template for rule in rules):
			self.add("exists", "Tax Rule", label)
			return

		for rule in rules:
			self.add(
				"conflict",
				"Tax Rule",
				rule.name,
				_("Applies to the same parties. If it has more filters set, it wins over ours."),
			)

		self.add("create", "Tax Rule", label, template)
		# Tax Rule.insert() fills blank fields from Global Defaults, which narrows the rule down
		# to almost never matching. in_import skips that.
		in_import = frappe.flags.in_import
		frappe.flags.in_import = True
		try:
			self.insert(
				{
					"doctype": "Tax Rule",
					"tax_type": tax_type,
					"tax_category": category,
					template_field: template,
					"company": self.company,
					"priority": 1,
				}
			)
		except ConflictingTaxRule:
			frappe.clear_last_message()
			self.report[-1].update(
				action="conflict", message=_("Not created, an existing Tax Rule has the same filters.")
			)
		finally:
			frappe.flags.in_import = in_import

	def make_item_group_rows(self):
		for item_group in {item_group for item_group, _category in self.cells}:
			doc = frappe.get_doc("Item Group", item_group)
			existing = {
				row.tax_category: row.item_tax_template
				for row in doc.taxes
				if frappe.get_cached_value("Item Tax Template", row.item_tax_template, "company")
				== self.company
			}
			added_rows = False
			for (cell_item_group, category), title in self.cells.items():
				if cell_item_group != item_group:
					continue

				template = f"{title} - {self.abbr}"
				label = f"{category} → {template}"
				if existing.get(category) == template:
					self.add("exists", "Item Group", item_group, label)
				elif category in existing:
					self.add("conflict", "Item Group", item_group, f"{category} → {existing[category]}")
				else:
					self.add("create", "Item Group", item_group, label)
					doc.append("taxes", {"item_tax_template": template, "tax_category": category})
					added_rows = True

			if added_rows and not self.dry_run:
				doc.save()

	def link_common_codes(self):
		"""Point the e-invoice code lists (imported by eu_einvoice) at our Item Tax Templates."""
		for code_lists, field in ((VAT_CATEGORY_CODE_LISTS, "category"), (VATEX_CODE_LISTS, "vatex")):
			code_list = self.get_code_list(code_lists)
			if not code_list:
				continue

			for title in self.item_tax_templates:
				if code := ITEM_TAX_TEMPLATES[title].get(field):
					self.link_common_code(code_list, code, "Item Tax Template", f"{title} - {self.abbr}")

	def get_code_list(self, code_lists: list[str]) -> str | None:
		code_list = next(filter(None, map(resolve_code_list, code_lists)), None)
		if not code_list:
			self.add("skipped", "Code List", code_lists[0], _("Install eu_einvoice and run again."))
		return code_list

	def link_common_code(self, code_list: str, code: str, link_doctype: str, link_name: str):
		if get_codes_for(code_list, link_doctype, link_name):
			self.add("exists", "Common Code", code, link_name)
			return

		common_code = frappe.db.get_value("Common Code", {"code_list": code_list, "common_code": code})
		if not common_code:
			self.add("skipped", "Common Code", code, _("Not found in {0}").format(code_list))
			return

		self.add("create", "Common Code", code, link_name)
		if not self.dry_run:
			doc = frappe.get_doc("Common Code", common_code)
			doc.append("applies_to", {"link_doctype": link_doctype, "link_name": link_name})
			doc.save()

	def update_settings(self):
		"""Rows come from the Sales Taxes and Charges Template, rates from the Item Tax Template.
		Parties and invoices without Tax Category get no taxes, so warn about them."""
		for doctype, field, value in (
			("Accounts Settings", "add_taxes_from_item_tax_template", 0),
			("Accounts Settings", "add_taxes_from_taxes_and_charges_template", 1),
			("ERPNext Germany Settings", "warn_if_tax_category_missing", 1),
		):
			if frappe.db.get_single_value(doctype, field) == value:
				continue

			self.add("change", doctype, field, str(value))
			if not self.dry_run:
				frappe.db.set_single_value(doctype, field, value)
