frappe.listview_settings["VAT ID Check"] = {
	add_fields: ["is_valid"],
    hide_name_column: true,
	get_indicator: function (doc) {
		return doc.is_valid === 1
			? [__("Valid"), "green", "is_valid,=,Yes"]
			: [__("Invalid"), "red", "is_valid,=,No"];
	},
};
