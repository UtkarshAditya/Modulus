import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useAuth } from '../../hooks/useAuth'
import '../../styles/modulus.css'

gsap.registerPlugin(ScrollTrigger)

const INTAKE_ROWS: Array<[string, 'clear' | 'review' | 'reject', string]> = [
  ['Warehouse Associate', 'clear', 'APPROVED'],
  ['Data Entry Specialist', 'reject', 'REJECTED'],
  ['Marketing Intern', 'clear', 'APPROVED'],
  ['Sales Representative', 'review', 'REVIEW'],
  ['Customer Support Rep', 'clear', 'APPROVED'],
  ['Crypto Trading Advisor', 'reject', 'REJECTED'],
]

const LIVE_SCORES = [0.18, 0.09, 0.62, 0.97, 0.14, 0.81, 0.22, 0.05]

export function LandingPage() {
  const rootRef = useRef<HTMLDivElement>(null)
  const navRef = useRef<HTMLElement>(null)
  const liveScoreRef = useRef<HTMLSpanElement>(null)
  const gaugeArcRef = useRef<SVGPathElement>(null)
  const { user, logout } = useAuth()

  const authed = user?.authenticated ?? false
  const dashboardPath = user?.role === 'MODERATOR' || user?.role === 'ADMIN' ? '/moderation' : '/postings'

  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const ctx = gsap.context(() => {
      gsap.set('[data-anim="hero"]', { opacity: 1, y: 0 })
      if (!reduced) {
        gsap.from('[data-anim="hero"]', { opacity: 0, y: 22, duration: 0.7, ease: 'power2.out', stagger: 0.09 })
      }

      gsap.utils.toArray<HTMLElement>('.m-reveal').forEach((el) => {
        gsap.fromTo(
          el,
          { opacity: 0, y: 20 },
          {
            opacity: 1,
            y: 0,
            duration: 0.6,
            ease: 'power2.out',
            scrollTrigger: { trigger: el, start: 'top 88%', toggleActions: 'play none none reverse' },
          },
        )
      })

      gsap.utils.toArray<HTMLElement>('[data-count]').forEach((el) => {
        const target = Number(el.getAttribute('data-count'))
        const obj = { v: 0 }
        ScrollTrigger.create({
          trigger: el,
          start: 'top 90%',
          once: true,
          onEnter: () =>
            gsap.to(obj, {
              v: target,
              duration: 1.1,
              ease: 'power1.out',
              onUpdate: () => {
                el.textContent = String(Math.round(obj.v))
              },
            }),
        })
      })
      gsap.utils.toArray<HTMLElement>('[data-count-decimal]').forEach((el) => {
        const target = Number(el.getAttribute('data-count-decimal'))
        const obj = { v: 0 }
        ScrollTrigger.create({
          trigger: el,
          start: 'top 90%',
          once: true,
          onEnter: () =>
            gsap.to(obj, {
              v: target,
              duration: 1.1,
              ease: 'power1.out',
              onUpdate: () => {
                el.textContent = obj.v.toFixed(2)
              },
            }),
        })
      })

      const STAGE_COUNT = 6
      let lastStage = -1
      const nodes = root.querySelectorAll<HTMLElement>('.m-pipeline-nodes li')
      const variants = root.querySelectorAll<HTMLElement>('.m-stage-variant')
      const marks = root.querySelectorAll<HTMLElement>('.m-mark[data-lit-at]')
      const fillEl = root.querySelector<HTMLElement>('.m-pipeline-fill')

      function applyStage(idx: number) {
        if (idx === lastStage) return
        lastStage = idx
        nodes.forEach((n) => n.classList.toggle('is-active', Number(n.dataset.stage) <= idx))
        variants.forEach((v) => v.classList.toggle('is-active', Number(v.dataset.stage) === idx))
        marks.forEach((m) => m.classList.toggle('is-lit', idx >= Number(m.dataset.litAt)))
        if (idx === 2) {
          variants.forEach((v) => {
            if (Number(v.dataset.stage) !== 2) return
            v.querySelectorAll<HTMLElement>('.m-fill').forEach((f) => {
              f.style.width = `${f.getAttribute('data-target')}%`
            })
          })
        }
      }
      applyStage(0)

      const mm = gsap.matchMedia()
      mm.add('(min-width: 901px)', () => {
        ScrollTrigger.create({
          trigger: '.m-pipeline-pin-wrap',
          start: 'top top',
          end: 'bottom bottom',
          scrub: true,
          onUpdate: (self) => {
            const p = self.progress
            if (fillEl) fillEl.style.width = `${(p * 100).toFixed(1)}%`
            applyStage(Math.min(STAGE_COUNT - 1, Math.floor(p * STAGE_COUNT)))
          },
        })
      })
      mm.add('(max-width: 900px)', () => {
        if (fillEl) fillEl.style.width = '100%'
        variants.forEach((v) => {
          v.classList.add('is-active')
          v.style.display = 'block'
          v.style.marginBottom = '18px'
        })
        marks.forEach((m) => m.classList.add('is-lit'))
        nodes.forEach((n) => n.classList.add('is-active'))
        root.querySelectorAll<HTMLElement>('.m-fill').forEach((f) => {
          f.style.width = `${f.getAttribute('data-target') ?? '0'}%`
        })
      })

      const evidenceCard = root.querySelector('.m-evidence-card')
      if (evidenceCard) {
        ScrollTrigger.create({
          trigger: evidenceCard,
          start: 'top 75%',
          once: true,
          onEnter: () => {
            gsap.utils.toArray<HTMLElement>('.m-ev-mark').forEach((el, i) => {
              gsap.to(el, {
                opacity: 1,
                y: 0,
                duration: 0.4,
                delay: i * 0.35,
                onStart: () => el.classList.add('show'),
              })
            })
            gsap.utils.toArray<HTMLElement>('.m-callout').forEach((el, i) => {
              gsap.to(el, {
                opacity: 1,
                x: 0,
                duration: 0.5,
                delay: 0.3 + i * 0.35,
                onStart: () => el.classList.add('show'),
              })
            })
          },
        })
      }
    }, root)

    return () => ctx.revert()
  }, [])

  useEffect(() => {
    let i = 0
    const id = setInterval(() => {
      i = (i + 1) % LIVE_SCORES.length
      const score = LIVE_SCORES[i]
      if (liveScoreRef.current) liveScoreRef.current.textContent = score.toFixed(2)
      if (gaugeArcRef.current) gaugeArcRef.current.style.strokeDashoffset = String(Math.round(157 - score * 140))
    }, 2200)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    function onScroll() {
      navRef.current?.classList.toggle('is-condensed', window.scrollY > 40)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className="modulus-page" ref={rootRef}>
      <header className="m-nav" ref={navRef}>
        <Link to="/" className="m-wordmark">
          <span className="m-bar">|</span>MODULUS<span className="m-bar">|</span>
        </Link>
        <ul className="m-nav-links">
          <li>
            <a href="#how-it-works">How it works</a>
          </li>
          <li>
            <a href="#use-cases">Use cases</a>
          </li>
          <li>
            <a href="#integrate">Integrate</a>
          </li>
        </ul>
        <div className="m-nav-actions">
          {authed ? (
            <>
              <Link to={dashboardPath} className="m-btn m-btn-ghost">
                Dashboard
              </Link>
              <button className="m-btn m-btn-solid" onClick={() => logout()}>
                Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="m-btn m-btn-ghost">
                Log in
              </Link>
              <Link to="/signup" className="m-btn m-btn-solid">
                Sign up
              </Link>
            </>
          )}
        </div>
      </header>

      <main>
        <section className="m-hero" id="top">
          <div className="m-container m-hero-grid">
            <div>
              <span className="m-eyebrow" data-anim="hero">
                MODERATION INFRASTRUCTURE
              </span>
              <h1 data-anim="hero">
                Score. Explain. Route. <em>Automatically.</em>
              </h1>
              <p className="m-lede" data-anim="hero">
                Modulus sits in front of whatever your users submit, computes how far it sits from
                your policy, and turns that into an auto&#8209;approve, an auto&#8209;reject, or a
                pre&#8209;reasoned case file for a human — in milliseconds, with the evidence
                attached.
              </p>
              <div className="m-hero-ctas" data-anim="hero">
                <Link to={authed ? dashboardPath : '/signup'} className="m-btn m-btn-solid m-btn-lg">
                  {authed ? 'Go to dashboard' : 'Start free'}
                </Link>
                <a href="#how-it-works" className="m-btn m-btn-ghost m-btn-lg">
                  See it work ↓
                </a>
              </div>
              <div className="m-hero-note" data-anim="hero">
                v1 live for job board postings · four more surfaces in the pipeline
              </div>
            </div>
            <div className="m-intake" data-anim="hero">
              <div className="m-intake-head">
                <span className="m-mono">LIVE INTAKE</span>
                <span className="m-mono">job_postings</span>
              </div>
              <div className="m-intake-stream">
                <div className="m-intake-track">
                  {[...INTAKE_ROWS, ...INTAKE_ROWS].map(([title, kind, label], i) => (
                    <div className="m-intake-row" key={i}>
                      <span>{title}</span>
                      <span className={`m-tag m-tag-${kind}`}>{label}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="m-gauge-wrap">
                <svg width="64" height="40" viewBox="0 0 120 70">
                  <path
                    d="M10 65 A50 50 0 0 1 110 65"
                    fill="none"
                    stroke="var(--m-border)"
                    strokeWidth={8}
                    strokeLinecap="round"
                  />
                  <path
                    ref={gaugeArcRef}
                    d="M10 65 A50 50 0 0 1 110 65"
                    fill="none"
                    stroke="var(--m-signal)"
                    strokeWidth={8}
                    strokeLinecap="round"
                    strokeDasharray={157}
                    strokeDashoffset={132}
                  />
                </svg>
                <div className="m-gauge-readout">
                  <div className="m-lbl">risk score, live median</div>
                  <div className="m-big m-mono">
                    <span ref={liveScoreRef}>0.18</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="m-stats">
          <div className="m-container" style={{ paddingInline: 0 }}>
            <div className="m-stats-row">
              <div className="m-stat m-reveal">
                <div className="m-num m-mono">
                  <span data-count={11}>0</span>
                </div>
                <div className="m-cap">flag categories in the job‑board taxonomy</div>
              </div>
              <div className="m-stat m-reveal">
                <div className="m-num m-mono">
                  <span data-count={6}>0</span>
                </div>
                <div className="m-cap">pipeline stages, from normalize to route</div>
              </div>
              <div className="m-stat m-reveal">
                <div className="m-num m-mono">
                  <span data-count-decimal={0.92}>0.00</span>
                  <span className="m-unit">–1.00</span>
                </div>
                <div className="m-cap">held‑out precision, critical &amp; high categories</div>
              </div>
              <div className="m-stat m-reveal">
                <div className="m-num m-mono">
                  <span data-count={3}>0</span>
                </div>
                <div className="m-cap">routing outcomes — approve, reject, or review</div>
              </div>
            </div>
          </div>
        </section>

        <section className="m-pipeline" id="how-it-works">
          <div className="m-container">
            <div className="m-section-head m-reveal">
              <span className="m-eyebrow">HOW IT WORKS</span>
              <h2>One pipeline, six stages, zero manual triage.</h2>
              <p>
                Scroll — this is the exact path a submission takes, end to end, on a real posting
                we ran through it.
              </p>
            </div>
          </div>

          <div className="m-pipeline-pin-wrap">
            <div className="m-pipeline-sticky">
              <div className="m-container">
                <div className="m-pipeline-rail">
                  <div className="m-pipeline-track">
                    <div className="m-pipeline-fill" />
                  </div>
                  <ol className="m-pipeline-nodes">
                    {['Normalize', 'Rules', 'Classifier', 'Dedupe', 'Fuse', 'Route'].map((label, i) => (
                      <li key={label} data-stage={i}>
                        <span className="m-node-dot" />
                        <span>{label}</span>
                      </li>
                    ))}
                  </ol>
                </div>

                <div className="m-pipeline-stage-panel">
                  <div className="m-stage-sample">
                    <span className="m-sample-title">Remote Data Entry Specialist</span>
                    Earn $5,000/week from home. Just pay a{' '}
                    <span className="m-mark" data-lit-at={1} data-sev="CRITICAL">
                      $50 registration fee
                    </span>{' '}
                    for your starter kit and message us on{' '}
                    <span className="m-mark" data-lit-at={1} data-sev="HIGH">
                      WhatsApp
                    </span>{' '}
                    to begin. Build your own team of recruits for extra commission on their sales.
                    Must be a{' '}
                    <span className="m-mark" data-lit-at={1} data-sev="HIGH">
                      US citizen under 40
                    </span>
                    .
                  </div>

                  <div className="m-stage-detail">
                    <div className="m-stage-variant is-active" data-stage={0}>
                      <span className="m-stage-index">STAGE 01 / 06</span>
                      <h4>Normalize</h4>
                      <p>Unicode‑folds the text and reverses common evasions before any rule or model sees it.</p>
                      <div className="m-transform-chip">
                        <span className="m-old">wh@tsapp</span>
                        <span className="m-arrow">→</span>
                        <span>whatsapp</span>
                      </div>
                    </div>
                    <div className="m-stage-variant" data-stage={1}>
                      <span className="m-stage-index">STAGE 02 / 06</span>
                      <h4>Rules</h4>
                      <p>
                        Nine deterministic rules scan for literal, high‑precision violations — the ones
                        where a false positive isn't tolerable.
                      </p>
                      <div className="m-chip-row">
                        <span className="m-chip" data-sev="CRITICAL">
                          ADVANCE_FEE · CRITICAL
                        </span>
                        <span className="m-chip" data-sev="HIGH">
                          OFF_PLATFORM_REDIRECT · HIGH
                        </span>
                        <span className="m-chip" data-sev="HIGH">
                          DISCRIMINATORY · HIGH
                        </span>
                      </div>
                    </div>
                    <div className="m-stage-variant" data-stage={2}>
                      <span className="m-stage-index">STAGE 03 / 06</span>
                      <h4>Classifier</h4>
                      <p>A calibrated model reads for tone and recruitment structure — the pattern no regex can catch.</p>
                      <div className="m-bar-demo">
                        <div className="m-row">
                          <span style={{ width: '9em' }}>MLM_RECRUITMENT</span>
                          <div className="m-track">
                            <div className="m-fill" data-target={87} />
                          </div>
                          <span className="m-val">0.87</span>
                        </div>
                        <div className="m-row">
                          <span style={{ width: '9em' }}>GHOST_JOB</span>
                          <div className="m-track">
                            <div className="m-fill" data-target={4} />
                          </div>
                          <span className="m-val">0.04</span>
                        </div>
                      </div>
                    </div>
                    <div className="m-stage-variant" data-stage={3}>
                      <span className="m-stage-index">STAGE 04 / 06</span>
                      <h4>Dedupe</h4>
                      <p>SimHash compares this submission against the recent window and the sender's own history.</p>
                      <div className="m-transform-chip">
                        <span>Hamming distance 41</span>
                        <span className="m-arrow">→</span>
                        <span>no duplicate found</span>
                      </div>
                    </div>
                    <div className="m-stage-variant" data-stage={4}>
                      <span className="m-stage-index">STAGE 05 / 06</span>
                      <h4>Fuse</h4>
                      <p>
                        Rule weights and model probabilities combine into one score — a literal
                        CRITICAL hit overrides everything else.
                      </p>
                      <div className="m-gauge-demo">
                        <svg width="120" height="70" viewBox="0 0 120 70">
                          <path
                            d="M10 65 A50 50 0 0 1 110 65"
                            fill="none"
                            stroke="var(--m-border)"
                            strokeWidth={9}
                            strokeLinecap="round"
                          />
                          <line
                            x1={60}
                            y1={65}
                            x2={60}
                            y2={20}
                            stroke="var(--m-signal)"
                            strokeWidth={3}
                            strokeLinecap="round"
                            className="m-gauge-needle"
                          />
                          <circle cx={60} cy={65} r={4} fill="var(--m-signal)" />
                        </svg>
                        <div className="m-gauge-num">0.97</div>
                      </div>
                    </div>
                    <div className="m-stage-variant" data-stage={5}>
                      <span className="m-stage-index">STAGE 06 / 06</span>
                      <h4>Route</h4>
                      <p>Compared against the active policy's thresholds for this category and score.</p>
                      <div className="m-route-badge">→ AUTO_REJECT</div>
                      <p style={{ marginTop: 10, fontSize: '.82rem' }}>
                        Reason: unambiguous literal match on an advance‑fee demand.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="m-evidence">
          <div className="m-container">
            <div className="m-section-head m-reveal">
              <span className="m-eyebrow">EVIDENTIARY, NOT NARRATIVE</span>
              <h2>Every flag comes with receipts.</h2>
              <p>
                No generated explanations. Rule hits carry the exact matched span; model flags carry
                their top contributing terms. A moderator sees precisely why, in the original text.
              </p>
            </div>
            <div className="m-evidence-grid">
              <div className="m-evidence-card m-reveal">
                <span className="m-kicker">Sales Representative — submitted posting</span>
                <p>
                  Commission‑only role, build your own{' '}
                  <span className="m-ev-mark" data-order={1}>
                    downline of recruits
                  </span>{' '}
                  and earn from their sales too. Must be a{' '}
                  <span className="m-ev-mark" data-order={2}>
                    US citizen under 40
                  </span>{' '}
                  to apply.
                </p>
              </div>
              <div className="m-ev-callouts">
                <div className="m-callout m-reveal" data-order={1}>
                  <div className="m-cat">MLM_RECRUITMENT · HIGH</div>
                  <div className="m-meta">Model confidence 0.87 — recruitment‑structure language, not a keyword match.</div>
                  <div className="m-terms">top terms: downline, commission‑only, recruits</div>
                </div>
                <div className="m-callout m-reveal" data-order={2}>
                  <div className="m-cat">DISCRIMINATORY · HIGH</div>
                  <div className="m-meta">Rule‑matched: age and citizenship stated as hiring criteria.</div>
                  <div className="m-terms">policy: §4.2 protected‑class criteria</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="m-usecases" id="use-cases">
          <div className="m-container">
            <div className="m-section-head m-reveal">
              <span className="m-eyebrow">ONE PIPELINE, MANY SURFACES</span>
              <h2>Job postings are live. The rest are queued.</h2>
              <p>
                The engine is domain‑agnostic — swapping surfaces means swapping the rule pack and
                the trained classifier, not the pipeline.
              </p>
            </div>
          </div>
          <div className="m-container" style={{ paddingInline: 0 }}>
            <div className="m-usecases-grid">
              <Link to={authed ? '/postings' : '/login?next=%2Fpostings'} className="m-usecase is-live m-reveal">
                <span className="m-uc-status">
                  <span className="m-dot" />
                  In production
                </span>
                <h3>Job board postings</h3>
                <p>
                  Advance‑fee scams, MLM recruitment, off‑platform redirects, upfront document
                  requests, discriminatory criteria, ghost jobs.
                </p>
                <div className="m-uc-tags">
                  <span>rules</span>
                  <span>classifier</span>
                  <span>dedupe</span>
                </div>
                <div className="m-uc-open">Open the submitter portal →</div>
              </Link>
              <div className="m-usecase m-reveal">
                <span className="m-uc-status">
                  <span className="m-dot" />
                  Queued
                </span>
                <h3>Marketplace listings</h3>
                <p>Prohibited or regulated goods, counterfeits, implausible pricing, contact‑info leakage.</p>
                <div className="m-uc-tags">
                  <span>rules</span>
                  <span>classifier</span>
                </div>
              </div>
              <div className="m-usecase m-reveal">
                <span className="m-uc-status">
                  <span className="m-dot" />
                  Queued
                </span>
                <h3>User‑generated content</h3>
                <p>Harassment, hate speech, self‑harm signals, spam, doxxing — routed with the same evidence‑first discipline.</p>
                <div className="m-uc-tags">
                  <span>classifier</span>
                  <span>dedupe</span>
                </div>
              </div>
              <div className="m-usecase m-reveal">
                <span className="m-uc-status">
                  <span className="m-dot" />
                  Queued
                </span>
                <h3>Product &amp; app reviews</h3>
                <p>Incentivized reviews, review‑bombing rings, competitor astroturfing.</p>
                <div className="m-uc-tags">
                  <span>classifier</span>
                  <span>dedupe</span>
                </div>
              </div>
              <div className="m-usecase m-reveal">
                <span className="m-uc-status">
                  <span className="m-dot" />
                  Queued
                </span>
                <h3>Financial &amp; health ads</h3>
                <p>Unsubstantiated claims, guaranteed‑return language, missing required disclosures.</p>
                <div className="m-uc-tags">
                  <span>rules</span>
                  <span>classifier</span>
                </div>
              </div>
              <div className="m-usecase m-reveal">
                <span className="m-uc-status">
                  <span className="m-dot" />
                  Roadmap
                </span>
                <h3>Visual moderation</h3>
                <p>NSFW, violence, brand‑unsafe imagery, and manipulated media — the pipeline's rule/model split extended to pixels.</p>
                <div className="m-uc-tags">
                  <span>vision model</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="m-integrate" id="integrate">
          <div className="m-container">
            <div className="m-section-head m-reveal">
              <span className="m-eyebrow">PLUG AND PLAY</span>
              <h2>One endpoint in. A decision back.</h2>
            </div>
            <div className="m-integrate-grid">
              <div className="m-integrate-list">
                <div className="m-integrate-item m-reveal">
                  <span className="m-idx">01</span>
                  <div>
                    <h4>Submit</h4>
                    <p>POST whatever your users write. Modulus queues it for analysis and returns immediately.</p>
                  </div>
                </div>
                <div className="m-integrate-item m-reveal">
                  <span className="m-idx">02</span>
                  <div>
                    <h4>Get routed</h4>
                    <p>Seconds later, a webhook carries the routing decision, the score, and every flag with its evidence.</p>
                  </div>
                </div>
                <div className="m-integrate-item m-reveal">
                  <span className="m-idx">03</span>
                  <div>
                    <h4>Write policy, not code</h4>
                    <p>Thresholds and rule weights live in a versioned policy — tune them without a deploy.</p>
                  </div>
                </div>
              </div>
              <div className="m-code-panel m-reveal">
                <span className="m-c-muted">POST</span> /v1/submissions
                <br />
                {'{'}
                <br />
                &nbsp;&nbsp;<span className="m-c-key">"surface"</span>: <span className="m-c-str">"job_posting"</span>,
                <br />
                &nbsp;&nbsp;<span className="m-c-key">"title"</span>: <span className="m-c-str">"Remote Data Entry Specialist"</span>,
                <br />
                &nbsp;&nbsp;<span className="m-c-key">"description"</span>: <span className="m-c-str">"…"</span>
                <br />
                {'}'}
                <br />
                <br />
                <span className="m-c-muted">← 202</span> {'{ '}
                <span className="m-c-key">"id"</span>: <span className="m-c-str">"sub_8f2a"</span>,{' '}
                <span className="m-c-key">"status"</span>: <span className="m-c-str">"pending"</span> {'}'}
                <br />
                <br />
                <span className="m-c-muted">webhook →</span>
                <br />
                {'{'}
                <br />
                &nbsp;&nbsp;<span className="m-c-key">"routing"</span>: <span className="m-c-signal">"AUTO_REJECT"</span>,
                <br />
                &nbsp;&nbsp;<span className="m-c-key">"risk_score"</span>: 0.97,
                <br />
                &nbsp;&nbsp;<span className="m-c-key">"flags"</span>: [{'{ '}
                <span className="m-c-key">"category"</span>: <span className="m-c-str">"ADVANCE_FEE"</span>,{' '}
                <span className="m-c-key">"severity"</span>: <span className="m-c-str">"CRITICAL"</span> {'}'}]
                <br />
                {'}'}
              </div>
            </div>
          </div>
        </section>

        <section className="m-console">
          <div className="m-container">
            <div className="m-section-head m-reveal">
              <span className="m-eyebrow">FOR THE HUMAN IN THE LOOP</span>
              <h2>When it's ambiguous, moderators get a case file — not a blob of text.</h2>
              <p>
                Every case arrives pre‑reasoned: the posting with evidence highlighted in place, a
                flag list explaining why, and a decision panel — nothing to re‑derive.
              </p>
            </div>
            <div className="m-console-wrap m-reveal">
              <div className="m-console-bar">
                <span className="m-dot" />
                <span className="m-dot" />
                <span className="m-dot" />
                <span className="m-mono">moderator console — queue</span>
              </div>
              <div className="m-console-panes">
                <div className="m-console-pane">
                  <h5>Queue</h5>
                  <div className="m-cq-row">
                    <span>Sales Representative</span>
                    <span className="m-risk m-mono" style={{ color: 'var(--m-signal)' }}>
                      0.81
                    </span>
                  </div>
                  <div className="m-cq-row">
                    <span>Warehouse Associate</span>
                    <span className="m-risk m-mono" style={{ color: 'var(--m-clear)' }}>
                      0.12
                    </span>
                  </div>
                  <div className="m-cq-row">
                    <span>Data Entry Specialist</span>
                    <span className="m-risk m-mono" style={{ color: 'var(--m-critical)' }}>
                      0.97
                    </span>
                  </div>
                  <div className="m-cq-row" style={{ borderBottom: 'none' }}>
                    <span>Marketing Intern</span>
                    <span className="m-risk m-mono" style={{ color: 'var(--m-clear)' }}>
                      0.09
                    </span>
                  </div>
                </div>
                <div className="m-console-pane">
                  <h5>Flags — Sales Representative</h5>
                  <div className="m-flagcard">
                    <b>MLM_RECRUITMENT</b> · HIGH
                    <br />
                    downline, commission‑only, recruits
                  </div>
                  <div className="m-flagcard">
                    <b>DISCRIMINATORY</b> · HIGH
                    <br />
                    age &amp; citizenship stated as criteria
                  </div>
                </div>
                <div className="m-console-pane">
                  <h5>Decision</h5>
                  <div className="m-decision-btns">
                    <button className="m-btn m-btn-ghost" style={{ borderColor: 'var(--m-clear)', color: 'var(--m-clear)' }}>
                      Approve
                    </button>
                    <button className="m-btn m-btn-ghost" style={{ borderColor: 'var(--m-critical)', color: 'var(--m-critical)' }}>
                      Reject
                    </button>
                    <button className="m-btn m-btn-ghost">Request changes</button>
                    <button className="m-btn m-btn-ghost">Escalate</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="m-cta" id="cta">
          <div className="m-container m-cta-box">
            <div>
              <span className="m-eyebrow">GET STARTED</span>
              <h2>Bring your policy. We'll bring the pipeline.</h2>
              <p>Job board postings are live today. Sign up and post your first listing in minutes.</p>
            </div>
            <div className="m-cta-actions">
              <Link to={authed ? dashboardPath : '/signup'} className="m-btn m-btn-solid m-btn-lg">
                {authed ? 'Go to dashboard' : 'Create free account'}
              </Link>
              {!authed && (
                <div className="m-cta-note">
                  Already have an account? <Link to="/login" style={{ color: '#ff9a5a' }}>Log in</Link>
                </div>
              )}
            </div>
          </div>
        </section>
      </main>

      <footer className="m-footer">
        <div className="m-container m-footer-row">
          <Link to="/" className="m-wordmark">
            <span className="m-bar">|</span>MODULUS<span className="m-bar">|</span>
          </Link>
          <ul className="m-footer-links">
            <li>
              <a href="#how-it-works">How it works</a>
            </li>
            <li>
              <a href="#use-cases">Use cases</a>
            </li>
            <li>
              <a href="#integrate">Integrate</a>
            </li>
          </ul>
          <span className="m-mono">engine v1 · job_postings taxonomy · 11 categories</span>
        </div>
      </footer>
    </div>
  )
}
