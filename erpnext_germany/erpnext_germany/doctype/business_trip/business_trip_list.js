// Copyright (c) 2024, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.listview_settings["Business Trip"] = {
	get_indicator: function (doc) {
		const colors = {
			Draft: "red",
			Approved: "yellow",
			Paid: "blue",
			Billed: "green",
		};
		return [__(doc.status), colors[doc.status], "status,=," + doc.status];
	},
};
