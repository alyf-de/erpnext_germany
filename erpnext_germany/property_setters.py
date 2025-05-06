PROTECTED_FILE_DOCTYPES = (
	"Quotation",
	"Sales Order",
	"Delivery Note",
	"Sales Invoice",
	"Request for Quotation",
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Receipt",
	"Purchase Invoice",
	"Journal Entry",
	"Payment Entry",
	"Asset",
	"Asset Depreciation Schedule",
	"Asset Repair",
	"Asset Value Adjustment",
	"Asset Capitalization",
	"POS Invoice",
	"Dunning",
	"Business Letter",
	"Period Closing Voucher",
	"Contract",
	"Blanket Order",
)


def get_property_setters():
	return {
		"Employee": [
			("salary_currency", "default", "EUR"),
			("salary_mode", "default", "Bank"),
			("permanent_accommodation_type", "hidden", 1),
			("current_accommodation_type", "hidden", 1),
		],
		PROTECTED_FILE_DOCTYPES: [
			(None, "protect_attached_files", 1),
		],
	}
