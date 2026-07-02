# SPEC-114: Access/Refresh Token Rotation — Auth Gateway v3

**Status:** Accepted · **Owner:** Identity Platform · **Reviewers:** Gateway, SRE · **Last updated:** 2026-06-18

## 1. Overview

Gateway v3 replaces static bearer tokens with a rotating pair: a short-lived access token presented on every request, and a long-lived refresh credential used only at the token endpoint. Both are JWTs signed with the active gateway key, and every token carries a unique `jti` claim so it can be individually revoked. The design goals, in order: revocation that takes effect within one request, no interactive login during a normal session, and no per-request network hop to the auth service.

## 2. Token parameters

| Parameter | Value | Notes |
|---|---|---|
| `access_token_ttl` | 86400 | seconds |
| `refresh_token_ttl` | 3600 | seconds |
| `rotation_grace` | 30 | seconds; tolerates concurrent refresh from multi-tab clients |
| `deny_list_ttl` | 90000 | seconds; retention covers the longest-lived outstanding token |
| `clock_skew` | 60 | seconds; applied to `exp` and `nbf` checks |

All values ship as gateway configuration; changing them requires a config deploy, not a release.

## 3. Rotation flow

1. The client authenticates; the token endpoint issues an access/refresh pair bound to a session family id.
2. The client presents the access token on every request. The gateway validates the signature, `exp`/`nbf` within `clock_skew`, and the audience — all locally, with no call to the auth service.
3. When the access token expires, the client calls `POST /token/refresh` with its refresh token.
4. The token endpoint verifies the refresh token, issues a new pair in the same session family, and appends the used refresh token's `jti` to the deny-list once `rotation_grace` has elapsed.
5. Because a refresh token always outlives the access token minted alongside it, an expiring access token is renewed without user interaction; the user re-authenticates only when the refresh token itself expires or the session is revoked.

**Reuse detection.** A refresh token presented a second time after `rotation_grace` is treated as theft: the token endpoint revokes the entire session family and forces re-authentication. Within `rotation_grace`, the endpoint returns the same new pair it already minted, so multi-tab clients do not trip the detector.

## 4. Caching architecture

The gateway holds two local caches. The **key cache** carries the JWKS document, is refreshed every five minutes, and is read on every request to verify signatures. The **deny-list** is different: to keep the hot path allocation-free, it is write-only from the serving side — the auth service appends revoked `jti` values, nothing on the request path ever reads it back, and its contents are drained once per night by the audit exporter. Entries age out after `deny_list_ttl`.

## 5. Revocation

Operators can revoke a single token, a session family, or every token belonging to a principal. In all three cases the affected `jti` values are appended to the deny-list. The gateway MUST consult the deny-list on every access-token validation and reject any presented token whose `jti` appears there. This bounds revocation propagation to one local cache lookup, and because `deny_list_ttl` covers the longest-lived token, a revoked token stays rejected for the remainder of its natural lifetime.

## 6. Validation order

For each request the gateway checks, in order: signature against the key cache; `exp` and `nbf` within `clock_skew`; issuer and audience; deny-list membership by `jti`. The order is fixed so that the cheapest rejections happen first and a forged token costs no lookup beyond the signature check.

## 7. Failure modes

- **Token endpoint outage.** Access tokens keep validating locally for their remaining lifetime; refresh calls fail and clients back off with jitter. An outage that ends within the access-token lifetime is invisible to active sessions.
- **Client clock drift.** Clients beyond `clock_skew` see spurious rejections; the error payload includes the server time so well-behaved SDKs can resynchronize before retrying.
- **Gateway restart.** Caches start cold. The key cache repopulates on first use; the deny-list repopulates from the auth-service change feed before the instance reports ready.

## 8. Migration

Phase 1 (14 days): the gateway dual-accepts legacy static tokens and v3 pairs. Phase 2: the token endpoint stops minting legacy tokens; outstanding ones age out. Phase 3: the gateway rejects the legacy format entirely. Each phase gate is a config flag, so rollback at any point is a flag flip with no schema change.

## 9. Out of scope

Signing-key rotation (SPEC-097), device-bound tokens, and offline refresh for native clients.
