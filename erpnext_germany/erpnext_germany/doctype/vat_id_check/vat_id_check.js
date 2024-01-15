// Copyright (c) 2023, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("VAT ID Check", {
	setup: function (frm) {
		frm.add_fetch("party", "tax_id", "party_vat_id");

		frm.set_query("party_type", function (doc) {
			return {
				filters: {
					name: ["in", ["Customer", "Supplier"]],
				},
			};
		});

		frm.set_query("party_address", function (doc) {
			return {
				query: "frappe.contacts.doctype.address.address.address_query",
				filters: {
					link_doctype: doc.party_type,
					link_name: doc.party,
				},
			};
		});
	},
});
