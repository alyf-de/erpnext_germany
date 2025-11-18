// Copyright (c) 2025, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.query_reports["Zusammenfassende Meldung"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Int",
			reqd: 1,
		},
		{
			fieldname: "period",
			label: __("Period"),
			fieldtype: "Select",
			options: [
				{ value: "1", label: __("January") },
				{ value: "2", label: __("February") },
				{ value: "3", label: __("March") },
				{ value: "4", label: __("April") },
				{ value: "5", label: __("May") },
				{ value: "6", label: __("June") },
				{ value: "7", label: __("July") },
				{ value: "8", label: __("August") },
				{ value: "9", label: __("September") },
				{ value: "10", label: __("October") },
				{ value: "11", label: __("November") },
				{ value: "12", label: __("December") },
				{ value: "1-2", label: __("January - February") },
				{ value: "4-5", label: __("April - May") },
				{ value: "7-8", label: __("July - August") },
				{ value: "10-11", label: __("October - November") },
				{ value: "1-3", label: __("First Quarter") },
				{ value: "4-6", label: __("Second Quarter") },
				{ value: "7-9", label: __("Third Quarter") },
				{ value: "10-12", label: __("Fourth Quarter") },
				{ value: "1-12", label: __("Calendar Year") },
			],
			reqd: 1,
		},
	],
	onload: function (query_report) {
		query_report.page.set_primary_action(__("Download CSV"), () => {
			const filters = encodeURIComponent(JSON.stringify(query_report.get_values()));
			window.open(
				`/api/method/erpnext_germany.erpnext_germany.report.zusammenfassende_meldung.zusammenfassende_meldung.download_zm_csv?filters=${filters}`
			);
		});
	},
};
