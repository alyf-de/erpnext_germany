// Copyright (c) 2026, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("Accountant Export", {
	setup(frm) {
		erpnext_germany.accountant_export.setup_doctypes_table(frm, "doctypes");
	},

	onload(frm) {
		if (!frm.is_new() || frm.doc.doctypes?.length) {
			return;
		}

		frappe
			.xcall(
				"erpnext_germany.erpnext_germany.doctype.accountant_export.accountant_export.get_default_doctypes"
			)
			.then((doctypes) => {
				doctypes.forEach((row) => frm.add_child("doctypes", row));
				frm.refresh_field("doctypes");
				erpnext_germany.accountant_export.set_attach_field_options_for_all(frm, "doctypes");
			});
	},

	refresh(frm) {
		erpnext_germany.accountant_export.set_attach_field_options_for_all(frm, "doctypes");

		if (frm.doc.docstatus === 1 && frm.doc.zip_file) {
			frm.add_custom_button(__("Download ZIP File"), async () => {
				const { file_url } = await frappe.db.get_value("File", frm.doc.zip_file, "file_url");
				window.open(file_url);
			});
		}
	},

	refresh_documents(frm) {
		frm.call({
			doc: frm.doc,
			method: "refresh_documents",
			freeze: true,
			freeze_message: __("Refreshing Documents..."),
		}).then(() => frm.refresh());
	},
});
