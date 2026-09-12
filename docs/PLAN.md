# Content Moderation Pipeline — Implementation Plan (v1)

## Context

`D:\Content_Pipeline` is an empty git repository. We are building, from scratch, a content
moderation pipeline where users submit content, an automated engine flags it with written
reasoning, high-confidence cases are decided automatically, and everything ambiguous is routed
to a human moderator who makes the final call.

The problem this addresses: purely manual moderation does not scale and is inconsistent between
reviewers, while purely automated moderation produces false positives that silently harm
legitimate users. The pipeline splits the difference — automation absorbs the unambiguous
volume and, critically, hands the human a *pre-reasoned* case file rather than a raw blob of
text, so the human spends their time deciding instead of reading.

Intended outcome for v1: a running end-to-end system where an employer posts a job, the posting
is analysed asynchronously within seconds, and it is either auto-approved, auto-rejected, or
placed in a moderator queue with highlighted evidence and per-category explanations.

---

## Use cases this pipeline serves

The architecture below is use-case agnostic. Swapping the domain means swapping the submission
model, the rule pack, and the trained classifier — not the pipeline. Candidates surveyed:

| Use case | What gets flagged | What a human decides |
| --- | --- | --- |
| **Job board postings (chosen for v1)** | Advance-fee scams, MLM recruitment, off-platform redirects, upfront document/bank requests, discriminatory criteria, ghost jobs | Approve, reject with reason, or request revision from the employer |
| Marketplace listings | Prohibited or regulated goods, counterfeits, implausible pricing, contact-info leakage | Approve, reject, or delist pending seller edit |
| Community forum posts | Harassment, hate speech, self-harm, spam, doxxing | Hide, delete, warn, or ban |
| Student and scholarship essays | Likely AI generation, plagiarism signals, PII leakage, off-topic | Accept, reject, or escalate to committee |
| App and product reviews | Incentivised reviews, review-bombing rings, competitor astroturfing | Remove, keep, or flag the reviewer account |
| Financial and health advertising | Unsubstantiated claims, guaranteed-return language, missing disclosures | Approve, reject, or require a disclaimer |
| Rental and property listings | Deposit scams, discriminatory tenant criteria, duplicate listings | Approve, reject, or verify landlord |

**v1 is job board postings.** It has the strongest combination of a bounded, writable rule
taxonomy, a real grey zone that genuinely needs a human, and a compliance angle that makes the
audit trail meaningful.

---

## Decisions locked for v1

- **Domain:** job board postings.
- **Engine:** deterministic rules plus a locally trained classifier. No external inference API.
- **Scope:** the core loop only — submit, auto-analyse, auto-decide the confident cases, human
  queue for the rest, decision, audit trail, status visible to the submitter. No appeals flow,
  no analytics dashboard.

### Consequence of the no-LLM decision, and the mitigation

Reasoning quality is the thing at risk. The mitigation is to make reasoning *evidentiary*
rather than *narrative*:

- Every rule hit carries the exact character span it matched, so the UI highlights the offending
  text in place.
- The classifier is a linear model over TF-IDF features, which means per-token coefficient
  contributions are directly readable. We surface the top contributing terms per category. This
  is genuinely more faithful than a generated explanation, which is a post-hoc narration.
- Reason sentences are rendered from templates bound to rule metadata, the matched span, and the
  model's contribution — specific, not generic.

The classifier sits behind a `Classifier` protocol so a different backend can be dropped in later
without changing the pipeline. This is an extension point, not v1 work.

---

## Architecture

```
React (Vite + TS)
  ├─ Submitter portal  ── POST /api/postings ──┐
  └─ Moderator console ── queue, claim, decide ┤
                                               ▼
                                    Django + DRF (gunicorn)
                                               │ enqueue
                                               ▼
                                        Redis (broker)
                                               ▼
                                    Celery worker(s) + beat
                                               │
              ┌────────────────────────────────┴─────────────────────────┐
              │  normalize → rules → classifier → dedupe → fuse → route   │
              └────────────────────────────────┬─────────────────────────┘
                                               ▼
                              PostgreSQL (postings, runs, flags,
                                          decisions, audit, policies)
```

