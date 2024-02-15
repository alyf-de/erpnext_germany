# Copyright (c) 2024, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.desk.doctype.notification_log.notification_log import get_title


class BusinessLetter(Document):
	def before_validate(self):
		self.set_subject_preview()
		self.set_content_preview()
		self.set_link_title()

	def set_subject_preview(self):
		self.subject_preview = (
			frappe.render_template(self.subject, self.get_context()) if self.subject else " "
		)

	def set_content_preview(self):
		self.content_preview = (
			frappe.render_template(self.content, self.get_context()) if self.content else " "
		)

	def set_link_title(self):
		if self.link_name:
			self.link_title = get_title(self.link_document_type, self.link_name)
		else:
			self.link_title = None

	def get_context(self):
		address = frappe.get_doc("Address", self.address) if self.address else None
		contact = frappe.get_doc("Contact", self.contact) if self.contact else None
		reference = (
			frappe.get_doc(self.link_document_type, self.link_name) if self.link_name else None
		)

		return {
			"address": address,
			"contact": contact,
			"reference": reference,
		}

	def on_submit(self):
		self.add_comments(
			_(
				"submitted Business Letter <a href='/app/business-letter/{0}'><strong>{1}</strong></a>"
			).format(self.name, self.subject_preview)
		)

	def on_cancel(self):
		self.add_comments(
			_(
				"canceled Business Letter <a href='/app/business-letter/{0}'><strong>{1}</strong></a>"
			).format(self.name, self.subject_preview)
		)

	def add_comments(self, msg):
		if self.contact:
			frappe.get_doc("Contact", self.contact).add_comment("Info", msg)

		if self.address:
			frappe.get_doc("Address", self.address).add_comment("Info", msg)

		if self.link_name:
			frappe.get_doc(self.link_document_type, self.link_name).add_comment("Info", msg)

	@frappe.whitelist()
	def get_template(self):
		subject = frappe.get_value("Business Letter Template", self.template, "subject")
		content = frappe.get_value("Business Letter Template", self.template, "content")

		return {"subject": subject, "content": content}
