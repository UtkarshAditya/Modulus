# Modulus — marketing website

Originally a design-only pass; now fully ported into `frontend/` as the app's public "/" route,
with real Django-backed signup/login wired in (see "From design to real feature" below). The
original static single-file preview (Claude Artifact, pre-port, kept for reference only — its own
copy has since drifted from what's actually in the repo):

https://claude.ai/code/artifact/3511c6a5-a2bd-4fa9-be58-bdaf794401d5

The decision from the "open questions" section below — landing page lives inside `frontend/`,
sharing the same auth state and router as the submitter/moderator app, rather than as a separate
static site — is what actually got built.

---

## Brand read

**Modulus** — the mathematical term for "distance from zero" (`|x|`). The product's actual job is
exactly that: measuring how far a piece of submitted content sits from a policy, as a number, with
receipts. The brand leans into that literally — the wordmark is set inside two vertical bars
(`|MODULUS|`), the same notation, and that bracket motif recurs on emphasized panels instead of
drop shadows.

The visual direction is **instrumentation, not SaaS-gradient**: a control-room/oscilloscope
aesthetic — hairline grid lines, monospace numerals for every score and stat, sharp-edged panels,
a signal-amber accent for "flagged/attention" states and a teal for "clear" states. This is a
deliberate reaction against the generic AI-landing-page look (purple-to-blue gradients, Inter or
Space Grotesk, `rounded-lg` everywhere, centered hero) — moderation is a measurement problem, so
the page should look like it was built by people who instrument things.

## Design tokens

**Color** (named, both themes defined — see the artifact's `:root` / `prefers-color-scheme` /
`[data-theme]` blocks):

| Token | Light | Dark | Role |
| --- | --- | --- | --- |
| `--ink` / `--paper` | `#0b0f14` / `#f2f4f6` | `#e9eef2` / `#0a0e13` | base text / base ground (swap per theme) |
| `--signal` | `#e8630f` | `#ff8a3d` | primary accent — flags, CTAs, active pipeline stage |
| `--clear` | `#0f8a74` | `#3fd6b6` | secondary semantic accent — "approved / no duplicate" |
| `--critical` | `#c62828` | `#ff6b5e` | reserved strictly for CRITICAL-severity badges |
| `--steel` | `#5b6b77` | `#94a3ad` | muted text — a grey with a cool, not neutral, bias |

Two components deliberately **don't** flip with the site theme — the integration code sample and
the waitlist band — on the reasoning that an instrument readout and a "signal" band read as
fixed, physical panels, not page chrome. They use their own constant tokens (`--term-*`,
`--band-*`) rather than the theme-flipping `--ink`/`--paper`, which was the source of a real bug
caught before publishing (see below).

**Type:**
- Display — **Archivo** (600–800): wordmark, headlines, big numerals. Geometric and a little
  stamped/industrial rather than a soft grotesk.
- Body — **IBM Plex Sans** (400–600): running copy. Chosen because it's part of IBM's actual
  technical/engineering design system, not a generic humanist sans.
- Mono — **IBM Plex Mono**: every score, category enum, stat, chip, and the code sample. Anything
  that's *data* is set in mono with `font-variant-numeric: tabular-nums` so digits line up.

**Layout:** a single long-scroll page structured as a literal signal path — content enters at the
top, gets visibly piped through the same six real pipeline stages the backend actually runs, and
exits as a routed decision. One flagship scrollytelling moment (the pipeline section) carries the
page; everything else is calm.

## Section-by-section

1. **Nav** — `|MODULUS|` wordmark, anchor links to the three content sections, ghost "Log in" /
   solid "Sign up" buttons. Condenses (less vertical padding) after 40px of scroll.
2. **Hero** — thesis statement ("Score. Explain. Route. Automatically.") plus a live-looking
   intake panel: a marquee of sample postings ticking past with APPROVED/REVIEW/REJECTED tags and
   a small risk-score gauge, running ambiently at rest (not gated behind scroll — the page must
   read correctly on first paint).
3. **Stat strip** — four real numbers pulled from this project's own verified results: 11 flag
   categories, 6 pipeline stages, 0.92–1.00 held-out precision on CRITICAL/HIGH categories
   (from `docs/PLAN.md`'s Phase 3 entry), 3 routing outcomes. Count up on scroll.
4. **Pipeline (flagship scroll moment)** — see below.
5. **Evidence** — a real example from this session's own live verification (the MLM/discriminatory
   posting a moderator actually rejected in the Phase 7 work): evidence spans highlight in place
   and annotation callouts fade in, mirroring the real `HighlightedText` component's job.
6. **Use cases** — Job board postings styled "in production"; Marketplace, UGC, Reviews, Financial
   ads, and Visual moderation styled "queued/roadmap" with a slow ambient scan-line sweep and
   reduced opacity — legible as "coming soon," not as a broken card.
7. **Integrate** — a three-step plug-and-play explanation next to a mock request/webhook pair,
   making the "plug and play" pitch concrete without needing a real API.
8. **Console preview** — a stylized three-pane mockup of the actual moderator console's shape
   (queue / flags / decision) from Phase 6.
9. **CTA** — fixed dark "instrument band," waitlist email form (non-functional, shows a toast on
   submit).
10. **Footer** — wordmark, repeated anchors, a mono status line.

Everything is real, specific copy — no lorem ipsum, no generic "streamline your workflow"
filler — drawn from the actual taxonomy, pipeline, and test data this project has already built
and verified.

## The pipeline section — how the scroll mechanic works

This is the page's one orchestrated set-piece, so it gets the most explanation:

- A tall (`560vh`) wrapper holds a `position: sticky` panel, so the stage panel stays pinned in
  the viewport while the wrapper scrolls underneath it — six stages mapped to six "screens" of
  scroll distance.
- A GSAP `ScrollTrigger` (`scrub: true`, no `pin` — the CSS `sticky` already handles pinning, which
  is more robust inside an iframe than GSAP's own pin/pin-spacer mechanism) reports scroll progress
  0–1, which is mapped to a stage index `0–5`.
- Each stage lights up its node on the progress rail, cross-fades in its own annotation panel
  (normalize's before/after chip, rules' flag chips, the classifier's probability bars, dedupe's
  Hamming-distance readout, the fusion gauge sweeping to its score, the final route badge), and
  progressively highlights the matching evidence span in a real sample job posting — the same
  advance-fee/off-platform/discriminatory example used throughout Phase 2–4's own tests.
- Below 900px, `gsap.matchMedia()` swaps this whole mechanic off and renders all six stages
  statically stacked — pinning a 560vh scroll region is not a good mobile pattern, and the
  fallback still tells the same story without motion sickness risk.
- `prefers-reduced-motion: reduce` disables the ambient marquee and scan-line animations; the
  scroll-scrubbed content still updates (it's driven by scroll position either way, not a timed
  animation), but nothing plays on its own.

## Scroll-animation ideas (requested — full list)

Implemented in the current preview:

1. **Ambient hero intake marquee** — a looping strip of sample submissions with outcome tags,
   running continuously at rest (not scroll-triggered), plus a small gauge that ticks through
   sample risk scores. Establishes "this is a live system" before any scrolling happens.
2. **Stat count-up** — the four headline numbers animate from 0 to their real value once scrolled
   into view.
3. **Pipeline scrub-and-pin** (flagship) — described above: the page's single most distinctive
   moment, because it's a literal, accurate diagram of the actual architecture, not a generic
   "how it works" graphic.
4. **Evidence-span reveal** — highlighted spans and their annotation callouts stagger in when the
   evidence section scrolls into view, mirroring the real product's evidence-first design
   principle instead of just describing it.
5. **Use-case scan-line sweep** — a slow, continuous diagonal light sweep across the "coming soon"
   cards, reading as "queued/being worked on" rather than "broken" or "empty."
6. **Section reveals** — a restrained fade/slide-up on section headers and panels as they enter,
   used as connective tissue between the bigger moments, not as its own attraction.

Suggested for a later pass, not built into this preview (to keep the current page from becoming a
demo reel — per the design principle that one orchestrated moment beats several competing ones):

7. **Threshold "trip" number line** — a horizontal line marked with the policy's
   `auto_approve_below` / `auto_reject_above` bands; a marker slides along it and visibly trips a
   gate as the fusion score crosses a threshold. Would pair naturally with the Fuse/Route stages.
8. **Console parallax** — the three mockup panes entering at slightly different scroll speeds for
   a sense of depth, plus a scripted micro-interaction (a flag card "clicked," its evidence span
   pulsing in response) to show the click-to-scroll behavior the real console has.
9. **Calibration-tick rail** — a thin ruler/graticule strip down one page margin whose ticks
   advance with scroll position, reinforcing the instrumentation motif ambiently across the whole
   page rather than in one section.
10. **Oscilloscope-trace dividers** — an SVG waveform between major sections that draws itself in
    (stroke animation) as it enters view, shifting from a calm to a spiked waveform to mark the
    transition from "clean content" framing to "risk" framing.

## Bugs caught during design (worth remembering)

- `--ink` and `--paper` are intentionally *swapped* between light and dark themes (that's how the
  rest of the page inverts correctly). Two components — the code sample and the CTA band — were
  meant to look like fixed dark instrument panels in *both* site themes. Using `var(--ink)` for
  their backgrounds broke that: in dark mode, `--ink` itself flips to a *light* color, so the code
  panel would have rendered with light-on-light, invisible text. Fixed by giving those two
  components their own constant, non-themed tokens (`--term-*`, `--band-*`) instead of reusing the
  theme-flipping base tokens. Worth checking for again if either component is touched later — the
  giveaway is any rule that mixes a hardcoded light-mode-only color with a token that flips.
- A stray typo (`color:#6b7active`) in the placeholder-text rule was invalid CSS and would have
  silently no-op'd (browsers drop a single invalid declaration, not the whole rule block) — caught
  by re-reading the CSS before publishing rather than by any tooling, since this is a standalone
  HTML file with no linter in the loop.

## From design to real feature (implemented)

The landing page became a real, functional part of the app:

- **Where it lives**: `frontend/src/pages/landing/LandingPage.tsx` + `frontend/src/styles/modulus.css`
  (the full design-token system, `m-`-prefixed to avoid colliding with the internal app's Tailwind
  classes) — mounted at `/` in `App.tsx`, alongside the existing submitter/moderator routes, not a
  separate static site. `gsap` is now a real npm dependency (was CDN-only in the artifact); the
  pipeline scroll-scrub, evidence reveal, stat count-up, and hero load sequence all run through
  `gsap.context()` scoped to a root ref, reverted on unmount — the React-idiomatic pattern for
  cleaning up ScrollTriggers when the route changes.
- **Signup**: new `POST /api/auth/signup/` (`apps/accounts`) — always creates an `EMPLOYER`
  (matches the model default; moderators/admins stay `seed_demo`-only), throttled at 10/hour by IP,
  validated through Django's real `AUTH_PASSWORD_VALIDATORS`, logs the new user in immediately.
  `frontend/src/pages/SignupPage.tsx` is a real form against it, brand-styled to match the landing
  page rather than the internal app's Tailwind look.
- **Auth-gated navigation**: the "Job board postings" use-case card is a real `<Link to="/postings">`
  wrapping the whole card. No special-casing was needed for the redirect — `ProtectedRoute` now
  appends `?next=<path>` when it bounces an unauthenticated visitor to `/login`, and both
  `LoginPage` and `SignupPage` read that param and land the user back where they were headed after
  auth succeeds. `LoginPage` was also restyled to match the Modulus brand instead of the old
  Tailwind slate card.
- **Nav is auth-aware**: logged out shows Log in/Sign up; logged in shows Dashboard (routes to
  `/moderation` or `/postings` depending on role, same logic the old `HomeRedirect` used to own)
  and Log out. The bottom CTA section does the same swap instead of the artifact's non-functional
  "join waitlist" email form, which was dropped entirely now that real signup exists — no point
  maintaining two signup-shaped UIs.
- Verified live with a real Playwright/Chrome run against the dev server (not just typecheck/build):
  logged-out click on the use-case card → `/login?next=%2Fpostings`; fresh signup → lands on
  `/postings` inside the real app shell; clicking the card again while authenticated skips the
  redirect entirely; log out → log back in with `demo_employer` → same destination. Zero console
  errors across the whole run.
- Hit the project's known Docker-on-Windows Vite-watch issue during this work (bind-mounted source
  edits not reaching the running dev server) — resolved by restarting the `frontend` container;
  now a standing memory entry so it's not re-diagnosed from scratch next time.

## Open questions for the next pass

- Copy throughout is a first pass, not legal/marketing-reviewed — the precision stat in particular
  (0.92–1.00) is real but was measured on the synthetic seed corpus (`docs/PLAN.md` Phase 3), not
  production traffic; that caveat needs to survive into whatever copy actually ships.
- The bottom CTA and hero "Start free" now both go straight to `/signup` — no separate waitlist /
  "request access" path exists anymore now that signup is real and unrestricted. Worth revisiting
  if the actual go-to-market wants gated access instead of open self-serve.
- The console-preview section is still a static mockup (not the real `CasePage`/`QueuePage`) —
  intentionally, since it's illustrating the moderator experience to a logged-out visitor, but
  worth a second look if it ever drifts from what the real console actually looks like.
