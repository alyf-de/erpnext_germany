// Copyright (c) 2023, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("VAT ID Check", {
	setup: function (frm) {
		frm.set_query("customer_address", function (doc) {
			return {
				query: "frappe.contacts.doctype.address.address.address_query",
				filters: {
					link_doctype: "Customer",
					link_name: doc.customer,
				},
			};
		});
	},
});