Redis carries three jobs: Celery broker and result backend, the moderator claim locks, and the
near-duplicate fingerprint window.

---

## Repository layout

```
backend/
  config/
    settings/{base,dev,prod}.py
    celery.py, urls.py, asgi.py, wsgi.py
  apps/
    accounts/      # custom user, roles, permissions
    postings/      # JobPosting, submitter-facing API
    moderation/    # runs, flags, decisions, queue, Celery tasks
      engine/
        normalize.py     # unicode fold, de-obfuscate, strip markup, span map
        rules/
          base.py        # Rule protocol, RuleHit dataclass
          packs/jobs.py  # the job-board rule pack
        classifier.py    # Classifier protocol + sklearn implementation
        dedupe.py        # SimHash over normalized text, Redis window
        fusion.py        # score aggregation + routing thresholds
        reasons.py       # renders RuleHit/model output into reason text
      tasks.py
    policies/      # versioned thresholds + rule enable/disable + weights
    audit/         # append-only event log
  ml/
    train.py             # training + held-out eval + champion/challenger gate
    data/seed.jsonl      # labelled seed corpus
    artifacts/           # versioned joblib bundles (gitignored, checksummed)
  tests/
frontend/
  src/{api,components,pages,hooks,types}/
infra/
  docker-compose.yml, Dockerfile.backend, Dockerfile.frontend
```

---

## Data model

`accounts.User` — Django custom user with a `role` field: `EMPLOYER`, `MODERATOR`, `ADMIN`.
Custom user from day one; retrofitting one later is painful.

`postings.JobPosting`
- Submitter FK, company name, title, description, location, employment type
- `salary_min`, `salary_max`, `currency`, `salary_disclosed`
- `apply_url`, `contact_email`
- `status`: `DRAFT`, `PENDING`, `AUTO_APPROVED`, `AUTO_REJECTED`, `IN_REVIEW`, `APPROVED`,
  `REJECTED`, `CHANGES_REQUESTED`
- `content_hash`, `version` (edits create a new version and re-trigger analysis)
- `submitted_at`, `decided_at`

`moderation.ModerationRun` — one pipeline execution over one posting version.
- Posting FK, `policy_version`, `model_version`, `engine_version`
- `risk_score` (0–1), `routing` (`AUTO_APPROVE` / `AUTO_REJECT` / `HUMAN_REVIEW`)
- `started_at`, `finished_at`, `duration_ms`, `status`, `error`
- Recording all three versions is what makes any past decision reproducible.

`moderation.Flag` — one per triggered category, belongs to a run.
- `category` (see taxonomy), `severity` (`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`)
- `source` (`RULE` / `MODEL` / `DEDUPE`), `confidence`
- `rule_id` (nullable), `evidence` JSON: list of `{start, end, text, note}` spans
- `reason` — the rendered explanation sentence
- `contributing_terms` JSON for model-sourced flags
- `is_false_positive` — set by a moderator, feeds the training set

`moderation.ReviewClaim` — moderator FK, posting FK, `expires_at`. Backed by a Redis lock so two
moderators never open the same case.

`moderation.Decision` — moderator FK, run FK, `action`, `reason_code`, `notes`, `created_at`.
Actions: `APPROVE`, `REJECT`, `REQUEST_CHANGES`, `ESCALATE`.

`policies.Policy` — versioned, one row active at a time.
- `thresholds` JSON: `auto_approve_below`, `auto_reject_above`, per-category overrides
- `rule_config` JSON: enable/disable and weight per rule id
- Editable by an admin without a deploy. Never edited in place — a change creates a new version.

`audit.AuditEvent` — append-only. `actor`, `action`, `object_type`, `object_id`, `before`,
`after`, `ip`, `created_at`. Written by signal handlers and by the moderation tasks.

---

## Flag taxonomy (job board)

