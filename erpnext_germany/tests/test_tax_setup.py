import frappe
from frappe.utils import today

from erpnext_germany.tax_setup import (
	EU_BUSINESS,
	INLAND,
	SALES_ACCOUNTS,
	SMALL_BUSINESS,
	SMALL_BUSINESS_TEXT,
	THIRD_COUNTRY,
	TaxSetup,
	find_vat_accounts,
)
from erpnext_germany.tests.utils import ERPNextGermanyTestSuite

COMPANY = "_Test Steuer GmbH"


class TestTaxSetup(ERPNextGermanyTestSuite):
	def setUp(self):
		make_company()
		self.abbr = frappe.db.get_value("Company", COMPANY, "abbr")
		self.root_item_group = frappe.db.get_value("Item Group", {"is_group": 1, "parent_item_group": ""})
		make_item_group("_Test Bücher")
		make_item_group("_Test Beratung")

	def run_setup(
		self, dry_run=False, tax_categories=(INLAND, EU_BUSINESS, THIRD_COUNTRY), item_groups=None, **kwargs
	) -> list[dict]:
		setup = TaxSetup(
			company=COMPANY,
			accounts=find_vat_accounts(COMPANY),
			item_groups=item_groups
			or [
				{"item_group": self.root_item_group, "tax_class": "Ware Standard"},
				{"item_group": "_Test Bücher", "tax_class": "Ware Ermäßigt"},
				{"item_group": "_Test Beratung", "tax_class": "Leistung Standard"},
			],
			tax_categories=list(tax_categories),
			dry_run=dry_run,
			**kwargs,
		)
		setup.run()
		return setup.report

	def test_finds_skr04_accounts(self):
		accounts = find_vat_accounts(COMPANY)
		self.assertEqual(
			frappe.db.get_value("Account", accounts["vat_standard_account"], "account_number"), "3806"
		)
		self.assertEqual(
			frappe.db.get_value("Account", accounts["vat_reduced_account"], "account_number"), "3801"
		)
		# Created by ERPNext's company setup, found under DATEV's number
		self.assertEqual(
			frappe.db.get_value("Account", accounts["rc_input_vat_standard_account"], "account_number"),
			"1407",
		)
		self.assertTrue(all(accounts.values()))

	def test_dry_run_writes_nothing(self):
		before = get_snapshot()
		report = self.run_setup(dry_run=True)

		self.assertIn(("create", "Item Tax Template", f"Inland Standard - {self.abbr}"), actions(report))
		self.assertEqual(get_snapshot(), before)

	def test_small_business_dry_run_writes_nothing(self):
		before = get_snapshot()
		setup = TaxSetup(company=COMPANY, dry_run=True)
		setup.run_small_business()

		self.assertIn(
			("create", "Sales Taxes and Charges Template", f"{SMALL_BUSINESS} - {self.abbr}"),
			actions(setup.report),
		)
		self.assertEqual(get_snapshot(), before)

	def test_invalid_input_is_rejected_before_writing(self):
		accounts = find_vat_accounts(COMPANY)
		same_account = TaxSetup(
			company=COMPANY,
			accounts={key: accounts["vat_standard_account"] for key in accounts},
			tax_categories=[INLAND],
		)
		self.assertRaises(frappe.ValidationError, same_account.run)

		duplicate_group = TaxSetup(
			company=COMPANY,
			accounts=accounts,
			item_groups=[
				{"item_group": "_Test Bücher", "tax_class": "Ware Standard"},
				{"item_group": "_Test Bücher", "tax_class": "Ware Ermäßigt"},
			],
			tax_categories=[INLAND],
		)
		self.assertRaises(frappe.ValidationError, duplicate_group.run)

	def test_setup_is_idempotent(self):
		self.run_setup()
		second_report = self.run_setup()

		self.assertFalse([row for row in second_report if row["action"] in ("create", "conflict", "change")])

	def test_item_tax_templates(self):
		self.run_setup()

		regelsatz = frappe.get_doc("Item Tax Template", f"Inland Standard - {self.abbr}")
		accounts = find_vat_accounts(COMPANY)

		self.assertEqual(
			{
				(row.tax_type, row.tax_rate, row.not_applicable)
				for row in regelsatz.taxes
				if not row.not_applicable
			},
			{(accounts["vat_standard_account"], 19, 0), (accounts["input_vat_standard_account"], 19, 0)},
		)
		self.assertEqual(len(regelsatz.taxes), len(accounts))

		ausfuhr = frappe.get_doc("Item Tax Template", f"Ausfuhrlieferung/Einfuhr - {self.abbr}")
		self.assertTrue(all(row.not_applicable for row in ausfuhr.taxes))

	def test_invoice_per_tax_category(self):
		self.run_setup()
		goods = make_item("_Test Ware", self.root_item_group)
		book = make_item("_Test Buch", "_Test Bücher")
		consulting = make_item("_Test Beratungsstunde", "_Test Beratung")

		domestic = make_invoice(make_customer("_Test Kunde Inland", INLAND), [goods, book, consulting])
		self.assertEqual(domestic.taxes_and_charges, f"{INLAND} - {self.abbr}")
		self.assertEqual(
			[row.item_tax_template for row in domestic.items],
			[
				f"Inland Standard - {self.abbr}",
				f"Inland Ermäßigt - {self.abbr}",
				f"Inland Standard - {self.abbr}",
			],
		)
		self.assertEqual(domestic.total_taxes_and_charges, 19 + 7 + 19)
		# Not Applicable keeps each line out of the other rate's basis
		self.assertEqual(sorted(row.net_amount for row in domestic.taxes), [100, 200])

		eu = make_invoice(make_customer("_Test Kunde EU", EU_BUSINESS), [goods, consulting])
		self.assertEqual(eu.taxes_and_charges, f"{EU_BUSINESS} - {self.abbr}")
		self.assertEqual(
			[row.item_tax_template for row in eu.items],
			[
				f"Innergemeinschaftliche Lieferung/Erwerb Standard - {self.abbr}",
				f"Reverse Charge Leistung EU Standard - {self.abbr}",
			],
		)
		self.assertEqual(eu.total_taxes_and_charges, 0)

		export = make_invoice(make_customer("_Test Kunde Drittland", THIRD_COUNTRY), [goods, consulting])
		self.assertEqual(
			[row.item_tax_template for row in export.items],
			[f"Ausfuhrlieferung/Einfuhr - {self.abbr}", f"Leistung Drittland Standard - {self.abbr}"],
		)

	def test_exemption_reason_from_item_tax_templates(self):
		if not frappe.get_meta("Item Tax Template").has_field("vat_exemption_reason_text"):
			self.skipTest("eu_einvoice with the exemption text field is not installed")

		self.run_setup()
		goods = make_item("_Test Ware", self.root_item_group)
		consulting = make_item("_Test Beratungsstunde", "_Test Beratung")

		eu = make_invoice(make_customer("_Test Kunde EU", EU_BUSINESS), [goods, consulting])
		self.assertEqual(
			eu.tax_exemption_reason.splitlines(),
			[
				"Steuerfreie innergemeinschaftliche Lieferung nach § 4 Nr. 1b i. V. m. § 6a UStG",
				"Steuerschuldnerschaft des Leistungsempfängers (Reverse Charge)",
			],
		)

	def test_small_business(self):
		setup = TaxSetup(company=COMPANY, dry_run=False)
		setup.run_small_business()
		template = f"{SMALL_BUSINESS} - {self.abbr}"
		self.assertIn(("create", "Sales Taxes and Charges Template", template), actions(setup.report))
		self.assertNotIn("Item Tax Template", {row["doctype"] for row in setup.report})
		self.assertNotIn("E Invoice Settings", {row["doctype"] for row in setup.report})
		if frappe.db.exists("DocType", "E Invoice Settings"):
			self.assertTrue(
				frappe.db.exists(
					"Dynamic Link",
					{
						"parenttype": "Common Code",
						"link_doctype": "Sales Taxes and Charges Template",
						"link_name": template,
					},
				)
			)

		# Customers without Tax Category; the item dimension plays no role.
		invoice = make_invoice(
			make_customer("_Test Kunde Inland", None), [make_item("_Test Ware", self.root_item_group)]
		)
		self.assertEqual(invoice.taxes_and_charges, template)
		self.assertFalse(invoice.taxes)
		self.assertFalse(invoice.items[0].item_tax_template)
		self.assertEqual(invoice.tax_exemption_reason, SMALL_BUSINESS_TEXT)

		second_run = TaxSetup(company=COMPANY, dry_run=False)
		second_run.run_small_business()
		self.assertFalse(
			[row for row in second_run.report if row["action"] in ("create", "conflict", "change")]
		)

	def test_existing_item_group_row_is_reported(self):
		self.run_setup(tax_categories=[INLAND])
		frappe.get_doc(
			{
				"doctype": "Item Tax Template",
				"title": "Eigene Vorlage",
				"company": COMPANY,
				"taxes": [{"tax_type": find_vat_accounts(COMPANY)["vat_standard_account"], "tax_rate": 19}],
			}
		).insert()
		item_group = frappe.get_doc("Item Group", "_Test Bücher")
		item_group.taxes = []
		item_group.append(
			"taxes", {"item_tax_template": f"Eigene Vorlage - {self.abbr}", "tax_category": INLAND}
		)
		item_group.save()

		report = self.run_setup()

		self.assertIn(("conflict", "Item Group", "_Test Bücher"), actions(report))
		item_group.reload()
		self.assertEqual(
			[
				(row.tax_category, row.item_tax_template)
				for row in item_group.taxes
				if row.tax_category == INLAND
			],
			[(INLAND, f"Eigene Vorlage - {self.abbr}")],
		)

	def test_foreign_tax_rule_is_reported(self):
		self.run_setup(tax_categories=[INLAND])
		if not frappe.db.exists("Tax Category", EU_BUSINESS):
			frappe.get_doc({"doctype": "Tax Category", "title": EU_BUSINESS}).insert()
		frappe.get_doc(
			{
				"doctype": "Tax Rule",
				"tax_type": "Sales",
				"company": COMPANY,
				"tax_category": EU_BUSINESS,
				"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}),
				"sales_tax_template": f"{INLAND} - {self.abbr}",
			}
		).insert()

		report = self.run_setup()

		self.assertIn(("conflict", "Tax Rule"), [(row["action"], row["doctype"]) for row in report])
		self.assertTrue(
			frappe.db.exists(
				"Tax Rule",
				{
					"company": COMPANY,
					"tax_type": "Sales",
					"tax_category": EU_BUSINESS,
					"sales_tax_template": f"{EU_BUSINESS} - {self.abbr}",
				},
			)
		)

	def test_purchase_invoice_per_tax_category(self):
		"""One Item Tax Template per cell serves both sides: the Purchase Taxes and Charges Template
		picks the purchase accounts, the line's template their rate."""
		self.run_setup()
		accounts = find_vat_accounts(COMPANY)
		goods = make_item("_Test Ware", self.root_item_group)
		book = make_item("_Test Buch", "_Test Bücher")
		consulting = make_item("_Test Beratungsstunde", "_Test Beratung")

		def taxes(invoice):
			return {
				(row.account_head, row.add_deduct_tax): row.tax_amount
				for row in invoice.taxes
				if row.tax_amount
			}

		domestic = make_purchase_invoice(
			make_supplier("_Test Lieferant Inland", INLAND), [goods, book, consulting]
		)
		self.assertEqual(
			taxes(domestic),
			{
				(accounts["input_vat_standard_account"], "Add"): 38,
				(accounts["input_vat_reduced_account"], "Add"): 7,
			},
		)

		eu = make_purchase_invoice(
			make_supplier("_Test Lieferant EU", EU_BUSINESS), [goods, book, consulting]
		)
		self.assertEqual(
			taxes(eu),
			{
				(accounts["ige_vat_standard_account"], "Deduct"): 19,
				(accounts["ige_input_vat_standard_account"], "Add"): 19,
				(accounts["ige_vat_reduced_account"], "Deduct"): 7,
				(accounts["ige_input_vat_reduced_account"], "Add"): 7,
				(accounts["rc_vat_standard_account"], "Deduct"): 19,
				(accounts["rc_input_vat_standard_account"], "Add"): 19,
			},
		)
		self.assertEqual(eu.grand_total, 300)

		non_eu = make_purchase_invoice(
			make_supplier("_Test Lieferant Drittland", THIRD_COUNTRY), [goods, consulting]
		)
		self.assertEqual(
			taxes(non_eu),
			{
				(accounts["rc_vat_standard_account"], "Deduct"): 19,
				(accounts["rc_input_vat_standard_account"], "Add"): 19,
			},
		)

	def test_sales_only_without_purchase_accounts(self):
		accounts = {
			key: account for key, account in find_vat_accounts(COMPANY).items() if key in SALES_ACCOUNTS
		}
		setup = TaxSetup(
			company=COMPANY, accounts=accounts, item_groups=[], tax_categories=[INLAND], dry_run=False
		)
		setup.run()

		self.assertNotIn("Purchase Taxes and Charges Template", {row["doctype"] for row in setup.report})
		self.assertFalse(frappe.db.exists("Tax Rule", {"company": COMPANY, "tax_type": "Purchase"}))

	def test_line_without_item_tax_template_gets_standard_rate(self):
		"""A gap in the setup overcharges visibly instead of silently charging no VAT."""
		self.run_setup(
			tax_categories=[INLAND],
			item_groups=[{"item_group": "_Test Bücher", "tax_class": "Ware Ermäßigt"}],
		)
		goods = make_item("_Test Ware", self.root_item_group)
		book = make_item("_Test Buch", "_Test Bücher")

		invoice = make_invoice(make_customer("_Test Kunde Inland", INLAND), [goods, book])

		self.assertEqual(
			[row.item_tax_template for row in invoice.items], [None, f"Inland Ermäßigt - {self.abbr}"]
		)
		self.assertEqual(invoice.total_taxes_and_charges, 19 + 7)

	def test_incomplete_tax_rows_warning(self):
		frappe.local.message_log = []
		self.run_setup()
		self.assertFalse(get_incomplete_rows_warnings())

		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_Test Leistung mit Ausnahme",
				"item_group": "_Test Bücher",
				"stock_uom": "Nos",
				"taxes": [{"item_tax_template": f"Inland Standard - {self.abbr}", "tax_category": INLAND}],
			}
		).insert()

		self.assertTrue(get_incomplete_rows_warnings())

	def test_class_added_in_a_later_run_is_taxed(self):
		self.run_setup(
			tax_categories=[INLAND],
			item_groups=[{"item_group": self.root_item_group, "tax_class": "Ware Standard"}],
		)
		self.run_setup(tax_categories=[INLAND])

		book = make_item("_Test Buch", "_Test Bücher")
		invoice = make_invoice(make_customer("_Test Kunde Inland", INLAND), [book])
		self.assertEqual(invoice.items[0].item_tax_template, f"Inland Ermäßigt - {self.abbr}")
		self.assertEqual(invoice.total_taxes_and_charges, 7)

	def test_missing_template_row_is_reported(self):
		self.run_setup(tax_categories=[INLAND])
		template = frappe.get_doc("Sales Taxes and Charges Template", f"{INLAND} - {self.abbr}")
		reduced = find_vat_accounts(COMPANY)["vat_reduced_account"]
		template.taxes = [row for row in template.taxes if row.account_head != reduced]
		template.save()

		report = self.run_setup(tax_categories=[INLAND])

		self.assertIn(("conflict", "Sales Taxes and Charges Template", template.name), actions(report))

	def test_template_with_same_tax_category_is_reported(self):
		"""ERPNext allows one enabled template per company and Tax Category: report, don't fail."""
		if not frappe.db.exists("Tax Category", INLAND):
			frappe.get_doc({"doctype": "Tax Category", "title": INLAND}).insert()
		other = (
			frappe.get_doc(
				{
					"doctype": "Sales Taxes and Charges Template",
					"title": "Eigene Inland",
					"company": COMPANY,
					"tax_category": INLAND,
				}
			)
			.insert()
			.name
		)

		for dry_run in (True, False):
			report = self.run_setup(tax_categories=[INLAND], dry_run=dry_run)
			self.assertIn(
				("conflict", "Sales Taxes and Charges Template", f"{INLAND} - {self.abbr}"), actions(report)
			)
			self.assertNotIn(f"Sales: {INLAND}", {row["name"] for row in report})

		self.assertFalse(frappe.db.exists("Sales Taxes and Charges Template", f"{INLAND} - {self.abbr}"))
		self.assertTrue(frappe.db.exists("Sales Taxes and Charges Template", other))

	def test_conflicting_tax_rule_is_reported(self):
		"""A foreign rule with exactly our filters makes ERPNext refuse ours; report it, no error."""
		self.run_setup(tax_categories=[INLAND], dry_run=False)
		ours = frappe.db.get_value(
			"Tax Rule", {"company": COMPANY, "tax_category": INLAND, "tax_type": "Sales"}
		)
		frappe.db.set_value("Tax Rule", ours, "sales_tax_template", f"{EU_BUSINESS} - {self.abbr}")
		frappe.local.message_log = []

		for dry_run in (True, False):
			report = self.run_setup(tax_categories=[INLAND], dry_run=dry_run)
			self.assertIn(("conflict", "Tax Rule", f"Sales: {INLAND}"), actions(report))
			self.assertNotIn(("create", "Tax Rule", f"Sales: {INLAND}"), actions(report))
		self.assertEqual(frappe.get_message_log(), [])

	def test_narrowed_rule_with_our_template_is_not_enough(self):
		"""A rule with our template but an extra filter applies to some parties only."""
		self.run_setup(tax_categories=[INLAND])
		ours = frappe.db.get_value(
			"Tax Rule", {"company": COMPANY, "tax_category": INLAND, "tax_type": "Sales"}
		)
		frappe.db.set_value(
			"Tax Rule", ours, "customer_group", frappe.db.get_value("Customer Group", {"is_group": 0})
		)

		report = self.run_setup(tax_categories=[INLAND])

		self.assertIn(("create", "Tax Rule", f"Sales: {INLAND}"), actions(report))
		self.assertEqual(
			frappe.db.count("Tax Rule", {"company": COMPANY, "tax_category": INLAND, "tax_type": "Sales"}), 2
		)

	def test_missing_tax_category_warning(self):
		warning = "No Tax Category is set, so taxes may not be applied automatically."
		self.run_setup(tax_categories=[INLAND])
		self.assertTrue(
			frappe.db.get_single_value("ERPNext Germany Settings", "warn_if_tax_category_missing")
		)

		frappe.local.message_log = []
		make_customer("_Test Kunde ohne Kategorie", None)
		make_supplier("_Test Lieferant ohne Kategorie", None)
		messages = [message["message"] for message in frappe.get_message_log()]
		self.assertEqual(messages.count(warning), 2)

		frappe.db.set_single_value("ERPNext Germany Settings", "warn_if_tax_category_missing", 0)
		frappe.local.message_log = []
		make_supplier("_Test Lieferant ohne Warnung", None)
		self.assertNotIn(warning, [message["message"] for message in frappe.get_message_log()])


