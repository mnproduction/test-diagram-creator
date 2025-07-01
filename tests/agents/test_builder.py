import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.base import ExecutionPlan, ToolCall
from src.agents.builder import BuilderAgent, DiagramResult


class TestBuilderAgent(unittest.TestCase):
    def setUp(self):
        # Patch DiagramEngine for all tests in this class
        self.diagram_engine_patch = patch("src.agents.builder.DiagramEngine")
        self.mock_diagram_engine_class = self.diagram_engine_patch.start()
        self.mock_engine_instance = self.mock_diagram_engine_class.return_value
        self.builder = BuilderAgent(diagram_engine=self.mock_engine_instance)

    def tearDown(self):
        self.diagram_engine_patch.stop()

    def test_handle_task_success(self):
        """
        Test that handle_task successfully executes a plan and returns a DiagramResult.
        """
        # Arrange
        execution_plan = ExecutionPlan(
            title="Test Diagram",
            description="A simple test diagram.",
            cluster_strategy="none",
            layout_preference="TB",
            estimated_duration=10,
            complexity_score=0.5,
            tool_sequence=[
                ToolCall(tool_name="tool1", parameters={"p": "v1"}, execution_order=1),
                ToolCall(tool_name="tool2", parameters={"p": "v2"}, execution_order=2),
            ],
        )

        task_data = {
            "execution_plan": execution_plan.model_dump(),
            "session_id": "test-session",
        }

        # Mock the tool registry and tools
        mock_tool1 = MagicMock()
        mock_tool1.execute = AsyncMock(return_value=None)
        mock_tool2 = MagicMock()
        mock_tool2.execute = AsyncMock(return_value=None)
        mock_render_tool = MagicMock()
        mock_render_tool.execute = AsyncMock(
            return_value={
                "success": True,
                "image_data": "base64data",
                "components_used": ["c1", "c2"],
            }
        )

        mock_tool_registry = self.builder.tool_registry
        mock_tool_registry.get_tool = MagicMock(
            side_effect=lambda name: {
                "tool1": mock_tool1,
                "tool2": mock_tool2,
                "render_diagram": mock_render_tool,
            }.get(name)
        )

        # Act
        result_dict = asyncio.run(self.builder.handle_task(task_data))
        result = DiagramResult(**result_dict)

        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.image_data, "base64data")
        self.assertEqual(result.components_used, ["c1", "c2"])
        self.assertEqual(
            mock_tool_registry.get_tool.call_count, 3
        )  # tool1, tool2, render
        mock_tool1.execute.assert_awaited_once_with(self.mock_engine_instance, p="v1")
        mock_tool2.execute.assert_awaited_once_with(self.mock_engine_instance, p="v2")
        mock_render_tool.execute.assert_awaited_once_with(
            self.mock_engine_instance, output_format="png", dry_run=False
        )

    def test_handle_task_tool_execution_failure(self):
        """
        Test that handle_task handles tool execution failure.
        """
        # Arrange
        execution_plan = ExecutionPlan(
            title="Test Diagram",
            description="A simple test diagram.",
            cluster_strategy="none",
            layout_preference="TB",
            estimated_duration=10,
            complexity_score=0.5,
            tool_sequence=[
                ToolCall(tool_name="tool1", parameters={"p": "v1"}, execution_order=1),
                ToolCall(tool_name="tool2", parameters={"p": "v2"}, execution_order=2),
            ],
        )

        task_data = {
            "execution_plan": execution_plan.model_dump(),
            "session_id": "test-session",
        }

        # Mock the tool registry and tools
        mock_tool1 = MagicMock()
        mock_tool1.execute = AsyncMock(side_effect=Exception("Tool execution failed"))

        mock_tool_registry = self.builder.tool_registry
        mock_tool_registry.get_tool = MagicMock(return_value=mock_tool1)

        # Act
        result_dict = asyncio.run(self.builder.handle_task(task_data))
        result = DiagramResult(**result_dict)

        # Assert
        self.assertFalse(result.success)
        self.assertIsNotNone(result.errors)
        self.assertIn("Failed to execute tool tool1", result.errors[0])
        mock_tool_registry.get_tool.assert_called_once_with("tool1")
        mock_tool1.execute.assert_awaited_once_with(self.mock_engine_instance, p="v1")

    def test_handle_task_render_failure(self):
        """
        Test that handle_task handles final diagram rendering failure.
        """
        # Arrange
        execution_plan = ExecutionPlan(
            title="Test Diagram",
            description="A simple test diagram.",
            cluster_strategy="none",
            layout_preference="TB",
            estimated_duration=10,
            complexity_score=0.5,
            tool_sequence=[
                ToolCall(tool_name="tool1", parameters={"p": "v1"}, execution_order=1),
                ToolCall(tool_name="tool2", parameters={"p": "v2"}, execution_order=2),
            ],
        )

        task_data = {
            "execution_plan": execution_plan.model_dump(),
            "session_id": "test-session",
        }

        # Mock the tool registry and tools
        mock_tool1 = MagicMock()
        mock_tool1.execute = AsyncMock(return_value=None)
        mock_tool2 = MagicMock()
        mock_tool2.execute = AsyncMock(return_value=None)
        mock_render_tool = MagicMock()
        mock_render_tool.execute = AsyncMock(side_effect=Exception("Render failed"))

        mock_tool_registry = self.builder.tool_registry
        mock_tool_registry.get_tool = MagicMock(
            side_effect=lambda name: {
                "tool1": mock_tool1,
                "tool2": mock_tool2,
                "render_diagram": mock_render_tool,
            }.get(name)
        )

        # Act
        result_dict = asyncio.run(self.builder.handle_task(task_data))
        result = DiagramResult(**result_dict)

        # Assert
        self.assertFalse(result.success)
        self.assertIsNotNone(result.errors)
        self.assertIn("Failed to render diagram", result.errors[0])

        # Check that the render tool was called, after the other tools
        from unittest.mock import call

        expected_calls = [call("tool1"), call("tool2"), call("render_diagram")]
        mock_tool_registry.get_tool.assert_has_calls(expected_calls)
        self.assertEqual(mock_tool_registry.get_tool.call_count, 3)

        mock_tool1.execute.assert_awaited_once_with(self.mock_engine_instance, p="v1")
        mock_tool2.execute.assert_awaited_once_with(self.mock_engine_instance, p="v2")
        mock_render_tool.execute.assert_awaited_once_with(
            self.mock_engine_instance, output_format="png", dry_run=False
        )


if __name__ == "__main__":
    unittest.main()