| Category | Severity | Primary detection |
| --- | --- | --- |
| `ADVANCE_FEE` — applicant asked to pay | CRITICAL | Rule (high-precision regex) |
| `PII_HARVEST` — bank/ID documents requested upfront | CRITICAL | Rule |
| `ILLEGAL_WORK` | CRITICAL | Rule + model |
| `MLM_RECRUITMENT` — commission-only, downline language | HIGH | Model + rule |
| `OFF_PLATFORM_REDIRECT` — WhatsApp/Telegram/personal email | HIGH | Rule |
| `DISCRIMINATORY` — age, gender, marital, religion, nationality | HIGH | Rule + model |
| `MISLEADING_COMP` — implausible or contradictory pay | MEDIUM | Rule (numeric checks) |
| `NO_COMP_DISCLOSURE` | LOW | Rule (field check) |
| `SPAM_DUPLICATE` | MEDIUM | SimHash |
| `GHOST_JOB` — no company, no responsibilities, boilerplate | LOW | Model |
| `KEYWORD_STUFFING` | LOW | Rule (statistical) |

Rules own the categories where a false positive is unacceptable and the pattern is literal.
The model owns the categories that are about tone and shape rather than specific words.

---

## Pipeline stages

Implemented as a Celery chain so each stage is independently retryable and timed.

1. **Normalize** — strip markup, NFKC unicode fold, collapse whitespace, de-obfuscate common
   evasions (`wh@tsapp`, `t.e.l.e.g.r.a.m`, zero-width joiners, homoglyphs). Maintains an
   offset map back to the original string so evidence spans point at the *original* text, not
   the normalized copy. This offset map is the single fiddliest piece of the engine and needs
   its own focused tests.
2. **Rules** — each rule is a class implementing `evaluate(doc) -> list[RuleHit]`. Rules are
   pure, deterministic, and individually testable. Weights and on/off come from the active
   `Policy`, not from the code.
3. **Classifier** — TF-IDF (word 1–2 grams plus char 3–5 grams to survive obfuscation) into a
   one-vs-rest calibrated logistic regression, multilabel. Returns per-category probability plus
   the top positive-coefficient terms present in the document.
4. **Dedupe** — SimHash of the normalized text, compared against a Redis-held rolling window of
   recent postings plus the submitter's own history. Hamming distance under threshold flags
   `SPAM_DUPLICATE`.
5. **Fuse** — combine rule weights and model probabilities into a single 0–1 risk score. Any
   CRITICAL rule hit short-circuits the score to the top. Per-category scores are retained, not
   just the aggregate.
6. **Route** — compare against active policy thresholds:
   - CRITICAL rule hit with an unambiguous literal match → `AUTO_REJECT`
   - score above `auto_reject_above` without a literal match → `HUMAN_REVIEW` (deliberately
     conservative; we do not auto-reject on model confidence alone in v1)
   - score below `auto_approve_below` with zero MEDIUM+ flags → `AUTO_APPROVE`
   - everything else → `HUMAN_REVIEW`
7. **Persist and notify** — write run, flags, and audit events in one transaction; update posting
   status; notify the submitter of the outcome.

Failure policy: if any stage raises, the run is marked `FAILED` and the posting is routed to
`HUMAN_REVIEW`. An engine failure must never silently approve content.

---

## API surface

Submitter:
- `POST /api/postings/` — create and submit, returns `202` with posting id
- `GET /api/postings/` — own postings with status
- `GET /api/postings/{id}/` — detail including public-safe outcome and reason summary
- `PATCH /api/postings/{id}/` — allowed in `CHANGES_REQUESTED`, creates a new version and
  re-triggers analysis

Moderator:
- `GET /api/moderation/queue/` — filter by category, severity, score band, age; sort by SLA risk
- `POST /api/moderation/queue/{id}/claim/` — acquire lock, returns TTL
- `POST /api/moderation/queue/{id}/release/`
- `GET /api/moderation/postings/{id}/` — full case file: posting, run, flags with evidence spans
- `POST /api/moderation/postings/{id}/decide/` — action, reason code, notes
- `POST /api/moderation/flags/{id}/false-positive/` — marks for the training set

