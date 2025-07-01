"""
Node Tools for Diagram Generation

Contains tools for creating and managing diagram nodes.
"""

from typing import Any

from src.diagram.engine import DiagramEngine

from .base_tool import BaseTool


class CreateAWSNodeTool(BaseTool):
    """Tool for creating AWS service nodes in the diagram."""

    name = "create_aws_node"
    description = "Creates an AWS service node in the diagram"

    # Define valid AWS services (from the DiagramEngine mapping)
    VALID_AWS_SERVICES = {
        "ec2",
        "rds",
        "elb",
        "apigateway",
        "sqs",
        "cloudwatch",
        "ecs",
        "eks",
        "sns",
        "codecommit",
        "codebuild",
        "s3",
        "lambda",
    }

    def validate_parameters(self, **kwargs) -> dict[str, Any]:
        """Validate AWS node creation parameters."""
        # Required parameters
        required_params = ["name", "aws_service"]
        for param in required_params:
            if param not in kwargs:
                raise KeyError(f"Missing required parameter: {param}")

        # Extract and validate parameters
        name = kwargs["name"]
        aws_service = kwargs["aws_service"]
        cluster_name = kwargs.get("cluster_name")
        label = kwargs.get("label")

        # Validate name
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Node name must be a non-empty string")

        # Validate AWS service
        if not isinstance(aws_service, str):
            raise ValueError("AWS service must be a string")

        aws_service_lower = aws_service.lower()
        if aws_service_lower not in self.VALID_AWS_SERVICES:
            raise ValueError(
                f"Invalid AWS service '{aws_service}'. "
                f"Valid services: {sorted(self.VALID_AWS_SERVICES)}"
            )

        # Validate cluster_name if provided
        if cluster_name is not None:
            if not isinstance(cluster_name, str) or not cluster_name.strip():
                raise ValueError("Cluster name must be a non-empty string if provided")

        # Validate label if provided
        if label is not None:
            if not isinstance(label, str):
                raise ValueError("Label must be a string if provided")

        # Return validated parameters
        validated = {
            "name": name.strip(),
            "aws_service": aws_service_lower,
            "cluster_name": cluster_name.strip() if cluster_name else None,
            "label": label if label is not None else name.strip(),
        }

        # Include any additional kwargs for styling
        for key, value in kwargs.items():
            if key not in validated:
                validated[key] = value

        return validated

    async def execute(self, engine: DiagramEngine, **kwargs) -> None:
        """Execute AWS node creation."""
        name = kwargs["name"]
        aws_service = kwargs["aws_service"]
        cluster_name = kwargs.get("cluster_name")
        label = kwargs["label"]

        # Extract additional styling parameters
        additional_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k not in ["name", "aws_service", "cluster_name", "label"]
        }

        self.logger.info(
            f"Creating {aws_service.upper()} node '{name}' (label: '{label}')"
            f"{f' in cluster {cluster_name}' if cluster_name else ''}"
        )

        # Call the engine's node creation method
        engine.create_aws_node(
            name=name,
            aws_service=aws_service,
            cluster_name=cluster_name,
            label=label,
            **additional_kwargs,
        )

        self.logger.debug(
            f"AWS node '{name}' created successfully"
            f"{f' in cluster {cluster_name}' if cluster_name else ''}"
        )
