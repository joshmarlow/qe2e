from unittest import TestCase, mock

import requests

from qe2e.core import AssertContains, AssertEq, Case, GetUrl, RunState


class TestCase(TestCase):
    def setUp(self):
        self.case = Case(
            name="Login screen",
            tags=["no-auth"],
            steps=[
                GetUrl(
                    response_name="login_response",
                    url="localhost:8000/login",
                ),
                AssertEq(
                    actual="login_response.status_code",
                    expected=200,
                ),
                AssertEq(
                    actual="login_response.html.title",
                    expected="Login to continue",
                ),
                AssertContains(
                    container="login_response.html.content",
                    content="You really want to login",
                ),
            ],
        )

    @mock.patch.object(requests, "get")
    def test_execute(self, mock_get):
        mock_get.return_value = mock.Mock(
            status_code=200,
            content="""
            <html>
                <title>Login to continue</title>
                <body>
                    You really want to login
                </body>
            </html>
            """,
        )
        expected_run_state: RunState = {
            0: {"success": True},
            1: {"success": True},
            2: {"success": True},
            3: {"success": True},
            "login_response": {
                "html": {
                    "content": "\n"
                    "\n"
                    "Login to continue\n"
                    "\n"
                    "                    You really want "
                    "to login\n"
                    "                \n"
                    "\n",
                    "title": "Login to continue",
                },
                "status_code": 200,
            },
        }
        actual_run_result = self.case.evaluate()
        assert actual_run_result == expected_run_state

    def test_load(self):
        json = {
            "name": "Login screen",
            "steps": [
                {
                    "type": "get_url",
                    "url": "localhost:8000/login",
                    "response_name": "login_response",
                },
                {
                    "type": "assert_eq",
                    "actual": "login_response.status_code",
                    "expected": 200,
                },
                {
                    "type": "assert_eq",
                    "actual": "login_response.html.title",
                    "expected": "Login to continue",
                },
                {
                    "type": "assert_contains",
                    "container": "login_response.html.content",
                    "content": "You really want to login",
                },
            ],
            "tags": ["no-auth"],
        }
        actual_case = Case.from_dict(json)
        assert actual_case == self.case
