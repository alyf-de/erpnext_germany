# Copyright (c) 2023, ALYF GmbH and Contributors
# See license.txt

from types import SimpleNamespace
from unittest.mock import patch

import frappe

from erpnext_germany.tests.utils import ERPNextGermanyTestSuite


class TestVATIDCheck(ERPNextGermanyTestSuite):
	def run_check_with_vies(self, check_vat_approx):
		"""Insert a VAT ID Check (runs synchronously in tests) with a stubbed VIES client."""
		with patch("erpnext_germany.utils.eu_vat.Client") as client:
			client.return_value.service.checkVatApprox = check_vat_approx
			doc = frappe.get_doc({"doctype": "VAT ID Check", "party_vat_id": "DE329035522"}).insert()

		doc.reload()
		return doc

	def test_valid_result(self):
		result = SimpleNamespace(
			valid=True,
			traderNameMatch=None,
			traderStreetMatch=None,
			traderPostcodeMatch=None,
			traderCityMatch=None,
			requestIdentifier="WAPIAAAAZ1234567",
			traderName="Example GmbH",
			traderAddress="Example Street 1",
		)

		def check_vat_approx(**kwargs):
			self.assertEqual(kwargs["countryCode"], "DE")
			self.assertEqual(kwargs["vatNumber"], "329035522")
			return result

		doc = self.run_check_with_vies(check_vat_approx)

		self.assertEqual(doc.status, "Completed")
		self.assertTrue(doc.is_valid)
		self.assertEqual(doc.request_id, "WAPIAAAAZ1234567")

	def test_service_unavailable(self):
		"""Exhausted retries must end as "Service Unavailable", not as "Error"."""

		def check_vat_approx(**_kwargs):
			raise Exception("SERVICE_UNAVAILABLE")

		doc = self.run_check_with_vies(check_vat_approx)

		self.assertEqual(doc.status, "Service Unavailable")
