import unittest
from unittest.mock import patch, Mock
from api.deployment_utils import check_deployment_status


class TestDeploymentStatus(unittest.TestCase):

    @patch("api.deployment_utils.requests.get")
    def test_deployment_is_up(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        self.assertTrue(check_deployment_status("https://fake-url"))

    @patch("api.deployment_utils.requests.get")
    def test_deployment_is_down(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp

        self.assertFalse(check_deployment_status("https://fake-url"))

    @patch("api.deployment_utils.requests.get")
    def test_deployment_raises_exception(self, mock_get):
        mock_get.side_effect = Exception("Network error")

        self.assertFalse(check_deployment_status("https://fake-url"))