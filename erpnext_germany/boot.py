import frappe


def boot_session(bootinfo):
	bootinfo.sysdefaults.prevent_attachment_deletion = frappe.db.get_single_value(
		"ERPNext Germany Settings", "prevent_attachment_deletion"
	)
