frappe.ui.form.on("Supplier", {
	setup: function (frm) {
		erpnext_germany.utils.setup_vat_id_validation_button(frm);
	}
});