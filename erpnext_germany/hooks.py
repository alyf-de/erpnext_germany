from . import __version__ as app_version
from .constants import REGISTER_COURTS

app_name = "erpnext_germany"
app_title = "ERPNext Germany"
app_publisher = "ALYF GmbH"
app_description = "App to hold regional code for Germany, built on top of ERPNext."
required_apps = ["erpnext"]
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "hallo@alyf.de"
app_license = "GPLv3"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/erpnext_germany/css/erpnext_germany.css"
app_include_js = "/assets/erpnext_germany/js/validate_vat_id.js"

# include js, css files in header of web template
# web_include_css = "/assets/erpnext_germany/css/erpnext_germany.css"
# web_include_js = "/assets/erpnext_germany/js/erpnext_germany.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "erpnext_germany/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Customer": "public/js/customer.js",
	"Supplier": "public/js/supplier.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "erpnext_germany.utils.jinja_methods",
# 	"filters": "erpnext_germany.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "erpnext_germany.install.before_install"
after_install = "erpnext_germany.install.after_install"

# Uninstallation
# ------------

before_uninstall = "erpnext_germany.uninstall.before_uninstall"
# after_uninstall = "erpnext_germany.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "erpnext_germany.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# doc_events = {}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"erpnext_germany.tasks.all"
# 	],
# 	"daily": [
# 		"erpnext_germany.tasks.daily"
# 	],
# 	"hourly": [
# 		"erpnext_germany.tasks.hourly"
# 	],
# 	"weekly": [
# 		"erpnext_germany.tasks.weekly"
# 	],
# 	"monthly": [
# 		"erpnext_germany.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "erpnext_germany.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "erpnext_germany.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "erpnext_germany.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"erpnext_germany.auth.validate"
# ]


def get_register_fields(insert_after: str):
	return [
		{
			"fieldtype": "Section Break",
			"fieldname": "register_sb_1",
			"label": "Register Information",
			"insert_after": insert_after,
			"collapsible": 1,
		},
		{
			"fieldtype": "Select",
			"fieldname": "register_type",
			"label": "Register Type",
			"insert_after": "register_sb_1",
			"options": "\nHRA\nHRB\nGnR\nPR\nVR",
			"translatable": 0,
		},
		{
			"fieldtype": "Column Break",
			"fieldname": "register_cb_1",
			"insert_after": "register_type",
		},
		{
			"fieldtype": "Data",
			"fieldname": "register_number",
			"label": "Register Number",
			"insert_after": "register_cb_1",
			"translatable": 0,
		},
		{
			"fieldtype": "Column Break",
			"fieldname": "register_cb_2",
			"insert_after": "register_number",
		},
		{
			"fieldtype": "Select",
			"fieldname": "register_court",
			"label": "Register Court",
			"insert_after": "register_cb_2",
			"options": "\n".join(REGISTER_COURTS),
			"translatable": 0,
		},
	]


germany_custom_fields = {
	"Company": [] + get_register_fields(insert_after="address_html"),
	"Customer": [] + get_register_fields(insert_after="disabled"),
	"Supplier": [] + get_register_fields(insert_after="prevent_pos"),
	"Employee": [
		{
			"fieldtype": "Link",
			"fieldname": "nationality",
			"label": "Nationality",
			"options": "Country",
			"insert_after": "date_of_joining",
		},
		{
			"fieldtype": "Check",
			"fieldname": "is_severely_disabled",
			"label": "Is Severely Disabled",
			"insert_after": "nationality",
		},
		{
			"fieldtype": "Float",
			"fieldname": "working_hours_per_week",
			"label": "Working Hours Per Week",
			"insert_after": "attendance_device_id",
		},
		# -- BEGIN TAXES SECTION --
		{
			"fieldtype": "Section Break",
			"fieldname": "employee_taxes_sb",
			"label": "Taxes",
			"insert_after": "default_shift",
			"collapsible": 1,
		},
		{
			"fieldtype": "Data",
			"fieldname": "tax_id",
			"label": "Tax ID",
			"insert_after": "employee_taxes_sb",
			"translatable": 0,
		},
		{
			"fieldtype": "Data",
			"fieldname": "tax_office",
			"label": "Tax Office",
			"insert_after": "tax_id",
			"translatable": 0,
		},
		{
			"fieldtype": "Data",
			"fieldname": "tax_office_number",
			"label": "Tax Office Number",
			"insert_after": "tax_office",
			"translatable": 0,
		},
		{
			"fieldtype": "Column Break",
			"fieldname": "employee_taxes_cb",
			"insert_after": "tax_office_number",
		},
		{
			"fieldtype": "Select",
			"fieldname": "tax_bracket",
			"label": "Tax Bracket",
			"options": "\nI\nII\nIII\nIV\nV\nVI",
			"insert_after": "employee_taxes_cb",
			"translatable": 0,
		},
		{
			"fieldtype": "Int",
			"fieldname": "children_eligible_for_tax_credits",
			"label": "Children Eligible for Tax Credits",
			"insert_after": "tax_bracket",
		},
		{
			"fieldtype": "Link",
			"fieldname": "religious_denomination",
			"label": "Religious Denomination",
			"options": "Religious Denomination",
			"insert_after": "children_eligible_for_tax_credits",
		},
		# -- END TAXES SECTION --
		{
			"fieldtype": "Check",
			"fieldname": "has_children",
			"label": "Has Children",
			"insert_after": "health_insurance_no",
		},
		{
			"fieldtype": "Check",
			"fieldname": "has_other_employments",
			"label": "Has Other Employments",
			"insert_after": "external_work_history",
		},
		{
			"fieldtype": "Select",
			"fieldname": "highest_school_qualification",
			"label": "Highest School Qualification",
			"options": "\nOhne Schulabschluss\nHaupt-/Volksschulabschluss\nMitttlere Reife\n(Fach-)Abitur",
			"insert_after": "education",
			"translatable": 0,
		},
	],
	("Quotation", "Sales Order", "Sales Invoice"): [
		{
			"label": "Tax Exemption Reason",
			"fieldtype": "Small Text",
			"fieldname": "tax_exemption_reason",
			"fetch_from": "taxes_and_charges.tax_exemption_reason",
			"depends_on": "tax_exemption_reason",
			"insert_after": "taxes_and_charges",
			"translatable": 0,
		}
	],
	"Sales Taxes and Charges Template": [
		{
			"label": "Tax Exemption Reason",
			"fieldtype": "Small Text",
			"fieldname": "tax_exemption_reason",
			"insert_after": "tax_category",
			"translatable": 0,
		}
	],
}

germany_property_setters = {
	"Employee": [
		("salary_currency", "default", "EUR", "Small Text"),
		("bank_ac_no", "label", "IBAN", "Data"),
		("ctc", "hidden", 1, "Check"),
		("salary_mode", "default", "Bank", "Small Text"),
		("permanent_accommodation_type", "hidden", 1, "Check"),
		("current_accommodation_type", "hidden", 1, "Check"),
	],
}
