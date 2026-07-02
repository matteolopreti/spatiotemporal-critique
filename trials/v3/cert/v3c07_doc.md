# Rostra API: migrating from v2 to v3

Rostra API v3 reached general availability on 2026-06-15. v3 renames several
fields for consistency, replaces page-number pagination with cursors, and
adopts a structured error format. This guide covers every breaking change and
the timeline for retiring v2.

## Deprecation timeline

| Date | Milestone |
|------|-----------|
| 2026-06-15 | v3 general availability. v2 continues to work unchanged. |
| 2026-09-15 | Three months after GA: every v2 response starts carrying `Sunset: Wed, 31 Mar 2027 00:00:00 GMT` and `Link: <https://developers.rostra.example/migrate-v3>; rel="deprecation"` headers. |
| 2027-01-15 | v2 write endpoints (POST, PATCH, DELETE) return `410 Gone`. v2 reads keep working. |
| 2027-03-31 | v2 retired. All v2 endpoints return `410 Gone`. |

That gives a migration window of just over nine months from GA to retirement.
The sandbox environment (`https://sandbox.rostra.example`) serves both
versions until retirement, so you can test v3 against production-shaped data
at any point.

## What is unchanged

Authentication is identical: the same bearer tokens work on both versions.
Resource IDs and their values are unchanged — a shift that is `sh_8h2k4` in v2
is `sh_8h2k4` in v3, and a member previously referenced as `usr_9f3k1` keeps
that exact ID. Only field *names* and *formats* change.

Base URL: `https://api.rostra.example/v2` becomes
`https://api.rostra.example/v3`.

## Renamed and reformatted fields

On the shift resource:

| v2 field | v3 field | Format change |
|----------|----------|---------------|
| `user_id` | `member_id` | none — same ID values |
| `type` | `shift_type` | none |
| `start` | `starts_at` | Unix seconds → RFC 3339 UTC string |
| `end` | `ends_at` | Unix seconds → RFC 3339 UTC string |
| `created` | `created_at` | Unix seconds → RFC 3339 UTC string |

The same renames apply to query parameters: `GET /v2/shifts?user_id=usr_9f3k1`
becomes `GET /v3/shifts?member_id=usr_9f3k1`.

A v2 shift:

```json
{
  "id": "sh_8h2k4",
  "user_id": "usr_9f3k1",
  "type": "closing",
  "start": 1783328400,
  "end": 1783357200,
  "created": 1782655929
}
```

The same shift in v3 — an eight-hour closing shift on 2026-07-06:

```json
{
  "id": "sh_8h2k4",
  "member_id": "usr_9f3k1",
  "shift_type": "closing",
  "starts_at": "2026-07-06T09:00:00Z",
  "ends_at": "2026-07-06T17:00:00Z",
  "created_at": "2026-06-28T14:12:09Z"
}
```

## Pagination

v2 uses page numbers: `page` and `per_page` (default 25, maximum 100), with
the response body as a bare JSON array. v3 uses cursors: `limit` (default 50,
maximum 200) and `cursor`, with results wrapped in an envelope:

```json
{
  "data": [ ... ],
  "next_cursor": "c_k29dm1"
}
```

`next_cursor` is `null` on the final page. Cursors are opaque; do not parse
them, and do not store them beyond a single traversal.

Before, in v2:

```python
page = 1
while True:
    resp = requests.get(
        f"{BASE}/v2/shifts",
        params={"page": page, "per_page": 100},
        headers=headers,
    )
    shifts = resp.json()
    if not shifts:
        break
    for s in shifts:
        print(s["user_id"], s["start"])
    page += 1
```

After, in v3:

```python
params = {"limit": 200}
while True:
    resp = requests.get(f"{BASE}/v3/shifts", params=params, headers=headers)
    body = resp.json()
    for s in body["data"]:
        print(s["member_id"], s["starts_at"])
    if body["next_cursor"] is None:
        break
    params["cursor"] = body["next_cursor"]
```

Equivalent first-page requests with curl:

```bash
# v2
curl -H "Authorization: Bearer $ROSTRA_TOKEN" \
  "https://api.rostra.example/v2/shifts?page=1&per_page=100"

# v3
curl -H "Authorization: Bearer $ROSTRA_TOKEN" \
  "https://api.rostra.example/v3/shifts?limit=200"
```

## Errors

v2 returned a flat string:

```json
{ "error": "shift not found" }
```

v3 returns a structured object with a stable machine-readable code:

```json
{
  "error": {
    "code": "not_found",
    "message": "Shift sh_8h2k4 does not exist."
  }
}
```

Match on `error.code`, not on `error.message` — messages may be reworded
without notice, codes will not. The v3 codes are `not_found`,
`validation_failed`, `rate_limited`, and `unauthorized`, and HTTP status codes
carry the same meaning as in v2.

## Rate limits

v3 doubles the per-token limit: 60 requests/minute in v2 becomes 120
requests/minute in v3. Both versions return `X-RateLimit-Limit`,
`X-RateLimit-Remaining`, and `X-RateLimit-Reset` (Unix seconds) on every
response, and `rate_limited` errors arrive with HTTP 429. Since the limits are
tracked per version, running v2 and v3 side by side during your migration does
not eat into a shared quota.

## Recommended migration order

1. Point a staging integration at `https://sandbox.rostra.example/v3` and run
   your test suite against it.
2. Migrate reads first: rename fields, switch timestamp parsing from epoch
   seconds to RFC 3339, and adopt cursor pagination. Reads are safe to migrate
   incrementally because v2 and v3 serve the same underlying data.
3. Migrate writes before 2027-01-15, when v2 write endpoints return 410.
4. Remove all remaining v2 calls before 2027-03-31, when v2 is retired.
5. Watch for the `Sunset` header in any client logs after 2026-09-15 — if you
   see it, that client still has unmigrated v2 calls.

## Checklist

- [ ] `user_id` → `member_id` (body fields and query parameters)
- [ ] `type` → `shift_type`
- [ ] `start` / `end` / `created` → `starts_at` / `ends_at` / `created_at`,
      parsed as RFC 3339
- [ ] Page-number pagination → cursor pagination with the `data` envelope
- [ ] Error handling matches on `error.code`
- [ ] All writes on v3 before 2027-01-15; all reads before 2027-03-31

Questions go to `api-support@rostra.example`; include the `X-Request-Id`
response header from any failing call.
