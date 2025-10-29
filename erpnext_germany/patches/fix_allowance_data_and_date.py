import frappe
from frappe import _

PARENT_DOCTYPE = "Business Trip Region"
CHILD_TABLE_FIELD = "allowances"

def execute():
    
    updated_docs = 0
    created_rows_total = 0  
    errors = 0

    try:
        regions = frappe.get_all(
            PARENT_DOCTYPE,
            fields=["name", "whole_day", "arrival_or_departure", "accommodation"],
        )
    except Exception as e:
        frappe.log_error(f"Patch failed: Could not get {PARENT_DOCTYPE} list. {e}")
        return

    if not regions:
        print("No Business Trip Region records found; nothing to do.")
        return

    total_docs = len(regions)
    print(f"Found {total_docs} '{PARENT_DOCTYPE}' documents to process...")

    for i, r in enumerate(regions):
        name = r.get("name")
        
        try:
            doc = frappe.get_doc(PARENT_DOCTYPE, name)
            
           
            parent_whole_day = r.get("whole_day") or 0
            parent_arrival = r.get("arrival_or_departure") or 0
            parent_accom = r.get("accommodation") or 0

           
            doc.set(CHILD_TABLE_FIELD, [])

            
            new_row = doc.append(CHILD_TABLE_FIELD, {})
            
            
            new_row.full_day = parent_whole_day
            new_row.arrival__departure = parent_arrival
            new_row.accommodation = parent_accom
      
            doc.save(ignore_permissions=True)
            
            updated_docs += 1
            created_rows_total += 1  # We added 1 new row
            print(f"Processing doc ({i + 1}/{total_docs}): {name} -> REPLACED all rows with 1 new row.")

        except Exception:
            errors += 1
            frappe.log_error(frappe.get_traceback(), title=f"Patch Error: {name}")
            print(f"Processing doc ({i + 1}/{total_docs}): {name} -> ERROR (see error.log)")
            continue

    
    frappe.db.commit()

    summary = {
        "updated_docs": updated_docs,
        "created_rows": created_rows_total,
        "errors": errors,
    }
    
    # Updated summary message to reflect the new action
    summary_message = _(
        "Business Trip Allowances Data REPLACED: Created {created_rows} new rows in {updated_docs} documents, "
        "errors {errors}"
    ).format(**summary)
    
    print(f"--- Patch Complete ---")
    print(summary_message)
    frappe.msgprint(summary_message)