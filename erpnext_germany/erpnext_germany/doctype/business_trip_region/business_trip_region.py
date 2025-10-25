# Copyright (c) 2024, ALYF GmbH and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from frappe import _
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from frappe.types import DF


class BusinessTripRegion(Document):

    if TYPE_CHECKING:
        from frappe.types import DF

        accommodation: "DF.Currency"
        arrival_or_departure: "DF.Currency"
        disabled: "DF.Check"
        title: "DF.Data | None"
        valid_from: "DF.Date | None"
        whole_day: "DF.Currency"
   
    def validate(self):
     """
        1) Warn if no allowances.
        2) Validate unique valid_till.
     """
       
        self._warn_if_no_allowances()
        self._validate_allowance_valid_till_unique()

    def _warn_if_no_allowances(self):
        """Show warning if there are no allowance rows."""
        if not getattr(self, "allowances", []):
            frappe.msgprint(
                _("No allowance entries found under this region. "
                  "Please add at least one record in the <b>Allowances</b> table.")
            )

    def _validate_allowance_valid_till_unique(self):
        """Ensure that each allowance row has a valid_till and no duplicates exist."""
        rows = getattr(self, "allowances", []) or []
        seen_dates = set()

        for idx, row in enumerate(rows, start=1):
            vt_raw = getattr(row, "valid_till", None) or row.get("valid_till")
            if not vt_raw:
                frappe.throw(_("Allowance row {0}: Please set a Valid Till date.").format(idx))

            try:
                vt_date = getdate(vt_raw)
            except Exception:
                frappe.throw(
                    _("Allowance row {0}: Invalid date format for Valid Till: {1}")
                    .format(idx, vt_raw)
                )

            if vt_date in seen_dates:
                frappe.throw(
                    _("Duplicate Valid Till date found in row {0}: {1}. "
                      "Each row must have a unique Valid Till date.")
                    .format(idx, vt_date)
                )

            seen_dates.add(vt_date)
