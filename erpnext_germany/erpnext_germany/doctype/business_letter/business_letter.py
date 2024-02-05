# Copyright (c) 2024, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BusinessLetter(Document):
	def before_validate(self):
		self.set_subject_preview()
		self.set_content_preview()

	def set_subject_preview(self):
		self.subject_preview = (
			frappe.render_template(self.subject, self.get_context()) if self.subject else " "
		)

	def set_content_preview(self):
		self.content_preview = (
			frappe.render_template(self.content, self.get_context()) if self.content else " "
		)

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

	@frappe.whitelist()
	def get_template(self):
		subject = frappe.get_value("Business Letter Template", self.template, "subject")
		content = frappe.get_value("Business Letter Template", self.template, "content")

		return {"subject": subject, "content": content}
