// Copyright (c) 2024, ALYF GmbH and contributors
// For license information, please see license.txt


frappe.ui.form.on('Business Trip Region', {
    whole_day(frm) {
        frm.events.copy_parent_values(frm);
    },
    arrival_or_departure(frm) {
        frm.events.copy_parent_values(frm);
    },
    accommodation(frm) {
        frm.events.copy_parent_values(frm);
    },

    copy_parent_values(frm) {
        if (!frm.doc.allowances?.length) return;

        frm.doc.allowances.forEach(row => {
            frappe.model.set_value(row.doctype, row.name, 'full_day', frm.doc.whole_day);
            frappe.model.set_value(row.doctype, row.name, 'arrival__departure', frm.doc.arrival_or_departure);
            frappe.model.set_value(row.doctype, row.name, 'accommodation', frm.doc.accommodation);
        });

        frm.refresh_field("allowances");
    }
});

frappe.ui.form.on('Business Trip Region Allowance', {
    valid_till(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, 'full_day', frm.doc.whole_day);
        frappe.model.set_value(cdt, cdn, 'arrival__departure', frm.doc.arrival_or_departure);
        frappe.model.set_value(cdt, cdn, 'accommodation', frm.doc.accommodation);
        frm.refresh_field("allowances");
    }
});