Admin:
- `GET|POST /api/policies/` — list versions, create a new active version
- `GET /api/audit/` — filterable audit log

Auth: session auth for the React app with CSRF, DRF permission classes keyed on `User.role`.
Throttling on submission endpoints via DRF throttles backed by Redis.

---

## Frontend

Two areas behind one React app, split by role at the router level.

**Submitter portal** — posting form with inline validation, a list of own postings with status
chips, and a detail view. When a posting is `CHANGES_REQUESTED`, the submitter sees the
moderator's reason codes and notes, and the specific highlighted passages, then edits and
resubmits. Submitters never see raw model scores.

**Moderator console** — this is where design effort should concentrate, because moderator
throughput is the product.
- Queue table: risk score, top category, age, submitter history, claim state
- Case view, three panes: the posting rendered with evidence spans highlighted and colour-coded
  by severity; a flag list where each card shows category, severity, confidence, reason sentence,
  and the evidence that produced it; a decision panel with the four actions and reason codes
- Clicking a flag card scrolls to and emphasises its span in the posting
- Keyboard shortcuts for approve/reject/next
- Claim auto-renews while the tab is active, releases on navigate away

State and data fetching via TanStack Query. Keep the component library minimal — Tailwind plus
headless primitives; no heavyweight kit.

---

## Model training and the feedback loop

`backend/ml/train.py` loads `data/seed.jsonl` plus exported moderator decisions, trains the
multilabel classifier, evaluates on a stratified held-out split, and writes a versioned joblib
bundle containing the vectorizer, the model, the label list, and an eval report.

Promotion gate: a new model is only written to `artifacts/current` if per-category precision on
the CRITICAL and HIGH categories is at or above the incumbent's. Precision is the metric that
matters — a false positive on a legitimate job posting costs an employer real money.

Seed corpus: 300–400 labelled examples, hand-written plus synthesised against the taxonomy.
Sized against the categories that actually need a model, not all eleven — the flag taxonomy
already assigns `ADVANCE_FEE`, `PII_HARVEST`, `OFF_PLATFORM_REDIRECT`, `MISLEADING_COMP`,
`NO_COMP_DISCLOSURE`, `KEYWORD_STUFFING`, and `SPAM_DUPLICATE` to rules or dedupe alone (Phase 2
and Phase 4), so the classifier only needs to carry `ILLEGAL_WORK`, `MLM_RECRUITMENT`,
`DISCRIMINATORY`, and `GHOST_JOB` — the categories tagged "Model" or "Rule + model" in the
taxonomy. Balanced so no category is under about 40 positives, plus a comparable pool of clean
postings so the model also learns what "nothing wrong" looks like. Still real up-front work and
still the largest determinant of v1 quality for the categories it covers — just scoped to the
categories where a model is doing the primary work, not duplicating what Phase 2 already handles.

Feedback loop: every moderator decision and every false-positive mark is training signal. A
Celery beat task exports the accumulated labels nightly. Retraining stays a deliberate manual
command in v1 — automatic retraining without a human looking at the eval report is how a
moderation model quietly drifts.

---

## Build phases

**Phase 0 — Scaffold.** Docker Compose with postgres, redis, backend, worker, beat, frontend.
Split settings, custom user model, Celery app wiring, health endpoint, pre-commit with ruff and
black. Verify: `docker compose up` and a Celery ping task round-trips.

**Phase 1 — Domain.** All models, migrations, Django admin registrations, factory-boy factories,
a `seed_demo` management command. Verify: create a posting through the admin.

**Phase 2 — Rules engine.** Normalizer with the offset map, `Rule` protocol, the job rule pack,
policy-driven config. Verify: golden-corpus tests, every rule with positive, negative, and
obfuscated-evasion cases.

**Phase 3 — Classifier.** Seed corpus, training script, eval report, `Classifier` protocol and
sklearn implementation, artifact loading with a lazy singleton per worker process. Verify: eval
report meets the per-category precision floor.

**Phase 4 — Orchestration.** Celery chain, dedupe, fusion, routing, reason rendering, audit
writes, retry and failure policy. Verify: integration test submits a posting and asserts the
resulting status, flags, and reasons for each of the three routing outcomes.