def get_incomplete_rows_warnings() -> list[str]:
	return [
		message["message"] for message in frappe.get_message_log() if "Tax rows for" in message["message"]
	]


def get_snapshot() -> dict:
	"""Everything the setup may write, to compare before and after a dry run."""
	return {
		doctype: frappe.get_all(doctype, pluck="name", order_by="name")
		for doctype in (
			"Tax Category",
			"Item Tax Template",
			"Sales Taxes and Charges Template",
			"Purchase Taxes and Charges Template",
			"Tax Rule",
		)
	} | {
		"Item Group rows": frappe.get_all(
			"Item Tax", {"parenttype": "Item Group"}, ["parent", "item_tax_template"], order_by="name"
		),
		"Common Code links": frappe.get_all(
			"Dynamic Link", {"parenttype": "Common Code"}, ["parent", "link_name"], order_by="name"
		),
		"Accounts without type": frappe.get_all(
			"Account", {"account_type": ("is", "not set")}, pluck="name", order_by="name"
		),
		"Accounts Settings": frappe.db.get_values_from_single(
			["add_taxes_from_item_tax_template", "add_taxes_from_taxes_and_charges_template"],
			None,
			"Accounts Settings",
		),
		"Warn if Tax Category is missing": frappe.db.get_single_value(
			"ERPNext Germany Settings", "warn_if_tax_category_missing"
		),
		"E Invoice Settings": frappe.db.get_single_value("E Invoice Settings", "vat_exemption_reason_text")
		if frappe.db.exists("DocType", "E Invoice Settings")
		else None,
	}


