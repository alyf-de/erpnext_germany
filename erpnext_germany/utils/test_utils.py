import pytest

from .eu_vat import parse_vat_id


def test_parse_vat_id_valid():
	"""Test parsing valid VAT IDs."""
	# Test with no spaces
	country_code, vat_number = parse_vat_id("DE329035522")
	assert country_code == "DE"
	assert vat_number == "329035522"

	# Test with spaces in VAT number (should be removed)
	country_code, vat_number = parse_vat_id("DE329 035 522")
	assert country_code == "DE"
	assert vat_number == "329035522"

	# Test with lowercase country code (should be uppercased)
	country_code, vat_number = parse_vat_id("de210157578")
	assert country_code == "DE"
	assert vat_number == "210157578"

	# Test with mixed case
	country_code, vat_number = parse_vat_id("Fr12345678901")
	assert country_code == "FR"
	assert vat_number == "12345678901"


def test_parse_vat_id_invalid_country_code():
	"""Test parsing VAT IDs with invalid country codes."""
	# Too short country code (only 1 character provided)
	with pytest.raises(ValueError, match="Invalid country code"):
		parse_vat_id("D123456789")

	# Non-alphabetic country code
	with pytest.raises(ValueError, match="Invalid country code"):
		parse_vat_id("D1123456789")

	# Numbers in country code
	with pytest.raises(ValueError, match="Invalid country code"):
		parse_vat_id("12123456789")

	# Special characters in country code
	with pytest.raises(ValueError, match="Invalid country code"):
		parse_vat_id("D-123456789")


def test_parse_vat_id_invalid_vat_number():
	"""Test parsing VAT IDs with invalid VAT numbers."""
	# Too short VAT number (less than 2 characters)
	with pytest.raises(ValueError, match="Invalid VAT number"):
		parse_vat_id("DE1")

	# Too long VAT number (more than 12 characters)
	with pytest.raises(ValueError, match="Invalid VAT number"):
		parse_vat_id("DE1234567890123")

	# Invalid characters in VAT number
	with pytest.raises(ValueError, match="Invalid VAT number"):
		parse_vat_id("DE123-456789")

	# Special characters not allowed
	with pytest.raises(ValueError, match="Invalid VAT number"):
		parse_vat_id("DE123@456789")


def test_parse_vat_id_edge_cases():
	"""Test edge cases for VAT ID parsing."""
	# Minimum length VAT number (2 characters)
	country_code, vat_number = parse_vat_id("DE12")
	assert country_code == "DE"
	assert vat_number == "12"

	# Maximum length VAT number (12 characters)
	country_code, vat_number = parse_vat_id("DE123456789012")
	assert country_code == "DE"
	assert vat_number == "123456789012"

	# VAT number with allowed special characters
	country_code, vat_number = parse_vat_id("DE123+456*78.9")
	assert country_code == "DE"
	assert vat_number == "123+456*78.9"
