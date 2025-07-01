"""
Unit tests for diagram node creation tools.
"""

from unittest.mock import MagicMock

import pytest

from src.diagram.engine import DiagramEngine
from src.diagram.tools.node_tools import CreateAWSNodeTool


@pytest.fixture
def node_tool() -> CreateAWSNodeTool:
    """Provides an instance of the CreateAWSNodeTool."""
    return CreateAWSNodeTool()


def test_tool_name_and_description(node_tool: CreateAWSNodeTool):
    """Test that the tool has the correct name and description."""
    assert node_tool.name == "create_aws_node"
    assert "Creates an AWS service node" in node_tool.description


def test_validate_parameters_success(node_tool: CreateAWSNodeTool):
    """Test successful parameter validation with all possible arguments."""
    params = node_tool.validate_parameters(
        name=" my_ec2 ",
        aws_service="EC2",
        label="My EC2 Instance",
        cluster_name=" my_cluster ",
        fontsize="10",
    )
    assert params["name"] == "my_ec2"
    assert params["aws_service"] == "ec2"
    assert params["label"] == "My EC2 Instance"
    assert params["cluster_name"] == "my_cluster"
    assert params["fontsize"] == "10"


def test_validate_parameters_defaults_label(node_tool: CreateAWSNodeTool):
    """Test that the label defaults to the node name if not provided."""
    params = node_tool.validate_parameters(name="my_rds", aws_service="rds")
    assert params["label"] == "my_rds"


def test_validate_parameters_missing_required(node_tool: CreateAWSNodeTool):
    """Test that missing required parameters raise a KeyError."""
    with pytest.raises(KeyError, match="Missing required parameter: name"):
        node_tool.validate_parameters(aws_service="ec2")

    with pytest.raises(KeyError, match="Missing required parameter: aws_service"):
        node_tool.validate_parameters(name="my_node")


def test_validate_parameters_invalid_service(node_tool: CreateAWSNodeTool):
    """Test that an invalid AWS service raises a ValueError."""
    with pytest.raises(ValueError, match="Invalid AWS service 'invalid_service'"):
        node_tool.validate_parameters(name="my_node", aws_service="invalid_service")


@pytest.mark.parametrize(
    "param, value, expected_error, match_str",
    [
        ("name", "", ValueError, "Node name must be a non-empty string"),
        ("name", "   ", ValueError, "Node name must be a non-empty string"),
        ("aws_service", 123, ValueError, "AWS service must be a string"),
        (
            "cluster_name",
            "",
            ValueError,
            "Cluster name must be a non-empty string if provided",
        ),
        ("label", 123, ValueError, "Label must be a string if provided"),
    ],
)
def test_validate_parameters_invalid_types(
    node_tool: CreateAWSNodeTool, param, value, expected_error, match_str
):
    """Test that various invalid parameter types raise ValueErrors."""
    kwargs = {"name": "my_node", "aws_service": "ec2"}
    kwargs[param] = value
    with pytest.raises(expected_error, match=match_str):
        node_tool.validate_parameters(**kwargs)


@pytest.mark.asyncio
async def test_execute_calls_engine_correctly(node_tool: CreateAWSNodeTool):
    """Test that the execute method calls the engine's creation method."""
    mock_engine = MagicMock(spec=DiagramEngine)
    mock_engine.diagram = MagicMock()  # Pass engine state validation

    await node_tool.execute(
        engine=mock_engine,
        name="my_lambda",
        aws_service="lambda",
        label="My Lambda Func",
        cluster_name="compute",
        shape="box",
        style="dashed",
    )

    mock_engine.create_aws_node.assert_called_once_with(
        name="my_lambda",
        aws_service="lambda",
        label="My Lambda Func",
        cluster_name="compute",
        shape="box",
        style="dashed",
    )


def test_node_tool_requires_initialized_engine(node_tool: CreateAWSNodeTool):
    """Test that the tool's _validate_engine_state requires an initialized diagram."""
    mock_engine = MagicMock(spec=DiagramEngine)
    mock_engine.diagram = None  # Simulate uninitialized state
    with pytest.raises(ValueError, match="DiagramEngine not properly initialized"):
        node_tool._validate_engine_state(mock_engine)
