# Release checks — 0.1.0b1

This is a locally prepared beta candidate. Public repository creation, a GitHub release, a HACS catalogue submission and Reddit messages require the owner's review.

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

The GitHub workflows and HACS repository-access validation remain pending publication approval. Local hassfest has passed; a valid layout does not imply HACS default-catalogue acceptance.

## Publication after review

1. Review source, documentation, icon and test evidence.
2. Create the proposed public GitHub repository `markgraham924/ha-eon-optimise-prices`.
3. Add a short read-only-price description and topics `home-assistant`, `hacs`, `eon-next`, `optimise`.
4. Remove the README's unpublished-candidate notice.
5. Run GitHub validation and resolve any failures before promoting the beta.
6. Publish tag/release `v0.1.0b1` with the verified release archive.
7. Verify unauthenticated access to the repository/release and HACS custom-repository installation.
8. Send the reviewed installation link only after the owner approves the reply.

None of those publication steps has been performed by preparing this candidate.
