import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.architect import ArchitectAgent
from src.agents.base import ComponentAnalysis
from src.agents.builder import BuilderAgent


class TestAgentIntegration(unittest.TestCase):
    @patch("src.agents.builder.DiagramEngine")
    @patch("src.agents.architect.Agent")
    def test_full_workflow_from_description_to_tool_calls(
        self, mock_agent_class, mock_diagram_engine
    ):
        """
        Integration test for the full workflow from description to diagram tool calls.
        """
        # --- ARRANGE ---
        # 1. Mock Architect's LLM response
        mock_llm_instance = AsyncMock()
        mock_agent_class.return_value = mock_llm_instance

        analysis_result = ComponentAnalysis(
            services=[
                {
                    "name": "WebApp",
                    "component_type": "aws_compute",
                    "service_name": "EC2",
                    "description": "Main web application server.",
                },
                {
                    "name": "Database",
                    "component_type": "aws_database",
                    "service_name": "RDS",
                    "description": "Primary database.",
                },
            ],
            clusters=[],
            connections=[
                {
                    "source": "WebApp",
                    "target": "Database",
                    "label": "Reads/Writes",
                }
            ],
            confidence_score=0.9,
        )
        mock_llm_instance.run.return_value.data = analysis_result

        # 2. Instantiate Agents
        architect = ArchitectAgent()
        builder = BuilderAgent(diagram_engine=mock_diagram_engine.return_value)

        # 3. Mock Builder's Tool Registry
        mock_tool_initialize = MagicMock()
        mock_tool_initialize.execute = AsyncMock(return_value=None)
        mock_tool_node = MagicMock()
        mock_tool_node.execute = AsyncMock(return_value=None)
        mock_tool_connect = MagicMock()
        mock_tool_connect.execute = AsyncMock(return_value=None)
        mock_tool_render = MagicMock()
        mock_tool_render.execute = AsyncMock(
            return_value={"success": True, "components_used": ["WebApp", "Database"]}
        )

        builder.tool_registry.get_tool = MagicMock(
            side_effect=lambda name: {
                "initialize_diagram": mock_tool_initialize,
                "create_aws_node": mock_tool_node,
                "connect_nodes": mock_tool_connect,
                "render_diagram": mock_tool_render,
            }.get(name)
        )

        # --- ACT ---
        description = "A web app using EC2 and RDS."
        # Run Architect
        execution_plan = architect.generate_execution_plan(
            analysis=analysis_result, description=description
        )
        # Run Builder
        task_data = {
            "execution_plan": execution_plan.model_dump(),
            "session_id": "integration-test",
            "dry_run": True,
        }
        asyncio.run(builder.handle_task(task_data))

        # --- ASSERT ---
        # Architect Asserts
        self.assertEqual(len(execution_plan.tool_sequence), 4)
        self.assertEqual(
            execution_plan.tool_sequence[0].tool_name, "initialize_diagram"
        )
        self.assertEqual(execution_plan.tool_sequence[3].tool_name, "connect_nodes")

        # Builder Asserts
        self.assertEqual(builder.tool_registry.get_tool.call_count, 5)
        mock_tool_initialize.execute.assert_awaited_once()
        self.assertEqual(mock_tool_node.execute.await_count, 2)
        mock_tool_connect.execute.assert_awaited_once()
        mock_tool_render.execute.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
