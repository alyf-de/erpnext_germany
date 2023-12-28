// Copyright (c) 2023, ALYF GmbH and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Summen- und Saldenliste"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "fiscal_year",
			label: __("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(),
			reqd: 1,
		},
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			default: (new Date()).getMonth(),
			options: [
				{ value: 1, label: __("January") },
				{ value: 2, label: __("February") },
				{ value: 3, label: __("March") },
				{ value: 4, label: __("April") },
				{ value: 5, label: __("May") },
				{ value: 6, label: __("June") },
				{ value: 7, label: __("July") },
				{ value: 8, label: __("August") },
				{ value: 9, label: __("September") },
				{ value: 10, label: __("October") },
				{ value: 11, label: __("November") },
				{ value: 12, label: __("December") },
			],
			reqd: 1,
		}
	],
};
