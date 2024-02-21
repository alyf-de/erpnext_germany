// Copyright (c) 2024, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("Business Letter Template", {
	onload(frm) {
		set_html_data(frm);
	},
});

function set_html_data(frm) {
	frm.get_field("html_help").$wrapper.html(
		erpnext_germany.business_letter.get_help_text()
	);
}
