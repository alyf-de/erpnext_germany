frappe.provide("erpnext_germany.accountant_export");

const ACCOUNTANT_EXPORT_METHOD =
	"erpnext_germany.erpnext_germany.doctype.accountant_export.accountant_export";

erpnext_germany.accountant_export = {
	/** Limit the selectable DocTypes and offer the attach fields of the selected DocType. */
	setup_doctypes_table(frm, fieldname) {
		frappe.xcall(`${ACCOUNTANT_EXPORT_METHOD}.get_allowed_doctypes`).then((doctypes) => {
			frm.set_query("reference_doctype", fieldname, () => ({
				filters: { name: ["in", doctypes] },
			}));
		});
	},

	set_attach_field_options_for_all(frm, fieldname) {
		(frm.doc[fieldname] || []).forEach((row) =>
			erpnext_germany.accountant_export.set_attach_field_options(frm, row.doctype, row.name)
		);
	},

	async set_attach_field_options(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const options = [""];

		if (row.reference_doctype) {
			await frappe.model.with_doctype(row.reference_doctype);
			frappe
				.get_meta(row.reference_doctype)
				.fields.filter((df) => ["Attach", "Attach Image"].includes(df.fieldtype))
				.forEach((df) =>
					options.push({ value: df.fieldname, label: `${__(df.label)} (${df.fieldname})` })
				);
		}

		frappe.meta.get_docfield(cdt, "attach_field", cdn).options = options;
		frm.fields_dict[row.parentfield]?.grid
			.get_row(cdn)
			?.set_field_property("attach_field", "options", options);
	},
};

frappe.ui.form.on("Accountant Export DocType", {
	form_render(frm, cdt, cdn) {
		erpnext_germany.accountant_export.set_attach_field_options(frm, cdt, cdn);
	},

	reference_doctype(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "attach_field", "");
		erpnext_germany.accountant_export.set_attach_field_options(frm, cdt, cdn);
	},
});
