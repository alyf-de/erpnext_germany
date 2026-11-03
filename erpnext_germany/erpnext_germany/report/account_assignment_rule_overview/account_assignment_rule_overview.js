// Copyright (c) 2026, ALYF GmbH and contributors
// For license information, please see license.txt

function load_rows(report) {
	const document_type = report.get_filter_value("document_type");
	const document_name = report.get_filter_value("document_name");
	if (!document_type || !document_name) {
		return;
	}

	frappe.db.get_doc(document_type, document_name).then((doc) => {
		if (report.get_filter_value("document_name") !== doc.name) {
			return; // another document was picked in the meantime
		}

		const row_filter = report.get_filter("row");
		row_filter.df.options = (doc.items || []).map((row) => ({
			value: String(row.idx),
			label: `${row.idx}: ${row.item_code} - ${row.item_name}`,
		}));
		// keep a row from the URL, otherwise start with the first one
		const row = row_filter.df.options.some((option) => option.value === row_filter.get_value())
			? row_filter.get_value()
			: "1";
		report.set_filter_value("row", row); // also renders the new options
		report.refresh();
	});
}

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
			on_change: load_rows,
		},
		{
			fieldname: "row",
			label: __("Row"),
			fieldtype: "Select",
			reqd: 1,
		},
	],

	onload: load_rows, // e.g. when the filters come from the URL

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		return data?.applied ? `<b>${value}</b>` : value;
	},
};
