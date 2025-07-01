"""
Unit tests for diagram connection tools.
"""

from unittest.mock import MagicMock

import pytest

from src.diagram.engine import DiagramEngine
from src.diagram.tools.connection_tools import ConnectNodesTool


@pytest.fixture
def conn_tool() -> ConnectNodesTool:
    """Provides an instance of the ConnectNodesTool."""
    return ConnectNodesTool()


def test_tool_name_and_description(conn_tool: ConnectNodesTool):
    """Test that the tool has the correct name and description."""
    assert conn_tool.name == "connect_nodes"
    assert "Creates connections between diagram nodes" in conn_tool.description


def test_validate_parameters_success(conn_tool: ConnectNodesTool):
    """Test successful parameter validation."""
    params = conn_tool.validate_parameters(
        source=" node_a ",
        target=" node_b ",
        label="data flow",
        color="blue",
        style="dashed",
    )
    assert params["source"] == "node_a"
    assert params["target"] == "node_b"
    assert params["label"] == "data flow"
    assert params["color"] == "blue"
    assert params["style"] == "dashed"


def test_validate_parameters_unknown_style_param(conn_tool: ConnectNodesTool):
    """Test that unknown styling parameters are passed through with a warning."""
    # We can't easily test the logging call without more complex mocking,
    # but we can verify the parameter is still included.
    params = conn_tool.validate_parameters(source="a", target="b", custom_param="123")
    assert "custom_param" in params
    assert params["custom_param"] == "123"


def test_validate_parameters_missing_required(conn_tool: ConnectNodesTool):
    """Test that missing source or target raises a KeyError."""
    with pytest.raises(KeyError, match="Missing required parameter: source"):
        conn_tool.validate_parameters(target="b")

    with pytest.raises(KeyError, match="Missing required parameter: target"):
        conn_tool.validate_parameters(source="a")


def test_validate_parameters_same_source_target(conn_tool: ConnectNodesTool):
    """Test that connecting a node to itself raises a ValueError."""
    with pytest.raises(ValueError, match="Source and target nodes must be different"):
        conn_tool.validate_parameters(source="a", target="a")

    with pytest.raises(ValueError, match="Source and target nodes must be different"):
        conn_tool.validate_parameters(source=" a ", target="a")


@pytest.mark.parametrize(
    "param, value, expected_error, match_str",
    [
        ("source", "", ValueError, "Source node name must be a non-empty string"),
        ("target", "  ", ValueError, "Target node name must be a non-empty string"),
        ("label", 123, ValueError, "Label must be a string if provided"),
    ],
)
def test_validate_parameters_invalid_types(
    conn_tool: ConnectNodesTool, param, value, expected_error, match_str
):
    """Test that invalid parameter types or values raise ValueErrors."""
    kwargs = {"source": "a", "target": "b"}
    kwargs[param] = value
    with pytest.raises(expected_error, match=match_str):
        conn_tool.validate_parameters(**kwargs)


@pytest.mark.asyncio
async def test_execute_calls_engine_correctly(conn_tool: ConnectNodesTool):
    """Test that the execute method calls the engine's connection method."""
    mock_engine = MagicMock(spec=DiagramEngine)
    mock_engine.diagram = MagicMock()  # Pass engine state validation

    await conn_tool.execute(
        engine=mock_engine,
        source="node1",
        target="node2",
        label="my connection",
        style="dashed",
        penwidth="2.0",
    )

    mock_engine.connect_nodes.assert_called_once_with(
        source="node1",
        target="node2",
        label="my connection",
        style="dashed",
        penwidth="2.0",
    )


def test_connection_tool_requires_initialized_engine(conn_tool: ConnectNodesTool):
    """Test that the tool requires an initialized diagram."""
    mock_engine = MagicMock(spec=DiagramEngine)
    mock_engine.diagram = None
    with pytest.raises(ValueError, match="DiagramEngine not properly initialized"):
        conn_tool._validate_engine_state(mock_engine)