**Phase 5 — Submitter API and portal.** Serializers, permissions, throttles, React form, list,
detail, resubmit flow. Verify: submit through the browser, watch status change without a reload.

**Phase 6 — Moderator API and console.** Queue, claims with Redis locks, case file endpoint,
decision endpoint, the three-pane React console with span highlighting. Verify: two browser
sessions cannot claim the same case.

**Phase 7 — Feedback and hardening.** False-positive marking, nightly label export, idempotency
on resubmission, rate limits, structured logging with a correlation id per run, Sentry hook,
Flower for Celery visibility.

---

## Verification

Automated:
- `pytest backend/tests/` — unit tests for each rule, the normalizer offset map, fusion and
  routing across threshold boundaries, and dedupe
- Integration tests with `CELERY_TASK_ALWAYS_EAGER=True` covering all three routing outcomes and
  the engine-failure path
- API contract tests per endpoint and per role, including negative authorisation cases
- `python backend/ml/train.py --evaluate-only` — asserts the precision floor
- Frontend: Vitest for the evidence-span highlighting component, which is the piece most likely
  to break subtly

Manual end-to-end, the acceptance walkthrough:
1. `docker compose up`, then `manage.py seed_demo`
2. As an employer, submit a clean posting — expect `AUTO_APPROVED` within a few seconds
3. Submit one with an explicit registration-fee demand — expect `AUTO_REJECTED` with the fee
   sentence highlighted
4. Submit a borderline commission-only posting — expect `IN_REVIEW`
5. As a moderator, open the queue, claim the borderline case, confirm the highlighted evidence
   and reasons match the text, request changes with a reason code
6. As the employer, see the reason, edit, resubmit, confirm a new run and a new version
7. Confirm the audit log contains every transition with the correct actor

---

## Status

Plan approved 2026-09-11. Implementation begins at Phase 0. Update this section as phases land.

