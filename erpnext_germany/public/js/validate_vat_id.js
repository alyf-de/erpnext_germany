
frappe.provide("erpnext_germany.utils");

erpnext_germany.utils.setup_vat_id_validation_button = function (frm) {
	const $wrapper = $(frm.fields_dict.tax_id.input_area);
	const $link_button = $(
		`<span class="link-btn"
			style="top: 2px; right: 2px;"
		>
            <a
				class="btn btn-xs btn-default"
				title="${__("Validate EU VAT ID")}"
				style="padding: 3px;"
			>
                ${frappe.utils.icon("search", "sm")}
            </a>
        </span>`
	);

	$($wrapper).append($link_button);
	$link_button.toggle(true);
	$link_button.on("click", "a", () => {
		const vat_id = frm.doc.tax_id;
		erpnext_germany.utils.check_vat_id(vat_id)
			.then((is_valid) => {
				if (is_valid === true) {
					frappe.show_alert({
						message: __("Tax ID is a valid EU VAT ID"),
						indicator: "green",
					});
				} else if (is_valid === false) {
					frappe.show_alert({
						message: __("Tax ID is not a valid EU VAT ID"),
						indicator: "red",
					});
				} else {
					frappe.show_alert({
						message: __("Tax ID could not be validated"),
						indicator: "grey",
					});
				}
			});
	});
};

erpnext_germany.utils.check_vat_id = function (vat_id) {
	return frappe.xcall(
		"erpnext_germany.api.validate_vat_id",
		{ vat_id: vat_id },
	);
};
