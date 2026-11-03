// Copyright (c) 2026, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.query_reports["Account Assignment Rule Overview"] = {
	filters: [
		{
			fieldname: "document_type",
			label: __("Document Type"),
			fieldtype: "Link",
			options: "DocType",
			default: "Sales Invoice",
			reqd: 1,
			get_query: () => ({ filters: { istable: 0, issingle: 0 } }),
		},
		{
			fieldname: "document_name",
			label: __("Document"),
			fieldtype: "Dynamic Link",
			get_options: () => frappe.query_report.get_filter_value("document_type"),
			reqd: 1,
			on_change: () => {
				const document_type = frappe.query_report.get_filter_value("document_type");
				const document_name = frappe.query_report.get_filter_value("document_name");
				if (!document_type || !document_name) {
					return;
				}

				frappe.db.get_doc(document_type, document_name).then((doc) => {
					frappe.query_report.set_filter_value("item", doc.items?.[0]?.item_code);
				});
			},
		},
		{
			fieldname: "item",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			reqd: 1,
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		return data?.applied ? `<b>${value}</b>` : value;
	},
};
