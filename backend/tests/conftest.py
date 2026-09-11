"""Shared fixtures for tests that exercise the real pipeline: Celery
eager mode, and a clean Redis between tests.

Redis state — the dedupe window (apps.moderation.engine.dedupe) and
review claim locks (apps.moderation.claims) — isn't rolled back the way
Postgres is by pytest-django's transactional tests. Postgres sequences
*do* reset on rollback, so a posting's primary key is commonly reused
across tests in the same session; without flushing Redis, a stale claim
or dedupe fingerprint keyed by an earlier test's posting id can leak into
a later test that happens to reuse that same id. Flushing the whole
Redis database used for this (db 1 in docker-compose, separate from
whatever a real deployment's broker uses) is simpler and safer than
tracking every key an engine stage might have written.
"""

import pytest

from apps.moderation.engine.dedupe import get_redis_client


@pytest.fixture(autouse=True)
def _eager_celery(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture(autouse=True)
def _clean_redis():
    client = get_redis_client()
    client.flushdb()
    yield
    client.flushdb()


# _active_policy is NOT global: apps/policies' own tests manage Policy rows
# directly (including asserting on `version` numbering), and pre-seeding one
# here would collide with those. It's defined per-file instead, only in the
# test modules that actually run the moderation pipeline and need an active
# policy to exist (test_moderation_pipeline.py, test_postings_api.py,
# test_moderation_api.py).
