import base64
import logging
import os
from typing import Any

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2, ECS, EKS, Lambda
from diagrams.aws.database import RDS
from diagrams.aws.devtools import Codebuild, Codecommit
from diagrams.aws.integration import SNS, SQS
from diagrams.aws.management import Cloudwatch
from diagrams.aws.network import ELB, APIGateway
from diagrams.aws.storage import S3

from src.core.exceptions import ContextManagementException, RenderingException

logger = logging.getLogger(__name__)


class DiagramEngine:
    """
    Core engine for building and rendering diagrams.
    Fixed version that properly handles cluster node assignment.
    """

    def __init__(self):
        self.diagram = None
        self.nodes = {}
        self.clusters = {}  # cluster_name -> {"label": str, "graph_attr": dict}
        self.pending_nodes = []  # List of node creation requests
        self.connections = []  # List of connection requests

    def initialize_diagram(self, title="My Diagram", graph_attr: dict = None):
        """Initializes a new diagram with optional graph attributes."""
        logger.info(f"Initializing diagram: {title}")
        attrs = graph_attr or {}
        self.diagram = Diagram(title, show=False, graph_attr=attrs)
        self.diagram.__enter__()

    def create_cluster(
        self, name: str, label: str, graph_attr: dict = None, cluster_name: str = None
    ):
        """Records cluster definition for later creation during rendering."""
        if not self.diagram:
            raise ContextManagementException(
                "Diagram not initialized. Call initialize_diagram() first."
            )

        attrs = graph_attr or {}
        self.clusters[name] = {
            "label": label,
            "graph_attr": attrs,
            "parent_cluster": cluster_name,
        }
        logger.debug(f"Recorded cluster definition: {name} ('{label}')")

    def create_aws_node(
        self,
        name: str,
        aws_service: str,
        cluster_name: str = None,
        label: str = None,
        **kwargs,
    ):
        """Records node creation request for later execution during rendering."""
        if not self.diagram:
            raise ContextManagementException("Diagram not initialized.")

        node_label = label if label is not None else name

        # Store node creation request
        node_request = {
            "name": name,
            "aws_service": aws_service,
            "cluster_name": cluster_name,
            "label": node_label,
            "kwargs": kwargs,
        }
        self.pending_nodes.append(node_request)

        logger.debug(
            f"Recorded node request: '{name}' (label: '{node_label}') of type '{aws_service}'"
            f"{f' for cluster {cluster_name}' if cluster_name else ''}"
        )

    def connect_nodes(self, source: str, target: str, label: str = "", **kwargs):
        """Records connection request for later execution during rendering."""
        # Store connection request
        connection_request = {
            "source": source,
            "target": target,
            "label": label,
            "kwargs": kwargs,
        }
        self.connections.append(connection_request)
        logger.debug(
            f"Recorded connection request: '{source}' -> '{target}'"
            f"{f' (label: {label})' if label else ''}"
        )

    def render(self, output_format: str = "png", dry_run: bool = False) -> dict:
        """
        Renders the diagram to the specified format and returns the result.
        If dry_run is True, it simulates rendering without writing a file.
        """
        if not self.diagram:
            raise ContextManagementException("Cannot render an uninitialized diagram.")

        try:
            logger.info("Creating clusters and nodes...")

            # Step 1 & 2: Create all diagram elements
            self._create_clusters_and_nodes()
            self._create_connections()

            logger.info("Rendering final diagram...")

            if dry_run:
                logger.debug("Dry run enabled. Skipping file rendering.")
                return {
                    "success": True,
                    "image_data": "dry_run_placeholder",
                    "components_used": list(self.nodes.keys()),
                }

            # Step 3: Render diagram by exiting the context, which writes the file
            self.diagram.__exit__(None, None, None)

            # Read the generated image file and encode it as base64
            image_filename = f"{self.diagram.filename}.{output_format}"
            if not os.path.exists(image_filename):
                logger.error(f"Rendered diagram file not found: {image_filename}")
                raise RenderingException(
                    f"Output file not found after rendering: {image_filename}"
                )

            with open(image_filename, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")

            # Step 4: Clean up the created diagram file
            try:
                os.remove(image_filename)
                logger.debug(f"Cleaned up temporary file: {image_filename}")
            except (PermissionError, OSError) as cleanup_error:
                logger.warning(
                    f"Could not remove temporary file {image_filename}: {cleanup_error}"
                )

            return {
                "success": True,
                "image_data": image_data,
                "components_used": list(self.nodes.keys()),
            }
        except Exception as e:
            logger.error("Failed to render diagram: %s", e, exc_info=True)
            raise RenderingException(f"Failed to render diagram: {e}") from e
        finally:
            # Ensure state is cleared for the next run
            self._clear_state()

    def _create_clusters_and_nodes(self):
        """Creates clusters and nodes in the correct hierarchy using recursion."""

        # 1. Organize nodes by their parent cluster
        nodes_by_cluster = {}
        for node_request in self.pending_nodes:
            cluster_name = node_request.get("cluster_name")
            if cluster_name not in nodes_by_cluster:
                nodes_by_cluster[cluster_name] = []
            nodes_by_cluster[cluster_name].append(node_request)

        # 2. Organize clusters by their parent
        clusters_by_parent = {}
        for cluster_name, cluster_info in self.clusters.items():
            parent_name = cluster_info.get("parent_cluster")
            if parent_name not in clusters_by_parent:
                clusters_by_parent[parent_name] = []
            clusters_by_parent[parent_name].append(cluster_name)

        # 3. Recursive function to build clusters
        def _create_cluster_recursively(parent_cluster_name: str):
            # Create nodes directly under this parent
            if parent_cluster_name in nodes_by_cluster:
                for node_request in nodes_by_cluster[parent_cluster_name]:
                    self._create_single_node(node_request)

            # Create child clusters of this parent
            if parent_cluster_name in clusters_by_parent:
                for child_cluster_name in clusters_by_parent[parent_cluster_name]:
                    child_cluster_info = self.clusters[child_cluster_name]
                    with Cluster(
                        child_cluster_info["label"],
                        graph_attr=child_cluster_info["graph_attr"],
                    ):
                        _create_cluster_recursively(child_cluster_name)

        # 4. Start the process
        # Create top-level nodes (no parent cluster)
        if None in nodes_by_cluster:
            logger.info(f"🔍 CREATING {len(nodes_by_cluster[None])} UNCLUSTERED NODES")
            for node_request in nodes_by_cluster[None]:
                self._create_single_node(node_request)

        # Create top-level clusters (no parent cluster)
        if None in clusters_by_parent:
            logger.info(
                f"🔍 CREATING {len(clusters_by_parent[None])} TOP-LEVEL CLUSTERS"
            )
            for cluster_name in clusters_by_parent[None]:
                cluster_info = self.clusters[cluster_name]
                with Cluster(
                    cluster_info["label"], graph_attr=cluster_info["graph_attr"]
                ):
                    _create_cluster_recursively(cluster_name)

    def _create_single_node(self, node_request):
        """Creates a single node from a node request."""
        name = node_request["name"]
        aws_service = node_request["aws_service"]
        node_label = node_request["label"]
        kwargs = node_request["kwargs"]

        node_class = self._get_aws_node_class(aws_service)
        node = node_class(node_label)
        self.nodes[name] = node

        if kwargs:
            logger.debug(
                f"Created node '{name}' (label: '{node_label}') of type '{aws_service}' - styling requested: {kwargs}"
            )
        else:
            logger.debug(
                f"Created node '{name}' (label: '{node_label}') of type '{aws_service}'"
            )

    def _create_connections(self):
        """Creates all recorded connections."""
        logger.info(f"🔍 CREATING {len(self.connections)} CONNECTIONS")
        for connection_request in self.connections:
            source = connection_request["source"]
            target = connection_request["target"]
            label = connection_request["label"]
            kwargs = connection_request["kwargs"]

            source_node = self.nodes.get(source)
            target_node = self.nodes.get(target)

            if source_node and target_node:
                # Apply edge styling if provided
                if kwargs or label:
                    edge_attrs = {}
                    if label:
                        edge_attrs["label"] = label

                    # Map connection styling parameters to Edge attributes
                    style_mapping = {
                        "color": "color",
                        "penwidth": "penwidth",
                        "arrowsize": "arrowsize",
                        "style": "style",
                        "fontcolor": "fontcolor",
                        "fontsize": "fontsize",
                    }

                    for param, edge_attr in style_mapping.items():
                        if param in kwargs:
                            edge_attrs[edge_attr] = kwargs[param]

                    # Create styled connection
                    if edge_attrs:
                        source_node >> Edge(**edge_attrs) >> target_node
                        logger.debug(
                            f"🔍 CONNECTED: '{source}' -> '{target}' with styled edge: {edge_attrs}"
                        )
                    else:
                        source_node >> target_node
                        logger.debug(
                            f"🔍 CONNECTED: '{source}' -> '{target}' with basic edge"
                        )
                else:
                    # Basic connection without styling
                    source_node >> target_node
                    logger.debug(
                        f"🔍 CONNECTED: '{source}' -> '{target}' with basic edge"
                    )
            else:
                logger.warning(
                    f"Could not connect nodes: '{source}' or '{target}' not found."
                )

    def _get_aws_node_class(self, service_name: str):
        """Maps a service name string to its corresponding diagrams class."""
        service_map = {
            "ec2": EC2,
            "rds": RDS,
            "elb": ELB,
            "apigateway": APIGateway,
            "sqs": SQS,
            "cloudwatch": Cloudwatch,
            "ecs": ECS,
            "eks": EKS,
            "sns": SNS,
            "codecommit": Codecommit,
            "codebuild": Codebuild,
            "s3": S3,
            "lambda": Lambda,
        }
        return service_map.get(service_name.lower(), EC2)  # Default to EC2

    def _clear_state(self):
        """Clears the state of the engine for the next run."""
        self.nodes = {}
        self.clusters = {}
        self.pending_nodes = []
        self.connections = []
        self.diagram = None

    def _get_node_by_name(self, name: str) -> Any:
        """Retrieve a node object by its unique name."""
        return self.nodes.get(name)
