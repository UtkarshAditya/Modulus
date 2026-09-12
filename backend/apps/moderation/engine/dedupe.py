"""Near-duplicate detection (Phase 4): a SimHash fingerprint of the
normalized text, compared against a Redis-held rolling window of recent
postings plus the submitter's own history. A close match (small Hamming
distance) flags `SPAM_DUPLICATE`.

Unlike rules and the classifier, this stage has side effects — it writes
its own fingerprint into Redis as part of checking it, so a posting is
compared against everything *before* it, and future postings are compared
against this one. `check_and_record` does both in one call because
splitting "check" from "record" would let a caller check without ever
recording, silently defeating the window.
"""

from __future__ import annotations

import hashlib
import re
import time

import redis
from django.conf import settings

from apps.moderation.engine.rules.base import Category, Evidence, RuleHit, Severity

SIMHASH_BITS = 64
# The textbook SimHash threshold (~3 of 64 bits) is tuned for full web
# documents with hundreds of tokens; job postings are much shorter, so the
# per-bit vote is noisier. Empirically, on realistic posting-length text
# (a few sentences), a near-duplicate (a repost with a location appended,
# or two words swapped) lands around 4-6 bits different, while unrelated
# postings land around 20+. 10 sits with margin below the unrelated band
# without being so tight it misses real reposts.
HAMMING_THRESHOLD = 10
GLOBAL_WINDOW_SIZE = 500
SUBMITTER_HISTORY_SIZE = 20
SUBMITTER_HISTORY_TTL_SECONDS = 60 * 60 * 24 * 90  # 90 days

GLOBAL_KEY = "dedupe:simhash:global"


def _submitter_key(submitter_id: int) -> str:
    return f"dedupe:simhash:user:{submitter_id}"


def _token_hash(token: str) -> int:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def compute_simhash(text: str) -> int:
    """A 64-bit fingerprint where similar documents produce fingerprints
    differing in only a few bits, and dissimilar documents differ in
    roughly half — the property that makes Hamming distance a usable
    similarity measure here.
    """
    tokens = re.findall(r"[a-z0-9]{3,}", text.lower())
    if not tokens:
        return 0
    bit_totals = [0] * SIMHASH_BITS
    for token in tokens:
        token_hash = _token_hash(token)
        for bit in range(SIMHASH_BITS):
            bit_totals[bit] += 1 if (token_hash >> bit) & 1 else -1
    fingerprint = 0
    for bit in range(SIMHASH_BITS):
        if bit_totals[bit] > 0:
            fingerprint |= 1 << bit
    return fingerprint


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def _closest_match(
    client: redis.Redis, key: str, fingerprint: int, exclude_posting_id: int
) -> tuple[int, int] | None:
    """Returns (matched_posting_id, hamming_distance) for the closest
    match under the threshold, or None.
    """
    best: tuple[int, int] | None = None
    for member in client.zrange(key, 0, -1):
        fp_str, _, pid_str = member.partition(":")
        posting_id = int(pid_str)
        if posting_id == exclude_posting_id:
            continue
        distance = hamming_distance(fingerprint, int(fp_str))
        if distance <= HAMMING_THRESHOLD and (best is None or distance < best[1]):
            best = (posting_id, distance)
    return best


def check_and_record(
    text: str, posting_id: int, submitter_id: int, client: redis.Redis | None = None
) -> list[RuleHit]:
    """Check `text` against the rolling window, record its fingerprint,
    and return a `SPAM_DUPLICATE` hit (as a one-item list, empty if no
    match) — list-returning to match the shape every other engine stage
    returns, so `tasks.py` can just concatenate all of them.
    """
    client = client or get_redis_client()
    fingerprint = compute_simhash(text)
    now = time.time()
    member = f"{fingerprint}:{posting_id}"

    global_match = _closest_match(client, GLOBAL_KEY, fingerprint, posting_id)
    client.zadd(GLOBAL_KEY, {member: now})
    client.zremrangebyrank(GLOBAL_KEY, 0, -(GLOBAL_WINDOW_SIZE + 1))

    submitter_key = _submitter_key(submitter_id)
    submitter_match = _closest_match(client, submitter_key, fingerprint, posting_id)
    client.zadd(submitter_key, {member: now})
    client.zremrangebyrank(submitter_key, 0, -(SUBMITTER_HISTORY_SIZE + 1))
    client.expire(submitter_key, SUBMITTER_HISTORY_TTL_SECONDS)

    match = None
    from_own_history = False
    if submitter_match is not None:
        match = submitter_match
        from_own_history = True
    if global_match is not None and (match is None or global_match[1] < match[1]):
        match = global_match
        from_own_history = False

    if match is None:
        return []

    matched_posting_id, distance = match
    scope = "this submitter's own recent postings" if from_own_history else "recent postings"
    return [
        RuleHit(
            rule_id="dedupe.simhash",
            category=Category.SPAM_DUPLICATE,
            severity=Severity.MEDIUM,
            source="DEDUPE",
            confidence=round(1 - (distance / SIMHASH_BITS), 4),
            evidence=[
                Evidence(
                    0,
                    0,
                    "",
                    note=f"near-duplicate of posting #{matched_posting_id} ({scope}), "
                    f"{distance} bits different",
                )
            ],
            reason=f"This posting is nearly identical to a recent posting (#{matched_posting_id}).",
        )
    ]
