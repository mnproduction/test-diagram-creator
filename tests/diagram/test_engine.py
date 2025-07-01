# tests/diagram/test_engine.py

import unittest
from unittest.mock import ANY, MagicMock, patch

from src.diagram.engine import ContextManagementException, DiagramEngine


class TestDiagramEngine(unittest.TestCase):
    def setUp(self):
        """Set up a new DiagramEngine for each test."""
        self.engine = DiagramEngine()

    @patch("src.diagram.engine.Diagram")
    def test_initialization(self, mock_diagram_class):
        """Test that the diagram is initialized correctly."""
        self.engine.initialize_diagram(title="Test Diag", graph_attr={"fontsize": "10"})
        mock_diagram_class.assert_called_once_with(
            "Test Diag", show=False, graph_attr={"fontsize": "10"}
        )
        mock_diagram_class.return_value.__enter__.assert_called_once()

    def test_error_on_action_before_init(self):
        """Test that actions before initialization raise an exception."""
        with self.assertRaises(ContextManagementException):
            self.engine.create_cluster("test", "Test")
        with self.assertRaises(ContextManagementException):
            self.engine.create_aws_node("test", "ec2")

    @patch("src.diagram.engine.Diagram")
    def test_state_after_render(self, mock_diagram_class):
        """
        Test that engine state (nodes, clusters) is cleared after rendering.
        This also implicitly tests successful creation.
        """
        # Mock the __exit__ call to prevent external rendering process
        mock_diagram_instance = mock_diagram_class.return_value
        mock_diagram_instance.filename = "test_diagram"
        mock_diagram_instance.__exit__.return_value = None

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open") as mock_open,
            patch("os.remove"),
            patch("diagrams.getdiagram") as mock_getdiagram,
        ):
            mock_getdiagram.return_value = mock_diagram_instance
            mock_open.return_value.__enter__.return_value.read.return_value = (
                b"imagedata"
            )

            self.engine.diagram = mock_diagram_instance
            self.engine.create_cluster(
                name="my_cluster", label="My Cluster", cluster_name=None
            )
            self.engine.create_aws_node(
                name="my_node",
                aws_service="ec2",
                cluster_name="my_cluster",
                label="My Node",
            )

            result = self.engine.render(dry_run=True)

            # After render, state should be cleared
            self.assertTrue(result["success"])
            self.assertIsNotNone(result["image_data"])
            self.assertEqual(len(result["components_used"]), 1)
            self.assertIsNone(self.engine.diagram)
            self.assertEqual(len(self.engine.nodes), 0)

    @patch("src.diagram.engine.Diagram")
    @patch("src.diagram.engine.Cluster")
    @patch("src.diagram.engine.EC2")
    def test_node_creation_in_cluster(self, mock_ec2_class, mock_cluster_class, _):
        """Test node is created within the correct cluster context."""
        self.engine.initialize_diagram()
        # Mock the __exit__ call to prevent external rendering process
        self.engine.diagram.__exit__ = MagicMock()

        with patch("diagrams.getdiagram") as mock_getdiagram, patch("os.remove"):
            mock_getdiagram.return_value = self.engine.diagram
            self.engine.diagram.render = MagicMock(return_value="mock_diagram.png")

            self.engine.create_cluster(name="c1", label="Cluster 1")
            self.engine.create_aws_node(name="n1", aws_service="ec2", cluster_name="c1")

            self.engine.render(dry_run=True)

            mock_cluster_class.assert_called_once_with("Cluster 1", graph_attr=ANY)
            mock_cluster_class.return_value.__enter__.assert_called()
            mock_ec2_class.assert_called_once_with("n1")


if __name__ == "__main__":
    unittest.main()
