// Copyright (c) 2026, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("GDPdU Export", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) {
			return;
		}

		if (frm.doc.export_file) {
			frm.add_custom_button(__("Download"), () => window.open(frm.doc.export_file));
		} else if (frm.doc.status === "Failed") {
			frm.dashboard.set_headline(__("The export failed, see the error log."));
			frm.add_custom_button(__("Retry"), () =>
				frm.call("enqueue_export").then(() => frm.reload_doc())
			);
		} else {
			frm.dashboard.set_headline(
				__("The export is being generated. Reload this page in a moment.")
			);
		}
	},
});
