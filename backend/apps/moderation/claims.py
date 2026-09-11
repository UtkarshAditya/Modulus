"""Redis-backed claim locks (Phase 6): what actually stops two moderators
from opening the same case at once. `ReviewClaim` rows are the durable
record for the queue UI and audit trail; this module is the enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import redis
from django.conf import settings
from django.utils import timezone

from apps.moderation.models import ReviewClaim

CLAIM_TTL_SECONDS = 10 * 60
_KEY_PREFIX = "moderation:claim:posting"

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def _key(posting_id: int) -> str:
    return f"{_KEY_PREFIX}:{posting_id}"


@dataclass(frozen=True)
class ClaimResult:
    success: bool
    expires_at: object | None = None
    held_by: int | None = None


def acquire_claim(posting_id: int, moderator) -> ClaimResult:
    """Claims the posting for `moderator`. Re-claiming your own already-held
    claim just renews its TTL — this is what lets the console's "claim
    auto-renews while the tab is active" behavior (Phase 6 frontend) work
    as repeated calls to the same endpoint rather than a separate one.
    """
    client = get_redis_client()
    key = _key(posting_id)
    expires_at = timezone.now() + timedelta(seconds=CLAIM_TTL_SECONDS)

    held_by = client.get(key)
    if held_by is not None and int(held_by) == moderator.id:
        client.expire(key, CLAIM_TTL_SECONDS)
        return ClaimResult(success=True, expires_at=expires_at, held_by=moderator.id)

    acquired = client.set(key, str(moderator.id), nx=True, ex=CLAIM_TTL_SECONDS)
    if not acquired:
        current_holder = client.get(key)
        return ClaimResult(success=False, held_by=int(current_holder) if current_holder else None)

    ReviewClaim.objects.create(moderator=moderator, posting_id=posting_id, expires_at=expires_at)
    return ClaimResult(success=True, expires_at=expires_at, held_by=moderator.id)


def release_claim(posting_id: int, moderator) -> bool:
    """Returns False if someone else holds the claim (and it isn't
    released). Releasing a claim nobody holds is a no-op success — that
    can legitimately happen if the TTL already expired.
    """
    client = get_redis_client()
    key = _key(posting_id)
    held_by = client.get(key)

    if held_by is not None and int(held_by) != moderator.id and not moderator.is_superuser:
        return False

    client.delete(key)
    ReviewClaim.objects.filter(
        posting_id=posting_id, moderator=moderator, released_at__isnull=True
    ).update(released_at=timezone.now())
    return True


def get_claim_holder(posting_id: int) -> int | None:
    held_by = get_redis_client().get(_key(posting_id))
    return int(held_by) if held_by is not None else None
