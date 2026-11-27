// Copyright (c) 2025, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("ERPNext Germany Settings", {
	setup(frm) {
		erpnext_germany.accountant_export.setup_doctypes_table(frm, "accountant_export_doctypes");
	},

	refresh(frm) {
		erpnext_germany.accountant_export.set_attach_field_options_for_all(frm, "accountant_export_doctypes");
	},
});
