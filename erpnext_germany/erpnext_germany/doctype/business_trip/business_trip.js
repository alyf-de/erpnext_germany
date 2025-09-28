// Copyright (c) 2024, ALYF GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on("Business Trip", {
	setup(frm) {
		frm.set_query("employee", erpnext.queries.employee);
		frm.set_query("region", (doc) => {
			return {
				filters: {
					valid_from: ["<=", doc.from_date],
				},
			};
		});
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Show Processing Details"), function () {
				show_processing_details_dialog(frm);
			});
		}
	},

	from_date: function (frm) {
		if (!frm.doc.to_date) {
			frm.set_value("to_date", frm.doc.from_date);
		}

		frm.fields_dict.to_date.datepicker.update({
			minDate: frm.doc.from_date ? new Date(frm.doc.from_date) : null,
		});
	},

	to_date: function (frm) {
		frm.fields_dict.from_date.datepicker.update({
			maxDate: frm.doc.to_date ? new Date(frm.doc.to_date) : null,
		});
	},
});

frappe.ui.form.on("Business Trip Journey", {
	journeys_add(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "date", frm.doc.from_date);
	},

	create_purchase_invoice(frm, cdt, cdn) {
		create_purchase_invoice_with_receipt(frm, cdt, cdn);
	},
});

frappe.ui.form.on("Business Trip Accommodation", {
	accommodations_add(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "from_date", frm.doc.from_date);
		frappe.model.set_value(cdt, cdn, "to_date", frm.doc.to_date);
	},

	create_purchase_invoice(frm, cdt, cdn) {
		create_purchase_invoice_with_receipt(frm, cdt, cdn);
	},
});

frappe.ui.form.on("Business Trip Allowance", {
	allowances_add(frm) {
		if (!frm.doc.from_date || !frm.doc.to_date) {
			frappe.msgprint(__("Please enter a start and end date of the trip!"));
			return;
		}

		let start = new Date(frm.doc.from_date);
		let end = new Date(frm.doc.to_date);

		if (end < start) {
			frappe.msgprint(__("The end date should not be before the start date!"));
			return;
		}

		if (frm.doc.allowances && frm.doc.allowances.length == 1 && !frm.doc.allowances[0].date) {
			frm.clear_table("allowances");

			for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
				let child = frm.add_child("allowances");
				let d_string = d.toISOString().slice(0, 10);

				frappe.model.set_value(child.doctype, child.name, "date", d_string);

				if (d_string == frm.doc.from_date && d_string == frm.doc.to_date) {
					continue;
				} else if (d_string == frm.doc.from_date) {
					frappe.model.set_value(child.doctype, child.name, "to_time", "23:59");
				} else if (d_string == frm.doc.to_date) {
					frappe.model.set_value(child.doctype, child.name, "from_time", "00:00");
				} else {
					frappe.model.set_value(child.doctype, child.name, "whole_day", true);
					frappe.model.set_value(child.doctype, child.name, "from_time", "00:00");
					frappe.model.set_value(child.doctype, child.name, "to_time", "23:59");
				}
			}

			frm.refresh_field("allowances");
		}
	},
});

function show_processing_details_dialog(frm) {
	frappe.call({
		method: "erpnext_germany.erpnext_germany.doctype.business_trip.business_trip.get_processing_details",
		args: {
			business_trip: frm.doc.name,
		},
		callback: function (r) {
			if (r.message) {
				// Prepare table data first
				let table_data = prepare_table_data(r.message);

				// Create dialog with the data
				let dialog = new frappe.ui.Dialog({
					title: __("Processing Details"),
					fields: [
						{
							fieldname: "processing_details",
							fieldtype: "Table",
							label: __("Linked Documents"),
							cannot_add_rows: true,
							in_place_edit: false,
							reqd: 0,
							data: table_data,
							get_data: function () {
								return this.data;
							},
							fields: [
								{
									fieldtype: "Link",
									fieldname: "doctype",
									label: __("DocType"),
									options: "DocType",
									read_only: 1,
									in_list_view: 1,
								},
								{
									fieldtype: "Dynamic Link",
									fieldname: "document_name",
									label: __("Document Name"),
									options: "doctype",
									read_only: 1,
									in_list_view: 1,
								},
								{
									fieldtype: "Data",
									fieldname: "supplier_name",
									label: __("Supplier Name"),
									read_only: 1,
									in_list_view: 1,
								},
								{
									fieldtype: "Currency",
									fieldname: "grand_total",
									label: __("Grand Total"),
									read_only: 1,
									in_list_view: 1,
								},
								{
									fieldtype: "Data",
									fieldname: "status",
									label: __("Status"),
									read_only: 1,
									in_list_view: 1,
								},
							],
						},
					],
					size: "large",
					primary_action_label: __("Close"),
					primary_action: function () {
						dialog.hide();
					},
				});

				dialog.show();
			} else {
				frappe.msgprint(__("No processing details found."));
			}
		},
	});
}

function prepare_table_data(data) {
	let table_data = [];

	if (data && data.length > 0) {
		data.forEach(function (record) {
			table_data.push({
				doctype: record.doctype,
				document_name: record.name,
				grand_total: record.grand_total || 0,
				status: __(record.status),
				supplier_name: record.supplier_name || "",
			});
		});
	}

	if (table_data.length === 0) {
		table_data.push({
			doctype: "",
			document_name: __("No linked documents found"),
			grand_total: 0,
			status: "",
			supplier_name: "",
		});
	}

	return table_data;
}

function create_purchase_invoice_with_receipt(frm, cdt, cdn) {
	if (frm.is_dirty()) {
		frappe.msgprint({
			title: __("Save Required"),
			message: __("Before creating a purchase invoice, please save this record."),
			indicator: "red",
		});
		return;
	}

	let row = locals[cdt][cdn];

	frappe.new_doc("Purchase Invoice", {
		from_date:
			row.doctype === "Business Trip Accomodation"
				? row.from_date
				: row.doctype === "Business Trip Journey"
				? row.date
				: null,
		to_date:
			row.doctype === "Business Trip Accomodation"
				? row.to_date
				: row.doctype === "Business Trip Journey"
				? row.date
				: null,
		// Note: the date range is only set if the respective fields are no_copy = 0.
		advance_paid_by_employee: 1,
		supplier_invoice_file: row.receipt,
		// this is a field form EU E-Invoice. If not existing in an instance: No error.
		// a more sophisticated solution is expected in the future.
		business_trip: frm.doc.name,
		project: frm.doc.project,
	});
}
