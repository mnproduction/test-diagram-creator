import asyncio
import unittest
from unittest.mock import MagicMock

from src.core.models import DiagramSpec
from src.validation.framework import ValidationRule
from src.validation.rules import (
    check_for_required_parameters,
    check_parameter_types,
    get_all_rules,
)


class TestValidationRules(unittest.TestCase):
    def test_check_for_required_parameters_success(self):
        """Test that the required parameters check passes with a valid spec."""
        spec = DiagramSpec(pattern_name="test", parameters={}, metadata={})
        result = asyncio.run(check_for_required_parameters(spec))
        self.assertTrue(result.is_valid)

    def test_check_for_required_parameters_failure(self):
        """Test that the required parameters check fails with a missing parameter."""
        spec = MagicMock(spec=DiagramSpec)
        # Unset one of the required attributes to test hasattr
        delattr(spec, "pattern_name")
        result = asyncio.run(check_for_required_parameters(spec))
        self.assertFalse(result.is_valid)
        self.assertIn("Missing required parameter: 'pattern_name'.", result.issues)

    def test_check_parameter_types_success(self):
        """Test that the parameter types check passes with valid types."""
        spec = DiagramSpec(
            pattern_name="test", parameters={"key": "value"}, metadata={}
        )
        result = asyncio.run(check_parameter_types(spec))
        self.assertTrue(result.is_valid)

    def test_check_parameter_types_failure(self):
        """Test that the parameter types check fails with an invalid type."""
        # Use a mock to bypass Pydantic's own validation and test the rule directly
        spec = MagicMock(spec=DiagramSpec)
        spec.parameters = "not_a_dictionary"

        result = asyncio.run(check_parameter_types(spec))
        self.assertFalse(result.is_valid)
        self.assertIn("'parameters' must be a dictionary.", result.issues)

    def test_get_all_rules(self):
        """Test that get_all_rules returns a list of ValidationRule instances."""
        rules = get_all_rules()
        self.assertIsInstance(rules, list)
        self.assertTrue(all(isinstance(rule, ValidationRule) for rule in rules))
        self.assertEqual(len(rules), 4)


if __name__ == "__main__":
    unittest.main()
