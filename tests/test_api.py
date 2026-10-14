"""Exercise retry limits and error redaction without contacting the provider."""

import importlib
import sys
import types
import unittest
from pathlib import Path

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
