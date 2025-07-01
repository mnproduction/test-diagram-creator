import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from main import app
from src.agents.base import DiagramResponse
from src.core.settings import settings

# Use one of the default allowed keys for successful tests
VALID_API_KEY = settings.security.allowed_api_keys[0]


class TestE2E(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch(
        "src.agents.coordinator.CoordinatorAgent.generate_diagram",
        new_callable=AsyncMock,
    )
    def test_generate_diagram_endpoint_success(self, mock_generate_diagram):
        """
        End-to-end test for the /generate-diagram endpoint, mocking the coordinator.
        """
        # --- ARRANGE ---
        mock_response_data = {
            "success": True,
            "result": {
                "success": True,
                "image_data": "base64_encoded_image_data",
                "components_used": ["EC2", "RDS"],
                "generation_time_ms": 1234,
            },
            "analysis": {
                "services": [],
                "clusters": [],
                "connections": [],
                "confidence_score": 0.9,
            },
            "execution_plan": {
                "tool_sequence": [],
                "cluster_strategy": "none",
                "layout_preference": "TB",
                "estimated_duration": 10,
                "complexity_score": 0.5,
            },
        }
        mock_response = DiagramResponse(**mock_response_data)
        mock_generate_diagram.return_value = mock_response

        request_data = {
            "description": "An EC2 instance connected to an RDS database.",
            "session_id": "e2e-test-session",
        }
        headers = {"X-API-Key": VALID_API_KEY}

        # --- ACT ---
        response = self.client.post(
            "/generate-diagram", json=request_data, headers=headers
        )

        # --- ASSERT ---
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertTrue(response_json["success"])
        self.assertEqual(
            response_json["result"]["image_data"], "base64_encoded_image_data"
        )

        mock_generate_diagram.assert_awaited_once()
        called_context = mock_generate_diagram.call_args[0][0]
        self.assertEqual(
            called_context.original_description, request_data["description"]
        )


if __name__ == "__main__":
    unittest.main()
