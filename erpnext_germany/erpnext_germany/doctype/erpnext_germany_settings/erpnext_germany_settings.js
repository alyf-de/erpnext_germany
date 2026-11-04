// Copyright (c) 2025, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("ERPNext Germany Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Set up Taxes"), () => show_tax_setup_dialog());
	},
});

const TAX_SETUP_METHOD = "erpnext_germany.tax_setup";

// Preset -> which Tax Categories to create. Item Group classes are chosen in the table.
// Kleinunternehmer needs neither: one template without VAT applies to every customer.
const TAX_PRESETS = {
	Simple: { eu_business: 0, third_country: 0, small_business: 0 },
	Standard: { eu_business: 1, third_country: 1, small_business: 0 },
	Kleinunternehmer: { eu_business: 0, third_country: 0, small_business: 1 },
};
const TAX_PRESET_DESCRIPTIONS = {
	Simple: __("Domestic business only: 19 % and 7 % per Item Group."),
	Standard: __(
		"Domestic business, EU businesses (intra-EU supplies, reverse charge) and non-EU countries (exports, imports, services abroad)."
	),
	Kleinunternehmer: __("Small business under § 19 UStG: no VAT on any invoice."),
};

function show_tax_setup_dialog() {
	// The account fields come from the server, which knows the accounts per chart.
	frappe.call({
		method: `${TAX_SETUP_METHOD}.get_defaults`,
		callback: ({ message }) => make_tax_setup_dialog(message),
	});
}

function make_tax_setup_dialog(defaults) {
	const account_field = (fieldname, label, mandatory) => ({
		fieldname,
		label,
		fieldtype: "Link",
		options: "Account",
		mandatory_depends_on: mandatory ? "eval:!doc.small_business" : undefined,
		get_query: () => ({ filters: { company: dialog.get_value("company"), is_group: 0 } }),
	});
	const account_fields = (accounts, mandatory) => {
		const fields = Object.entries(accounts).map(([fieldname, label]) =>
			account_field(fieldname, label, mandatory)
		);
		const half = Math.ceil(fields.length / 2);
		return [...fields.slice(0, half), { fieldtype: "Column Break" }, ...fields.slice(half)];
	};

	const dialog = new frappe.ui.Dialog({
		title: __("Set up Taxes"),
		size: "large",
		fields: [
			{
				fieldname: "company",
				fieldtype: "Link",
				options: "Company",
				label: __("Company"),
				reqd: 1,
				default: frappe.defaults.get_user_default("Company"),
				onchange: () => load_defaults(dialog),
			},
			{
				fieldname: "preset",
				fieldtype: "Select",
				label: __("Preset"),
				options: Object.keys(TAX_PRESETS).join("\n"),
				default: "Standard",
				description: TAX_PRESET_DESCRIPTIONS.Standard,
				onchange: () => {
					const preset = dialog.get_value("preset");
					dialog.set_df_property("preset", "description", TAX_PRESET_DESCRIPTIONS[preset]);
					dialog.set_values(TAX_PRESETS[preset]);
				},
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "eu_business",
				fieldtype: "Check",
				label: __("EU Businesses (Reverse Charge)"),
				default: 1,
				depends_on: "eval:!doc.small_business",
			},
			{
				fieldname: "third_country",
				fieldtype: "Check",
				label: __("Non-EU Countries"),
				default: 1,
				depends_on: "eval:!doc.small_business",
			},
			{
				fieldname: "small_business",
				fieldtype: "Check",
				label: __("Small Business (§ 19 UStG)"),
				hidden: 1,
			},
			{
				fieldtype: "Section Break",
				label: __("Sales Accounts"),
				depends_on: "eval:!doc.small_business",
			},
			...account_fields(defaults.sales_accounts, true),
			{
				fieldtype: "Section Break",
				label: __("Purchase Accounts"),
				collapsible: 1,
				depends_on: "eval:!doc.small_business",
				description: __("Leave all empty to set up sales taxes only."),
			},
			...account_fields(defaults.purchase_accounts, false),
			{
				fieldtype: "Section Break",
				label: __("Item Groups"),
				depends_on: "eval:!doc.small_business",
				description: __(
					"Subgroups inherit the tax class of their parent. Add rows only for groups that differ."
				),
			},
			{
				fieldname: "item_groups",
				fieldtype: "Table",
				label: __("Tax Class per Item Group"),
				cannot_add_rows: false,
				in_place_edit: true,
				data: [],
				fields: [
					{
						fieldname: "item_group",
						fieldtype: "Link",
						options: "Item Group",
						label: __("Item Group"),
						in_list_view: 1,
						reqd: 1,
					},
					{
						fieldname: "tax_class",
						fieldtype: "Select",
						label: __("Tax Class"),
						in_list_view: 1,
						reqd: 1,
					},
				],
			},
			{ fieldtype: "Section Break", label: __("Preview") },
			{ fieldname: "report", fieldtype: "HTML" },
		],
		primary_action_label: __("Set up"),
		primary_action: () => run_tax_setup(dialog, false),
		secondary_action_label: __("Preview"),
		secondary_action: () => run_tax_setup(dialog, true),
	});

	dialog.account_keys = [
		...Object.keys(defaults.sales_accounts),
		...Object.keys(defaults.purchase_accounts),
	];
	dialog.show();
	load_defaults(dialog);
}

