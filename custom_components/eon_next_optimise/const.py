"""Constants for the read-only Optimise price feed."""

from datetime import timedelta

DOMAIN = "eon_next_optimise"
NAME = "E.ON Next Optimise Prices"
UPDATE_INTERVAL = timedelta(minutes=5)
MAX_AGE = timedelta(minutes=15)
GRAPHQL_URL = "https://backend.production.eon-next.amber-international.com.au/graphql"
CLIENT_ID = "5tjc4igm29bcmsal7eridtuii6"
USER_POOL_ID = "eu-west-2_qbjjnayWT"
REGION = "eu-west-2"
CONF_REFRESH_TOKEN = "refresh_token"
PRICE_QUERY = """query OptimisePrices {
  sitePricing {
    meterWindows {
      usageType
      currentPeriod { start kwhPriceInCents estimate }
      previousPeriods { start kwhPriceInCents estimate }
      forecastPeriods { start kwhPriceInCents estimate }
    }
  }
}"""
