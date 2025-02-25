$(document).ready(function () {
	$(document).on("form-load", function (event, frm) {
		if (!frappe.boot.sysdefaults.prevent_attachment_deletion || frappe.user.has_role("System Manager")) {
			return;
		}

		if (![
			"Quotation",
			"Sales Order",
			"Delivery Note",
			"Sales Invoice",
			"Request for Quotation",
			"Supplier Quotation",
			"Purchase Order",
			"Purchase Receipt",
			"Purchase Invoice",
		].includes(frm.doctype)) {
			return;
		}

		frappe.ui.form.on(frm.doctype, {
			refresh: () => {
				$(".attachment-row .remove-btn").hide();
			},
		});
	});
});
