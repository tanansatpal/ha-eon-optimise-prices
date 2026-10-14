# Release checks — 0.1.0b1

The owner reviewed the candidate and approved public repository and beta-release publication on 14 October 2026. Reddit messages and a HACS default-catalogue submission are not part of that publication approval.

## Scope

- One integration directory: `custom_components/eon_next_optimise`.
- One device per configured account; import price, export price and last-update sensors.
- Only the account's own API periods. No experimental forecast extensions, supplier insights, private price history, personal booster dates or local HTTP services.
- No battery, EV or SmartShift control code.
- Separate domain from the working private installation.
- Included original PNG icon, English setup/error text, MIT licence and installation documentation.

## Validation

Verified on 14 October 2026:

- 28 automated tests and 7 subtests passed using Linux and Home Assistant 2026.10.1.
- Ruff checks and formatting checks passed.
- Official Home Assistant hassfest container validated one integration, with zero invalid integrations. Validator image digest: `sha256:4b1adfb1e0a37710af0390708eb8000230b80b2193ccffbeed0a901fa9765181`.
- A fresh email/password login succeeded without supplying an existing refresh token. Each direction returned 97 API periods, including 48 upcoming periods; actual prices and credentials are omitted from the evidence.
- The existing isolated test Home Assistant created one device with three entities. Its integration picture displayed correctly. See [demonstration screenshot](device-demo.png).
- All 12 installed component files matched the candidate byte for byte. The preview transport uses synthetic data and is a separate, private lab fixture; it is not included in the release.
- No production integration, battery control or SmartShift configuration was changed.
- Follow-up: the synthetic lab account was replaced with the owner's real login through Home Assistant's normal setup flow. Production HA, test HA and a fresh direct API login agreed on both current prices; all 97 overlapping periods matched in each direction. The test instance uses a private TLS pass-through restricted to the supplier's two hostnames, because its Docker network is isolated. Neither this gateway nor real account data is included in the release. The public screenshot above remains a demonstration screenshot.

The test Home Assistant is separate from the production installation. Another customer's account, interactive MFA and Home Assistant versions other than 2026.10.1 have not been verified.

The fresh-password check uses owner-authorised credentials in memory, against the same production app API. Credentials and actual prices are omitted from the evidence. UI/device screenshots use labelled demonstration data.

Local hassfest has passed. GitHub workflow results are available from the repository's Actions tab. A valid custom-repository layout does not imply HACS default-catalogue acceptance.

## Distribution

Repository: `markgraham924/ha-eon-optimise-prices`. Beta tag: `v0.1.0b1`.

Use the HACS custom-repository instructions in the README, or copy the component folder from the release ZIP. HACS default-catalogue inclusion has not been requested. Real account data, credentials and private lab infrastructure are excluded from source and release assets.
