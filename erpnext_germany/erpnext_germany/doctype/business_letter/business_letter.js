// Copyright (c) 2024, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("Business Letter", {
	onload(frm) {
		set_html_data(frm);
	},
	template: function (frm) {
		if (frm.doc.template) {
			frappe.call({
				method: "get_template",
				doc: frm.doc,
				callback: function (r) {
					if (r.message) {
						frm.set_value("subject", r.message.subject);
						frm.set_value("content", r.message.content);
					}
				},
			});
		}
	},
	address: function (frm) {
		erpnext.utils.get_address_display(frm, "address");
	},
});

function set_html_data(frm) {
	const html_notice = `<div class="form-message orange"><div>${__(
		"Unsaved changes. Save the document first to get a preview."
	)}</div></div>`;

	frm.get_field("html_notice").$wrapper.html(html_notice);
	frm.get_field("html_help").$wrapper.html(
		`<div>${erpnext_germany.business_letter.get_help_text()}</div>`
	);
}