def actions(report: list[dict]) -> list[tuple]:
	return [(row["action"], row["doctype"], row["name"]) for row in report]


def make_company():
	if frappe.db.exists("Company", COMPANY):
		return

	frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": COMPANY,
			"abbr": "_TSG",
			"country": "Germany",
			"default_currency": "EUR",
			"create_chart_of_accounts_based_on": "Standard Template",
			"chart_of_accounts": "SKR04 mit Kontonummern",
		}
	).insert()


def make_item_group(name: str):
	if not frappe.db.exists("Item Group", name):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": name, "is_group": 0}).insert()


def make_item(item_code: str, item_group: str) -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_group": item_group,
				"stock_uom": "Nos",
				"is_stock_item": 0,
			}
		)
		.insert()
		.name
	)


def make_customer(name: str, tax_category: str | None) -> str:
	return (
		frappe.get_doc({"doctype": "Customer", "customer_name": name, "tax_category": tax_category})
		.insert()
		.name
	)


def make_supplier(name: str, tax_category: str | None) -> str:
	return (
		frappe.get_doc({"doctype": "Supplier", "supplier_name": name, "tax_category": tax_category})
		.insert()
		.name
	)


def make_purchase_invoice(supplier: str, items: list[str]):
	invoice = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"company": COMPANY,
			"supplier": supplier,
			"currency": "EUR",
			"posting_date": today(),
			"items": [{"item_code": item, "qty": 1, "rate": 100} for item in items],
		}
	)
	invoice.set_missing_values()
	return invoice.insert()


def make_invoice(customer: str, items: list[str]):
	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": COMPANY,
			"customer": customer,
			"currency": "EUR",
			"posting_date": today(),
			"items": [{"item_code": item, "qty": 1, "rate": 100} for item in items],
		}
	)
	invoice.set_missing_values()
	return invoice.insert()
