"""Contract tests based on the authenticated Optimise response, 11 Sep 2026."""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "optimise_rates", Path(__file__).parents[1] / "custom_components/eon_next_optimise/rates.py"
)
rates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rates)


def payload(price=30, export=-25, start="2026-09-11T19:00:00Z"):
    """Return a minimal real-response-shaped fixture without account details."""
    return {
        "data": {
            "sitePricing": {
                "meterWindows": [
                    {
                        "usageType": "GENERAL",
                        "currentPeriod": {"start": start, "kwhPriceInCents": price},
                    },
                    {
                        "usageType": "FEED_IN",
                        "currentPeriod": {"start": start, "kwhPriceInCents": export},
                    },
                ]
            }
        }
    }


class OptimiseRatesTests(unittest.TestCase):
    """Validate units, signs, coverage and invalid input rejection."""

    def test_screenshot_current_prices(self):
        result = rates.normalise_response(payload())
        self.assertEqual(result["import"][0]["value_inc_vat"], 30)
        self.assertEqual(result["export"][0]["value_inc_vat"], 25)

    def test_negative_export_and_zero_import_preserved(self):
        result = rates.normalise_response(payload(0, 3))
        self.assertEqual(result["import"][0]["value_inc_vat"], 0)
        self.assertEqual(result["export"][0]["value_inc_vat"], -3)

    def test_bst_instant(self):
        result = rates.normalise_response(payload(start="2026-09-11T20:00:00+01:00"))
        self.assertEqual(result["import"][0]["valid_from"], "2026-09-11T19:00:00+00:00")

    def test_half_open_current_interval(self):
        result = rates.normalise_response(payload())["import"]
        self.assertIsNotNone(rates.coverage(result, rates.parse_time("2026-09-11T19:29:59Z"))[0])
        self.assertEqual(
            rates.coverage(result, rates.parse_time("2026-09-11T19:30:00Z")), (None, None)
        )

    def test_gaps_are_not_filled(self):
        p = payload()
        p["data"]["sitePricing"]["meterWindows"][0]["forecastPeriods"] = [
            {"start": "2026-09-11T20:00:00Z", "kwhPriceInCents": 27}
        ]
        result = rates.normalise_response(p)["import"]
        self.assertEqual(
            rates.coverage(result, rates.parse_time("2026-09-11T19:10:00Z"))[1],
            "2026-09-11T19:30:00+00:00",
        )
        self.assertEqual(result[1]["source_quality"], "forecast")

    def test_invalid_numeric_prices(self):
        for value in (None, True, "30", float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                rates.normalise_response(payload(price=value))

    def test_naive_or_five_minute_timestamp_rejected(self):
        for stamp in ("2026-09-11T19:00:00", "2026-09-11T19:05:00Z"):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                rates.normalise_response(payload(start=stamp))

    def test_partial_response_rejected(self):
        p = payload()
        p["errors"] = [{"message": "partial"}]
        with self.assertRaises(ValueError):
            rates.normalise_response(p)

    def test_missing_channel_rejected(self):
        p = payload()
        p["data"]["sitePricing"]["meterWindows"].pop()
        with self.assertRaises(ValueError):
            rates.normalise_response(p)

    def test_conflicting_duplicate_rejected(self):
        p = payload()
        p["data"]["sitePricing"]["meterWindows"][0]["forecastPeriods"] = [
            {"start": "2026-09-11T19:00:00Z", "kwhPriceInCents": 31}
        ]
        with self.assertRaises(ValueError):
            rates.normalise_response(p)


if __name__ == "__main__":
    unittest.main()
