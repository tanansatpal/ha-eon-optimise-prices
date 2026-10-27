"""Exercise retry limits and error redaction without contacting the provider."""

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError

package = types.ModuleType("optimise_test")
package.__path__ = [str(Path(__file__).parents[1] / "custom_components/eon_next_optimise")]
sys.modules.setdefault("optimise_test", package)
api = importlib.import_module("optimise_test.api")


class Response:
    """A minimal async HTTP response."""

    def __init__(self, status, payload):
        self.status, self.payload = status, payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def json(self):
        return self.payload


class Session:
    """Count exact HTTP attempts."""

    def __init__(self, responses):
        self.responses, self.calls = iter(responses), []

    def post(self, url, **kwargs):
        self.calls.append(url)
        return next(self.responses)


class ApiTests(unittest.IsolatedAsyncioTestCase):
    """A failed feed must not spin, leak secrets or publish partial schedules."""

    async def executor(self, function):
        function()

    def client(self, responses):
        client = api.OptimiseClient(Session(responses), "private-email", "private-password")
        client.auth_calls = 0

        def authenticate():
            client.auth_calls += 1
            client.id_token = "private-token"
            client.expires = float("inf")

        client.authenticate = authenticate
        return client

    async def test_401_retries_exactly_once(self):
        client = self.client([Response(401, {}), Response(401, {})])
        with self.assertRaises(api.AuthenticationError):
            await client.fetch(self.executor)
        self.assertEqual(len(client.session.calls), 2)
        self.assertEqual(client.auth_calls, 2)

    async def test_500_not_retried(self):
        client = self.client([Response(500, {})])
        with self.assertRaises(api.PriceFeedError):
            await client.fetch(self.executor)
        self.assertEqual(len(client.session.calls), 1)

    async def test_provider_error_text_redacted(self):
        client = self.client([Response(200, {"errors": [{"message": "private-token"}]})])
        with self.assertRaises(api.PriceFeedError) as caught:
            await client.fetch(self.executor)
        self.assertNotIn("private", str(caught.exception))

    async def test_success_uses_one_request(self):
        payload = {
            "data": {
                "sitePricing": {
                    "meterWindows": [
                        {
                            "usageType": direction,
                            "currentPeriod": {
                                "start": "2026-09-11T19:00:00Z",
                                "kwhPriceInCents": value,
                            },
                        }
                        for direction, value in (("GENERAL", 30), ("FEED_IN", -25))
                    ]
                }
            }
        }
        client = self.client([Response(200, payload)])
        self.assertEqual((await client.fetch(self.executor))["export"][0]["value_inc_vat"], 25)
        self.assertEqual(len(client.session.calls), 1)


def cognito_failing_with(error):
    """A Cognito stand-in whose password sign-in raises the given error."""

    class FailingCognito:
        def __init__(self, *args, **kwargs):
            self.id_token = None
            self.refresh_token = kwargs.get("refresh_token")

        def authenticate(self, password):
            raise error

    return FailingCognito


class AuthenticateTests(unittest.TestCase):
    """Only a rejected login may ask the user to re-authenticate."""

    def authenticate(self, error):
        client = api.OptimiseClient(None, "private-email", "private-password")
        with patch.object(api, "Cognito", cognito_failing_with(error)):
            client.authenticate()

    def test_network_failures_are_temporary(self):
        for error in (
            EndpointConnectionError(endpoint_url="https://cognito.invalid"),
            ReadTimeoutError(endpoint_url="https://cognito.invalid"),
        ):
            with self.subTest(error=type(error).__name__):
                with self.assertRaises(api.PriceFeedError):
                    self.authenticate(error)

    def test_rejected_login_needs_attention(self):
        error = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "private"}}, "InitiateAuth"
        )
        with self.assertRaises(api.AuthenticationError) as caught:
            self.authenticate(error)
        self.assertNotIn("private", str(caught.exception))
