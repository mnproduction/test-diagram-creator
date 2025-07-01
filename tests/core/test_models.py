import unittest

from src.core.models import DiagramSpec, ValidationResult


class TestCoreModels(unittest.TestCase):
    def test_diagram_spec_creation(self):
        """Test the creation of a DiagramSpec model."""
        spec = DiagramSpec(
            pattern_name="test_pattern",
            parameters={"param1": "value1"},
            metadata={"source": "test"},
        )
        self.assertEqual(spec.pattern_name, "test_pattern")
        self.assertEqual(spec.parameters, {"param1": "value1"})
        self.assertEqual(spec.metadata, {"source": "test"})

    def test_diagram_spec_defaults(self):
        """Test the default values of a DiagramSpec model."""
        spec = DiagramSpec(pattern_name="test_pattern", parameters={})
        self.assertEqual(spec.metadata, {})

    def test_validation_result_creation(self):
        """Test the creation of a ValidationResult model."""
        result = ValidationResult(is_valid=False, issues=["issue1", "issue2"])
        self.assertFalse(result.is_valid)
        self.assertEqual(result.issues, ["issue1", "issue2"])

    def test_validation_result_defaults(self):
        """Test the default values of a ValidationResult model."""
        result = ValidationResult(is_valid=True)
        self.assertEqual(result.issues, [])


if __name__ == "__main__":
    unittest.main()
