# Copyright (c) 2024, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _  
from typing import TYPE_CHECKING 

class BusinessTripRegion(Document):
   
    if TYPE_CHECKING:
       
        from erpnext_germany.erpnext_germany.doctype.business_trip_region_allowance.business_trip_region_allowance import BusinessTripRegionAllowance
        from frappe.types import DF

        accommodation: DF.Currency
        allowances: DF.Table[BusinessTripRegionAllowance] 
        arrival_or_departure: DF.Currency
        disabled: DF.Check
        title: DF.Data | None
        valid_from: DF.Date | None
        whole_day: DF.Currency
    
    def validate(self):
        """
        Validate that no child row's 'valid_till' date
        is the same as the parent's 'valid_from' date.
        """
        if not self.valid_from:
            return 

        for row in self.allowances:
            if row.valid_till and row.valid_till == self.valid_from:
                
                frappe.throw(
                    _("Row #{0}: The 'Valid Till' date ({1}) cannot be the same as the parent's 'Valid From' date.").format(
                        row.idx, 
                        row.valid_till
                    ),
                    title="Invalid Date"
                )