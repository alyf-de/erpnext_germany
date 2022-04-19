from unittest import TestCase
from .eu_vat import is_valid_vat_id


class TestUtils(TestCase):
	def test_validate_vat_id(self):
		valid_ids = [
			"DE329035522", # ALYF
			"DE210157578", # SAP
		]
		invalid_ids = [
			"ABC123",
			"Test Test",
			"DE1234567890",
		]

		for vat_id in valid_ids:
			self.assertTrue(is_valid_vat_id(vat_id))

		for vat_id in invalid_ids:
			self.assertFalse(is_valid_vat_id(vat_id))
