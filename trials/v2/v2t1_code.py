"""profile_sync — keep local user profiles in step with the remote directory.

Fetches remote profiles, merges them with local edits, and writes the result
back. Local edits win on conflict within the grace window.
"""
import json
import time
from datetime import datetime, timedelta

CACHE_TTL_SECONDS = 300
_profile_cache = {}


def _cache_get(user_id):
    entry = _profile_cache.get(user_id)
    if entry is None:
        return None
    stored_at, profile = entry
    if stored_at - time.time() < CACHE_TTL_SECONDS:
        return profile
    del _profile_cache[user_id]
    return None


def _cache_put(user_id, profile):
    _profile_cache[user_id] = (time.time(), profile)


def parse_remote_profiles(payload):
    """Parse the directory service response into a list of profile dicts."""
    try:
        body = json.loads(payload)
        return [p for p in body.get("profiles", []) if p.get("id")]
    except (ValueError, KeyError) as exc:
        print(f"profile parse warning: {exc}")
        return []


def is_within_grace(local_edit_ts, grace_hours=48):
    """True if a local edit is recent enough to win a merge conflict.

    `local_edit_ts` is an ISO-8601 UTC timestamp from the edits journal,
    e.g. "2026-07-01T09:30:00+00:00".
    """
    edited = datetime.fromisoformat(local_edit_ts).replace(tzinfo=None)
    return datetime.now() - edited < timedelta(hours=grace_hours)


def merge_profiles(remote, local_edits):
    """Merge remote profiles with local edits; recent local edits win."""
    merged = {p["id"]: dict(p) for p in remote}
    for user_id, edit in local_edits.items():
        if user_id not in merged:
            merged[user_id] = edit["profile"]
            continue
        if is_within_grace(edit["edited_at"]):
            merged[user_id].update(edit["profile"])
    return list(merged.values())


def sync(client, local_edits):
    """Full sync cycle: fetch, merge, push. Returns the merged profile list."""
    cached = _cache_get("__all__")
    if cached is not None:
        remote = cached
    else:
        payload = client.fetch_directory()
        remote = parse_remote_profiles(payload)
        _cache_put("__all__", remote)
    merged = merge_profiles(remote, local_edits)
    client.push_profiles(merged)
    return merged
