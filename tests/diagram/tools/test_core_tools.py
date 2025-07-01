"""
Unit tests for core diagramming tools.
"""

from unittest.mock import MagicMock

import pytest

from src.diagram.engine import DiagramEngine
from src.diagram.tools.core_tools import InitializeDiagramTool, RenderDiagramTool


# Tests for InitializeDiagramTool
@pytest.fixture
def init_tool() -> InitializeDiagramTool:
    """Provides an instance of the InitializeDiagramTool."""
    return InitializeDiagramTool()


def test_initialize_diagram_tool_name_and_description(init_tool: InitializeDiagramTool):
    """Test that the tool has the correct name and description."""
    assert init_tool.name == "initialize_diagram"
    assert "Initializes a new diagram" in init_tool.description


def test_validate_parameters_defaults(init_tool: InitializeDiagramTool):
    """Test parameter validation with default values."""
    params = init_tool.validate_parameters()
    assert params["title"] == "My Diagram"
    assert params["graph_attr"] == {}


def test_validate_parameters_custom(init_tool: InitializeDiagramTool):
    """Test parameter validation with custom values."""
    graph_attr = {"fontsize": "12", "bgcolor": "lightblue"}
    params = init_tool.validate_parameters(title="Custom Title", graph_attr=graph_attr)
    assert params["title"] == "Custom Title"
    assert params["graph_attr"] == graph_attr


def test_validate_parameters_invalid_title_type(init_tool: InitializeDiagramTool):
    """Test that a non-string title raises a ValueError."""
    with pytest.raises(ValueError, match="Title must be a string"):
        init_tool.validate_parameters(title=12345)


def test_validate_parameters_invalid_graph_attr_type(init_tool: InitializeDiagramTool):
    """Test that a non-dict graph_attr raises a ValueError."""
    with pytest.raises(ValueError, match="graph_attr must be a dictionary"):
        init_tool.validate_parameters(graph_attr=["not", "a", "dict"])


@pytest.mark.asyncio
async def test_execute_initialization(init_tool: InitializeDiagramTool):
    """Test the execution of the initialization tool."""
    mock_engine = MagicMock(spec=DiagramEngine)
    # Mock the method directly on the mock object
    mock_engine.initialize_diagram = MagicMock()

    title = "My Test Diagram"
    graph_attr = {"label": "Test Diagram"}

    # The execute method gets the validated parameters
    await init_tool.execute(engine=mock_engine, title=title, graph_attr=graph_attr)

    # Verify that the engine's method was called correctly
    mock_engine.initialize_diagram.assert_called_once_with(
        title=title, graph_attr=graph_attr
    )


def test_validate_engine_state_override(init_tool: InitializeDiagramTool):
    """
    Verify that InitializeDiagramTool overrides _validate_engine_state
    and does not raise an error if the diagram is not yet present.
    """
    mock_engine = MagicMock(spec=DiagramEngine)
    mock_engine.diagram = None
    try:
        # This method is protected, but we test it to ensure the override is correct
        init_tool._validate_engine_state(mock_engine)
    except ValueError:
        pytest.fail(
            "InitializeDiagramTool._validate_engine_state should not raise an error."
        )


# Tests for RenderDiagramTool
@pytest.fixture
def render_tool() -> RenderDiagramTool:
    """Provides an instance of the RenderDiagramTool."""
    return RenderDiagramTool()


def test_render_diagram_tool_name_and_description(render_tool: RenderDiagramTool):
    """Test that the tool has the correct name and description."""
    assert render_tool.name == "render_diagram"
    assert "Renders the final diagram" in render_tool.description


def test_render_validate_parameters_defaults(render_tool: RenderDiagramTool):
    """Test parameter validation with default format."""
    params = render_tool.validate_parameters()
    assert params["output_format"] == "png"


@pytest.mark.parametrize("output_format", ["png", "svg", "pdf"])
def test_render_validate_parameters_valid_formats(
    render_tool: RenderDiagramTool, output_format: str
):
    """Test parameter validation with all valid formats."""
    params = render_tool.validate_parameters(output_format=output_format)
    assert params["output_format"] == output_format


def test_render_validate_parameters_invalid_format(render_tool: RenderDiagramTool):
    """Test that an invalid format raises a ValueError."""
    with pytest.raises(ValueError, match="Invalid output format 'jpg'"):
        render_tool.validate_parameters(output_format="jpg")


@pytest.mark.asyncio
async def test_render_execute_calls_engine(render_tool: RenderDiagramTool):
    """Test that the execute method calls the engine's render method."""
    mock_engine = MagicMock(spec=DiagramEngine)
    mock_engine.diagram = MagicMock()  # To pass _validate_engine_state
    render_result = {"success": True, "components_used": ["c1", "c2"]}
    mock_engine.render.return_value = render_result

    validated_params = render_tool.validate_parameters(output_format="svg")
    result = await render_tool.execute(engine=mock_engine, **validated_params)

    mock_engine.render.assert_called_once_with(output_format="svg", dry_run=False)
    assert result == render_result


def test_render_requires_initialized_engine(render_tool: RenderDiagramTool):
    """Test that RenderDiagramTool requires an initialized engine."""
    mock_engine = MagicMock(spec=DiagramEngine)
    mock_engine.diagram = None  # Uninitialized state
    with pytest.raises(ValueError, match="DiagramEngine not properly initialized"):
        render_tool._validate_engine_state(mock_engine)