function load_defaults(dialog) {
	const company = dialog.get_value("company");
	if (!company) return;

	frappe.call({
		method: `${TAX_SETUP_METHOD}.get_defaults`,
		args: { company },
		callback: ({ message }) => {
			dialog.set_values(message.accounts);

			const table = dialog.fields_dict.item_groups;
			table.grid.update_docfield_property("tax_class", "options", message.tax_classes.join("\n"));
			if (!table.df.data.length) {
				table.df.data = [{ item_group: message.root_item_group, tax_class: message.tax_classes[0] }];
				table.grid.refresh();
			}
		},
	});
}

function run_tax_setup(dialog, dry_run) {
	const values = dialog.get_values();
	if (!values) return;

	const accounts = Object.fromEntries(dialog.account_keys.map((key) => [key, values[key]]));
	frappe.call({
		method: `${TAX_SETUP_METHOD}.setup_taxes`,
		args: {
			company: values.company,
			accounts,
			item_groups: values.item_groups || [],
			eu_business: values.eu_business,
			third_country: values.third_country,
			small_business: values.small_business,
			dry_run,
		},
		freeze: true,
		callback: ({ message }) => {
			dialog.fields_dict.report.$wrapper.html(render_report(message, dry_run));
			if (!dry_run) {
				frappe.show_alert({ message: __("Tax setup completed"), indicator: "green" });
			}
		},
	});
}

function render_report(rows, dry_run) {
	const labels = {
		create: dry_run ? __("Will be created") : __("Created"),
		exists: __("Exists, unchanged"),
		conflict: __("Conflict, please check"),
		change: dry_run ? __("Will be changed") : __("Changed"),
		skipped: __("Skipped"),
	};
	const colors = { create: "green", exists: "gray", conflict: "red", change: "orange", skipped: "orange" };

	const body = rows
		.map(
			(row) => `<tr>
				<td><span class="indicator-pill ${colors[row.action]}">${labels[row.action]}</span></td>
				<td>${__(row.doctype)}</td>
				<td>${frappe.utils.escape_html(row.name)}</td>
				<td>${frappe.utils.escape_html(row.message || "")}</td>
			</tr>`
		)
		.join("");

	return `<table class="table table-bordered small">
		<thead><tr><th>${__("Action")}</th><th>${__("DocType")}</th><th>${__("Name")}</th><th>${__(
			"Details"
		)}</th></tr></thead>
		<tbody>${body}</tbody>
	</table>`;
}
