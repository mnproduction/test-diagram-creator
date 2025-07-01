import asyncio
import unittest
from unittest.mock import MagicMock

from src.core.exceptions import TemplateException
from src.diagram.engine import DiagramEngine
from src.templates.engine import PatternLibrary, PatternTemplate, TemplateEngine


class TestPatternLibrary(unittest.TestCase):
    def setUp(self):
        self.library = PatternLibrary()

    def test_register_and_get_pattern(self):
        """Test that a pattern can be registered and then retrieved."""
        pattern = PatternTemplate(
            name="test_pattern",
            description="A simple test pattern.",
            parameters={},
            steps=[{"action": "create_node", "params": {"name": "test_node"}}],
        )
        self.library.register_pattern(pattern)
        retrieved_pattern = self.library.get_pattern("test_pattern")
        self.assertEqual(retrieved_pattern, pattern)

    def test_get_nonexistent_pattern_raises_exception(self):
        """Test that trying to get a non-existent pattern raises a TemplateException."""
        with self.assertRaises(TemplateException):
            self.library.get_pattern("nonexistent_pattern")


class TestTemplateEngine(unittest.TestCase):
    def setUp(self):
        self.mock_diagram_engine = MagicMock(spec=DiagramEngine)
        self.mock_pattern_library = MagicMock()
        self.engine = TemplateEngine(
            self.mock_diagram_engine, self.mock_pattern_library
        )

    def test_apply_template_success(self):
        """Test the successful application of a template."""
        # Arrange
        spec = MagicMock()
        spec.pattern_name = "test_pattern"

        pattern = PatternTemplate(
            name="test_pattern",
            description="A test pattern",
            parameters={},
            steps=[
                {"action": "create_node", "params": {"name": "node1"}},
                {"action": "create_cluster", "params": {"name": "cluster1"}},
            ],
        )
        self.mock_pattern_library.get_pattern.return_value = pattern

        # Mock the tool functions on the diagram engine
        self.mock_diagram_engine.create_node = MagicMock()
        self.mock_diagram_engine.create_cluster = MagicMock()

        # Act
        asyncio.run(self.engine.apply_template(spec))

        # Assert
        self.mock_pattern_library.get_pattern.assert_called_once_with("test_pattern")
        self.mock_diagram_engine.initialize_diagram.assert_called_once_with(
            title="A test pattern"
        )
        self.mock_diagram_engine.create_node.assert_called_once_with(name="node1")
        self.mock_diagram_engine.create_cluster.assert_called_once_with(name="cluster1")

    def test_apply_template_unknown_action_raises_exception(self):
        """Test that an unknown action in a pattern raises a TemplateException."""
        # Arrange
        spec = MagicMock()
        spec.pattern_name = "test_pattern"

        pattern = PatternTemplate(
            name="test_pattern",
            description="A test pattern with an invalid action",
            parameters={},
            steps=[{"action": "nonexistent_action", "params": {}}],
        )
        self.mock_pattern_library.get_pattern.return_value = pattern

        # Act & Assert
        with self.assertRaisesRegex(
            TemplateException, "Action 'nonexistent_action' not found"
        ):
            asyncio.run(self.engine.apply_template(spec))

    def test_apply_template_action_execution_fails(self):
        """Test that a failure in executing a diagram engine action is handled."""
        # Arrange
        spec = MagicMock()
        spec.pattern_name = "test_pattern"

        pattern = PatternTemplate(
            name="test_pattern",
            description="A test pattern",
            parameters={},
            steps=[{"action": "create_node", "params": {"name": "node1"}}],
        )
        self.mock_pattern_library.get_pattern.return_value = pattern
        self.mock_diagram_engine.create_node = MagicMock(
            side_effect=Exception("Execution failed")
        )

        # Act & Assert
        with self.assertRaisesRegex(
            TemplateException, "Failed to execute action 'create_node'"
        ):
            asyncio.run(self.engine.apply_template(spec))


if __name__ == "__main__":
    unittest.main()
