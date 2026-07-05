# Provider System

Last updated: 2026-07-05

## Provider Registry And Tiers

`src/core/provider_registry.py` is the single source of truth for which
providers exist, what each is good at, and which search tier it serves. Every
provider declares `CAPABILITIES` (a `ProviderCapabilities`): `airline`,
`region`, `cost`, `freshness`, `bookable`, `has_calendar`, `has_one_way`, and
`tiers`. The search engine routes work by capability, not provider-name strings.

Two tiers express the discovery/verification split:

| Tier | Job | Freshness | Providers |
|---|---|---|---|
| `DISCOVERY` | Broad, cheap "which cities/dates are worth looking at?" | May be cached or approximate | Ryanair, Ryanair Calendar, Google, Google Multi-Mode, Travelpayouts when configured |
| `VERIFICATION` | Narrow, exact-date "is THIS deal real right now?" | Live where possible, clearly labelled when cached/approximate | Ryanair, Google, Google Multi-Mode, Travelpayouts when configured, Amadeus when configured, Duffel when enabled |

Adding a source is one `ProviderSpec` in the registry. Build helpers:
`build_verification_providers()` (today's exact-date set),
`build_discovery_providers()` (free discovery set), `build_guest_providers()`
(free-only), and `build_owner_providers()` (may include Duffel).

Metered providers gate themselves via `pre_call_ok()` / `record_call()`. Duffel
reserves a daily-budget slot before a paid request is issued, and the counter is
lock-protected so concurrent searches cannot overspend the configured cap.

## Active Providers

| Provider class | Source | Cost | Tiers | Used for |
|---|---|---|---|---|
| `RyanairProvider` | Ryanair public JSON endpoints | Free | Both | Direct LCC prices, one-way legs, exact-date round trips |
| `RyanairCalendarProvider` | Ryanair `cheapestPerDay` calendar | Free | Discovery | Whole-month fare surface in about one call per route; approximate |
| `GoogleScraperProvider` | `fast-flights` Google Flights Protobuf | Free | Both | Broad airline coverage; requests force EUR and are timeout-bounded |
| `MultiGoogleScraperProvider` | Google Flights direct/all modes via `fast-flights` | Free | Both | Wider search coverage and backup signal, with cache/rate limiting |
| `TravelpayoutsProvider` | Travelpayouts / Aviasales Data API | Free keyed | Both | Cached fares over a real API; useful on server IPs where scraping is blocked |
| `AmadeusProvider` | Amadeus Self-Service API | Free/test keyed | Verification | Independent GDS offers when `AMADEUS_CLIENT_ID` and secret are configured |
| `DuffelProvider` | Duffel GDS API | Paid | Verification | Independent bookable GDS offers, budget-gated |

## Direct-Airline Coverage Reality

Direct airline readers were probed for key-free availability. Only Ryanair's
public API answers cleanly (calendar, route graph, active-airports list). The
rest are walled and would need official APIs, keys, or scraping infrastructure
that is out of scope:

| Carrier / source | Result |
|---|---|
| Ryanair | Open - calendar, routes, airports all return JSON |
| Wizz Air | 403 / Cloudflare |
| easyJet | 403 Access Denied / Akamai |
| Vueling | Walled or unreliable direct host |
| Transavia | Requires official API access |
| Kiwi | Old skypicker endpoint deprecated; Tequila needs a key |

Consequence: most non-Ryanair fares arrive through Google, Travelpayouts,
Amadeus, or Duffel rather than direct airline scrapers.

## Duffel Safety

Duffel is paid, so the app protects the owner's wallet:

- Guest searches use `build_guest_providers()` and never include paid providers.
- Owner searches may use Duffel through `build_providers()` / `build_owner_providers()`.
- Duffel is only added when `DUFFEL_TOKEN` is set and `DUFFEL_DAILY_BUDGET` remains.
- Budget helpers track local-day usage: `duffel_budget_remaining`,
  `duffel_budget_used_today`, `record_duffel_call`, and `duffel_budget_ok`.

Set `DUFFEL_DAILY_BUDGET=0` to disable Duffel.

## Health And Reliability

All providers inherit from `FlightProvider`, which supplies:

- failure tracking,
- circuit breaker behavior,
- health status/reason fields,
- retry/backoff wrapper hooks.

Provider instances cache health checks for 15 minutes. Google scraper calls are
bounded so a stalled Google connection does not block a search forever, and a
malformed Google fare now skips only that fare rather than discarding the whole
route.

## Provider Consensus

The ranking system prefers confirmed prices. Quotes are deduplicated by airline
and near-identical price before being counted, so Google relaying the same fare
is not treated as an independent second source.

Confidence labels:

| Label | Meaning |
|---|---|
| `HIGH` | Multiple independent sources agree closely |
| `MEDIUM` | Multiple sources exist but disagree more |
| `SINGLE_SOURCE` | One source only; verify before booking |
| `LOW` | Weak/stale/fallback signal |

## Luggage Costing

Default search mode is `carryon_10kg`.

Known examples:

| Airline | Code | 10 kg carry-on round trip |
|---|---|---|
| Ryanair | FR | EUR 40 |
| Wizz Air | W6 | EUR 36 |
| easyJet | U2 | EUR 14 |
| Norwegian | DY | EUR 22 |
| airBaltic | BT | EUR 24 |
| Vueling | VY | EUR 22 |
| Eurowings | EW | EUR 16 |
| Lufthansa / Air France / KLM / BA | LH / AF / KL / BA | EUR 0 assumed included |

The bot also exposes `none` and `checked_23kg` luggage modes.

## Transfer Costing

`cost_utils.py` contains transfer costs for many airports. Search requests can
include or exclude transfers. Origin transfers are counted per participant and
destination transfers are multiplied by the number of travellers, because every
traveller needs destination airport-city transport.

## Removed Or Inactive Providers

Several providers from earlier iterations are no longer active: SerpApi,
RapidAPI/Kiwi, Aviationstack, SearchAPI, and dead direct-airline scrapers.
Travelpayouts and Amadeus are active only when their keys are configured. Duffel
is active only for owner/paid searches when token and budget allow it.
