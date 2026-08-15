// Copyright (c) 2026, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("Business Trip Intake", {
	setup(frm) {
		frm.set_query("employee", erpnext.queries.employee);
		frm.set_query("employee_vehicle", (doc) => {
			return {
				filters: {
					employee: doc.employee,
					disabled: 0,
				},
			};
		});
	},

	refresh(frm) {
		if (frm.doc.business_trip) {
			frm.add_custom_button(__("Business Trip"), () => {
				frappe.set_route("Form", "Business Trip", frm.doc.business_trip);
			});
			return;
		}

		if (frm.doc.status === "Ready" && !frm.is_new()) {
			frm.add_custom_button(__("Create Business Trip"), () => {
				frm.call("create_business_trip").then((r) => {
					if (r.message) {
						frappe.set_route("Form", "Business Trip", r.message);
					}
				});
			});
		}
	},
});
