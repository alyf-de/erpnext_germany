// Copyright (c) 2026, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("Account Assignment Rule", {
	setup(frm) {
		frm.set_query("account", (doc) => {
			const filters = { company: doc.company, is_group: 0 };
			if (["Income Account", "Expense Account"].includes(doc.rule_type)) {
				filters.root_type = doc.rule_type.split(" ")[0];
			}
			return { filters };
		});

		frm.set_query("cost_center", (doc) => ({ filters: { company: doc.company, is_group: 0 } }));

		for (const fieldname of [
			"filter_item_tax_template",
			"filter_sales_taxes_and_charges_template",
			"filter_purchase_taxes_and_charges_template",
		]) {
			frm.set_query(fieldname, (doc) => ({ filters: { company: doc.company } }));
		}

		frm.set_query("for_doctype", () => ({ filters: { istable: 0, issingle: 0 } }));
	},
});
