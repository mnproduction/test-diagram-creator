"""
Unit tests for diagram cluster creation tools.
"""

from unittest.mock import MagicMock

import pytest

from src.diagram.engine import DiagramEngine
from src.diagram.tools.cluster_tools import CreateClusterTool


@pytest.fixture
def cluster_tool() -> CreateClusterTool:
    """Provides an instance of the CreateClusterTool."""
    return CreateClusterTool()


def test_tool_name_and_description(cluster_tool: CreateClusterTool):
    """Test that the tool has the correct name and description."""
    assert cluster_tool.name == "create_cluster"
    assert "Creates a cluster to group" in cluster_tool.description


def test_validate_parameters_success(cluster_tool: CreateClusterTool):
    """Test successful parameter validation with all arguments."""
    params = cluster_tool.validate_parameters(
        name=" k8s_cluster ",
        label=" K8s Components ",
        parent_name=" cloud_provider ",
        graph_attr={"fontsize": "12", "bgcolor": "lightgrey"},
    )
    assert params["name"] == "k8s_cluster"
    assert params["label"] == "K8s Components"
    assert params["parent_name"] == "cloud_provider"
    assert params["graph_attr"] == {"fontsize": "12", "bgcolor": "lightgrey"}


def test_validate_parameters_defaults(cluster_tool: CreateClusterTool):
    """Test that optional parameters have correct default values."""
    params = cluster_tool.validate_parameters(name="c1", label="L1")
    assert params["parent_name"] is None
    assert params["graph_attr"] == {}


def test_validate_parameters_missing_required(cluster_tool: CreateClusterTool):
    """Test that missing required parameters raise a KeyError."""
    with pytest.raises(KeyError, match="Missing required parameter: name"):
        cluster_tool.validate_parameters(label="l1")

    with pytest.raises(KeyError, match="Missing required parameter: label"):
        cluster_tool.validate_parameters(name="n1")


@pytest.mark.parametrize(
    "param, value, expected_error, match_str",
    [
        ("name", "", ValueError, "Cluster name must be a non-empty string"),
        ("label", "  ", ValueError, "Cluster label must be a non-empty string"),
        ("graph_attr", [], ValueError, "graph_attr must be a dictionary"),
        (
            "parent_name",
            " ",
            ValueError,
            "Parent cluster name must be a non-empty string if provided",
        ),
    ],
)
def test_validate_parameters_invalid_types(
    cluster_tool: CreateClusterTool, param, value, expected_error, match_str
):
    """Test that various invalid parameter types or values raise ValueErrors."""
    kwargs = {"name": "n1", "label": "l1"}
    kwargs[param] = value
    with pytest.raises(expected_error, match=match_str):
        cluster_tool.validate_parameters(**kwargs)


@pytest.mark.asyncio
async def test_execute_calls_engine_correctly(cluster_tool: CreateClusterTool):
    """Test that execute calls the engine's create_cluster method correctly."""
    mock_engine = MagicMock(spec=DiagramEngine)
    mock_engine.diagram = MagicMock()  # Pass engine state validation

    await cluster_tool.execute(
        engine=mock_engine,
        name="my_cluster",
        label="My Awesome Cluster",
        parent_name="root",
        graph_attr={"bgcolor": "lightblue"},
    )

    mock_engine.create_cluster.assert_called_once_with(
        name="my_cluster",
        label="My Awesome Cluster",
        cluster_name="root",  # Note: parent_name maps to cluster_name in engine
        graph_attr={"bgcolor": "lightblue"},
    )


def test_cluster_tool_requires_initialized_engine(cluster_tool: CreateClusterTool):
    """Test that the tool's _validate_engine_state requires an initialized diagram."""
    mock_engine = MagicMock(spec=DiagramEngine)
    mock_engine.diagram = None
    with pytest.raises(ValueError, match="DiagramEngine not properly initialized"):
        cluster_tool._validate_engine_state(mock_engine)