| Phase | State |
| --- | --- |
| 0 — Scaffold | Done and verified (2026-09-11). `docker compose up --build` runs clean: postgres and redis healthy, migrations applied (including the custom user model), backend `/healthz/` and the frontend dev server both return 200, and a Celery task round-tripped through the real Redis broker and worker (not eager mode). |
| 1 — Domain | Done and verified (2026-09-11). `postings`, `moderation`, `policies`, `audit` apps with all models from the data model section, admin registrations, factory-boy factories, and a `seed_demo` command. Migrations applied in the docker compose stack; posting creation verified through the real admin add view (test client), not just the ORM. |
| 2 — Rules engine | Done and verified (2026-09-11). Normalizer with a dual-view offset map (`folded` for word-boundary rules, `collapsed` for leetspeak/separator-evasion resistance), the `Rule` protocol, and a 9-rule job-board pack covering every taxonomy category a deterministic pattern can catch. Policy-driven via `apps.policies.services.get_rule_config`. 44 engine tests: positive, negative, and an evasion case for every text-based rule. |
| 3 — Classifier | Done and verified (2026-09-11). 370-example synthetic seed corpus (`ml/data/generate_seed_corpus.py` → `seed.jsonl`) covering the 4 model-tagged categories (`ILLEGAL_WORK`, `MLM_RECRUITMENT`, `DISCRIMINATORY`, `GHOST_JOB`); TF-IDF (word 1–2gram + char 3–5gram) → one-vs-rest logistic regression in `ml/train.py`, with a champion/challenger promotion gate on CRITICAL/HIGH precision; `apps/moderation/engine/classifier.py` mirrors `Rule`'s shape so Phase 4 can treat rule and model hits identically, with per-hit `contributing_terms` for evidentiary (not generated) reasoning. Held-out precision 0.92–1.00 across all 4 categories on this corpus. Rebuilt the docker images with scikit-learn baked in and reran the full suite (69 tests) on the fresh images. |
| 4 — Orchestration | Done and verified (2026-09-11). One Celery task (`apps/moderation/tasks.py`) runs normalize → rules → classifier → dedupe → fuse → persist → route as internal stages (not a literal `celery.chain()` — `RuleHit`'s enum fields aren't trivially JSON-serializable between chained tasks, and nothing yet needs separate queues; each stage is still independently tested). New: `engine/dedupe.py` (SimHash, empirically-tuned Hamming threshold — job postings are much shorter than the web documents SimHash was designed for), `engine/fusion.py` (noisy-OR score combination, literal-CRITICAL-rule-hit short-circuits to auto-reject), `engine/reasons.py`. `apps/moderation/services.py` is the single entry point (`submit_for_moderation`) that guarantees a run exists before the task fires and that resubmission bumps `version`. 5 integration tests cover all three routing outcomes plus the engine-failure path, asserting on real `ModerationRun`/`Flag` rows. |
| 5 — Submitter API and portal | Done and verified (2026-09-11). Session auth (`apps/accounts`: csrf/login/logout/me) needed for both this and Phase 6. `apps/postings` DRF viewset: create submits immediately (202), list/retrieve scoped to the owner, PATCH gated to `CHANGES_REQUESTED` and re-triggers analysis. Submitter-facing serializer deliberately excludes risk_score/confidence/contributing_terms. React: `PostingForm`, list/detail/new pages, evidence highlighting via `HighlightedText`, role-aware `Layout` + `ProtectedRoute`, `react-router-dom`. |
| 6 — Moderator API and console | Done and verified (2026-09-11). Redis claim locks (`apps/moderation/claims.py`, re-claiming your own claim renews it) backing `ReviewClaim` rows. Queue endpoint annotates risk_score/routing via a Subquery on each posting's latest run, filters by category/severity in one `.filter()` call so they apply to the same joined flag row. Case detail exposes full internal flag data (confidence, contributing_terms) — nothing hidden from a moderator. Three-pane React console: posting with severity-colored evidence highlighting, flag cards (click to scroll/highlight), decision panel (4 actions, reason code, notes), claim auto-renews every 3 minutes and releases on unmount. 10 API tests. Full stack verified live end-to-end via curl through the real Docker network (not just pytest): submit → async worker → auto-reject with real evidence spans and classifier contributing_terms → moderator claims → decides REQUEST_CHANGES → submitter sees the moderator's actual notes, CORS preflight confirmed for the frontend origin. |
| 7 — Feedback and hardening | Done and verified (2026-09-12). `apps/moderation/exports.py` derives training labels from real moderator decisions (REJECTED → its surviving model-category flags, APPROVED → negative examples for every model category, everything else skipped) and `write_export()` regenerates `ml/data/exported_labels.jsonl` from scratch each time so a later false-positive mark can't leave a stale label behind; wired to a nightly Celery beat task and a `manage.py export_training_labels` command, and `ml/train.py`'s `load_all_examples()` folds it in alongside the seed corpus. Idempotency: resubmitting unchanged content returns the existing run instead of bumping version or re-triggering. Submission throttle now has a test that drives the real `ScopedRateThrottle` class rather than trusting config. Structured logging: every pipeline run's log lines are keyed by run id. Sentry hook wired (no-op until `SENTRY_DSN` is set) and Flower added as its own compose service for Celery visibility — both verified live against the running stack, including catching and fixing a stale local `.env` missing the new Flower/Sentry variables. Escalation UX: an `ESCALATE` decision now marks the posting `is_escalated` in the queue (`Decision.Action.ESCALATE` still exists on the posting, annotated via `Exists`) and escalated cases sort first by default, with a badge in the console. Verified beyond pytest: a real borderline posting was submitted, routed to `HUMAN_REVIEW`, rejected by `demo_moderator` through the live API, and the export command turned that decision into an actual training example that `ml/train.py` picked up (370 → 371 examples). Frontend: `HighlightedText` (the piece most likely to break subtly) now has a Vitest + React Testing Library suite covering no-span passthrough, exact span wrapping, zero-length/inverted span filtering, out-of-order/overlapping span clamping, severity color fallback, and active-span ringing. |
