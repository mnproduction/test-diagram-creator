"""
Unit tests for the Architect Agent.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.architect import ArchitectAgent
from src.agents.base import (
    ClusterDefinition,
    ComponentAnalysis,
    ComponentType,
    ConnectionSpec,
    ServiceComponent,
)


# Mock environment variables for all tests in this module
@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables to prevent ValueErrors on initialization."""
    with patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "test_key", "OPENROUTER_API_KEY": "test_key"},
    ):
        yield


@pytest.fixture
def architect_agent() -> ArchitectAgent:
    """Provides an instance of the ArchitectAgent."""
    # Mock the PydanticAI Agent constructor to avoid actual LLM calls
    with patch("pydantic_ai.Agent") as mock_pydantic_agent:
        # Make sure the mock agent can be instantiated
        mock_pydantic_agent.return_value = MagicMock()
        agent = ArchitectAgent()
    return agent


def test_architect_agent_initialization(architect_agent: ArchitectAgent):
    """Test that the agent initializes correctly with mocked keys."""
    assert architect_agent.agent_id == "architect"
    assert "gemini" in architect_agent.agents
    assert "openrouter" in architect_agent.agents
    assert architect_agent.gemini_model is not None


@pytest.mark.parametrize(
    "description, expected_title",
    [
        (
            'Create a diagram titled "My Awesome Architecture".',
            "My Awesome Architecture",
        ),
        (
            "The diagram is for a 'Secure Cloud Storage' system.",
            "Secure Cloud Storage",
        ),
        ("A basic system with no title specified.", "System Architecture"),
    ],
)
def test_extract_diagram_title(
    architect_agent: ArchitectAgent, description: str, expected_title: str
):
    """Test the extraction of diagram titles from descriptions."""
    title = architect_agent._extract_diagram_title(description)
    assert title == expected_title


@pytest.mark.parametrize(
    "service_name, component_name, expected_aws_service",
    [
        ("api gateway", "my_api", "apigateway"),
        ("Lambda", "my-function", "lambda"),
        ("s3 bucket", "data_lake", "s3"),
        ("A CI/CD build process", "builder", "codebuild"),
        ("The main git repository", "source_code", "codecommit"),
        ("PostgreSQL", "user_database", "rds"),
        ("A web server", "frontend_server", "ec2"),
        ("worker_process", "worker", "ec2"),
        ("unknown_service", "default_node", "ec2"),  # default case
    ],
)
def test_get_aws_tool_for_service(
    architect_agent: ArchitectAgent,
    service_name: str,
    component_name: str,
    expected_aws_service: str,
):
    """Test the intelligent mapping of service names to AWS tool types."""
    service = ServiceComponent(
        name=component_name,
        service_name=service_name,
        component_type=ComponentType.AWS_COMPUTE,  # Type doesn't drive the logic here
    )
    tool_name, params = architect_agent._get_aws_tool_for_service(service)
    assert tool_name == "create_aws_node"
    assert params["aws_service"] == expected_aws_service


def test_generate_execution_plan(architect_agent: ArchitectAgent):
    """Test the generation of an execution plan from a component analysis."""
    analysis = ComponentAnalysis(
        services=[
            ServiceComponent(
                name="user_api",
                service_name="API Gateway",
                component_type=ComponentType.AWS_NETWORK,
            ),
            ServiceComponent(
                name="auth_lambda",
                service_name="Lambda",
                component_type=ComponentType.AWS_COMPUTE,
            ),
            ServiceComponent(
                name="user_db",
                service_name="RDS",
                component_type=ComponentType.AWS_DATABASE,
            ),
        ],
        clusters=[
            ClusterDefinition(
                name="api_cluster", label="API Layer", services=["user_api"]
            ),
            ClusterDefinition(
                name="backend_cluster",
                label="Backend Services",
                services=["auth_lambda", "user_db"],
                parent="api_cluster",  # Nested cluster
            ),
        ],
        connections=[
            ConnectionSpec(source="user_api", target="auth_lambda", label="invokes"),
            ConnectionSpec(source="auth_lambda", target="user_db"),
        ],
        confidence_score=0.95,
    )

    description = 'A diagram titled "User Authentication Flow".'
    plan = architect_agent.generate_execution_plan(analysis, description)

    # 1. Check plan metadata
    assert plan.complexity_score > 0
    assert plan.tool_sequence[0].parameters["title"] == "User Authentication Flow"

    # 2. Check tool sequence content
    tool_calls = sorted(plan.tool_sequence, key=lambda x: x.execution_order)
    tool_names = [tc.tool_name for tc in tool_calls]

    # Expected sequence: init, cluster, cluster, node, node, node, connect, connect
    assert tool_names.count("initialize_diagram") == 1
    assert tool_names.count("create_cluster") == 2
    assert tool_names.count("create_aws_node") == 3
    assert tool_names.count("connect_nodes") == 2

    # 3. Check execution order logic
    init_call = next(tc for tc in tool_calls if tc.tool_name == "initialize_diagram")
    parent_cluster_call = next(
        tc for tc in tool_calls if tc.parameters.get("name") == "api_cluster"
    )
    child_cluster_call = next(
        tc for tc in tool_calls if tc.parameters.get("name") == "backend_cluster"
    )
    node_calls = [tc for tc in tool_calls if tc.tool_name == "create_aws_node"]
    connection_calls = [tc for tc in tool_calls if tc.tool_name == "connect_nodes"]

    # Assert parent cluster is created before child
    assert parent_cluster_call.execution_order < child_cluster_call.execution_order
    # Assert clusters are created after init
    assert init_call.execution_order < parent_cluster_call.execution_order
    # Assert nodes are created after clusters
    assert child_cluster_call.execution_order < min(
        tc.execution_order for tc in node_calls
    )
    # Assert connections are made after nodes
    assert max(tc.execution_order for tc in node_calls) < min(
        tc.execution_order for tc in connection_calls
    )

    # 4. Check specific tool parameters
    assert child_cluster_call.parameters["parent_name"] == "api_cluster"
    auth_node_call = next(
        tc for tc in node_calls if tc.parameters["name"] == "auth_lambda"
    )
    assert auth_node_call.parameters["cluster_name"] == "backend_cluster"
    connection = next(
        tc for tc in connection_calls if tc.parameters["source"] == "user_api"
    )
    assert connection.parameters["target"] == "auth_lambda"
    assert connection.parameters["label"] == "invokes"


# More tests will be added below for other methods.
