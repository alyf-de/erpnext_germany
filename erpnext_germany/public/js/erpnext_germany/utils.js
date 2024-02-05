frappe.provide("erpnext_germany.utils");

erpnext_germany.utils = {
	...erpnext_germany.utils,

	get_business_letter_help() {
		return __(
			'<div>You can use <a href="https://jinja.palletsprojects.com/en/2.11.x/" target="_blank"><strong>Jinja tags</strong></a> in the Subject and Content fields for dynamic values.<br><br>All address details are available under the <code>address</code> object (e.g., <code>{{ address.city }}</code>), contact details under the <code>contact</code> object (e.g., <code>{{ contact.first_name }}</code>), and any specific information related to the dynamically linked document under the <code>reference</code> object (e.g., <code>{{ reference.some_field }}</code>).<br><br></div>'
		);
	},
};
