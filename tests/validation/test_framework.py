import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from src.core.exceptions import ValidationException
from src.core.models import DiagramSpec, ValidationResult
from src.validation.framework import (
    RuleEngine,
    RuleRegistry,
    ValidationFramework,
    ValidationRule,
)


class TestRuleRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = RuleRegistry()

    def test_register_rule_success(self):
        """Test successful registration of a validation rule."""
        rule = ValidationRule(name="test_rule", function=lambda x: None, layer="syntax")
        self.registry.register(rule)
        self.assertIn(rule, self.registry.get_rules_for_layer("syntax"))

    def test_register_rule_invalid_layer_raises_exception(self):
        """Test that registering a rule with an invalid layer raises an exception."""
        rule = ValidationRule(
            name="test_rule", function=lambda x: None, layer="nonexistent"
        )
        with self.assertRaises(ValidationException):
            self.registry.register(rule)

    def test_get_rules_for_layer(self):
        """Test retrieving rules for a specific layer."""
        rule1 = ValidationRule(
            name="rule1", function=lambda x: None, layer="syntax", priority=1
        )
        rule2 = ValidationRule(
            name="rule2", function=lambda x: None, layer="syntax", priority=2
        )
        self.registry.register(rule1)
        self.registry.register(rule2)
        rules = self.registry.get_rules_for_layer("syntax")
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0], rule1)
        self.assertEqual(rules[1], rule2)

    def test_get_rules_for_empty_layer_returns_empty_list(self):
        """Test that getting rules for a layer with no rules returns an empty list."""
        self.assertEqual(self.registry.get_rules_for_layer("structure"), [])


class TestRuleEngine(unittest.TestCase):
    def setUp(self):
        self.mock_registry = MagicMock(spec=RuleRegistry)
        self.engine = RuleEngine(self.mock_registry)
        self.spec = MagicMock(spec=DiagramSpec)

    def test_execute_layer_success(self):
        """Test successful execution of a validation layer."""

        # Arrange
        async def successful_rule(_):
            return ValidationResult(is_valid=True, issues=[])

        rule = ValidationRule(
            name="success_rule", function=successful_rule, layer="syntax"
        )
        self.mock_registry.get_rules_for_layer.return_value = [rule]

        # Act
        results = asyncio.run(self.engine.execute_layer("syntax", self.spec))

        # Assert
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].is_valid)

    def test_execute_layer_with_failing_rule(self):
        """Test execution of a layer with a rule that returns a failure."""

        # Arrange
        async def failing_rule(_):
            return ValidationResult(is_valid=False, issues=["failure"])

        rule = ValidationRule(
            name="failing_rule", function=failing_rule, layer="syntax"
        )
        self.mock_registry.get_rules_for_layer.return_value = [rule]

        # Act
        results = asyncio.run(self.engine.execute_layer("syntax", self.spec))

        # Assert
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_valid)
        self.assertEqual(results[0].issues, ["failure"])

    def test_execute_layer_with_exception(self):
        """Test execution of a layer where a rule raises an exception."""

        # Arrange
        async def exception_rule(_):
            raise ValueError("Something went wrong")

        rule = ValidationRule(
            name="exception_rule", function=exception_rule, layer="syntax"
        )
        self.mock_registry.get_rules_for_layer.return_value = [rule]

        # Act
        results = asyncio.run(self.engine.execute_layer("syntax", self.spec))

        # Assert
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_valid)
        self.assertIn("threw an exception", results[0].issues[0])

    def test_execute_layer_with_no_rules(self):
        """Test that executing a layer with no rules returns an empty list."""
        # Arrange
        self.mock_registry.get_rules_for_layer.return_value = []

        # Act
        results = asyncio.run(self.engine.execute_layer("syntax", self.spec))

        # Assert
        self.assertEqual(len(results), 0)


class TestValidationFramework(unittest.TestCase):
    def setUp(self):
        self.mock_rule_engine = MagicMock(spec=RuleEngine)
        # We need to mock the async method on the instance
        self.mock_rule_engine.execute_layer = AsyncMock()

        self.framework = ValidationFramework(MagicMock())
        # We replace the engine instance with our mock
        self.framework.engine = self.mock_rule_engine
        self.spec = MagicMock(spec=DiagramSpec)

    def test_validate_all_layers_pass(self):
        """Test a successful validation where all layers pass."""
        # Arrange
        self.mock_rule_engine.execute_layer.return_value = [
            ValidationResult(is_valid=True, issues=[])
        ]

        # Act
        result = asyncio.run(self.framework.validate(self.spec))

        # Assert
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.issues), 0)
        self.assertEqual(self.mock_rule_engine.execute_layer.call_count, 4)

    def test_validate_stops_at_first_failing_layer(self):
        """Test that validation stops at the first layer that has failures."""
        # Arrange
        self.mock_rule_engine.execute_layer.side_effect = [
            [ValidationResult(is_valid=True, issues=[])],  # syntax layer
            [
                ValidationResult(is_valid=False, issues=["structural issue"])
            ],  # structure layer
            [
                ValidationResult(is_valid=True, issues=[])
            ],  # visual layer (should not be called)
        ]

        # Act
        result = asyncio.run(self.framework.validate(self.spec))

        # Assert
        self.assertFalse(result.is_valid)
        self.assertEqual(result.issues, ["structural issue"])
        # Should be called for syntax and structure, but not for subsequent layers
        self.assertEqual(self.mock_rule_engine.execute_layer.call_count, 2)
