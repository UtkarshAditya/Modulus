"""Generates backend/ml/data/seed.jsonl — the labelled seed corpus for the
classifier (Phase 3).

Deliberately synthetic and templated, not hand-labelled by a real reviewer.
That's a known, documented limitation, not an oversight: it's a bootstrap
dataset meant to get a first model trained and the pipeline end to end, and
to be progressively replaced by real moderator decisions through the
feedback loop described in docs/PLAN.md. The phrasings here are written to
paraphrase the underlying scam/exclusion patterns rather than reuse the
literal regex wording from the Phase 2 rule pack — the point of the model
is to generalize past what a fixed pattern catches, so training it on the
rules' own vocabulary would defeat the purpose.

Run with: python ml/data/generate_seed_corpus.py

Only four categories get a label here — ADVANCE_FEE, PII_HARVEST,
OFF_PLATFORM_REDIRECT, MISLEADING_COMP, NO_COMP_DISCLOSURE, KEYWORD_STUFFING,
and SPAM_DUPLICATE are rule/dedupe categories per the taxonomy in
docs/PLAN.md and don't need classifier training data.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

RNG_SEED = 20260101
OUTPUT_PATH = Path(__file__).parent / "seed.jsonl"

# --- category trigger phrases -----------------------------------------------
# Paraphrased, not lifted from the Phase 2 regexes — see module docstring.

ILLEGAL_WORK_PHRASES = [
    "You'll be paid in cash every week, no paperwork involved.",
    "We don't issue 1099s or W-2s here, just cash at the end of each shift.",
    "No ID or work authorization needed — we don't ask questions.",
    "Payment is handled informally and never goes through official channels.",
    "This role is fully unofficial, so there's no tax reporting on our end.",
    "We keep everything off the record for tax purposes.",
    "You'll receive your earnings hand to hand, no bank transfers or records.",
    "Immigration status doesn't matter, we don't verify anything.",
    "All compensation here is informal and untraceable.",
    "This is a cash-only arrangement outside the usual employment rules.",
    "We pay under a different name than the one on the job, so it never shows up anywhere.",
    "No contracts, no tax forms, just an agreement between us.",
    "Everything here stays private and off any government system.",
    "We'll never ask for a social security number since this isn't on the books.",
]

MLM_RECRUITMENT_PHRASES = [
    "Grow your income by bringing new people into our network.",
    "The more people you sign up under you, the more you earn.",
    "This is a business opportunity, not a traditional job — you invest in a starter package "
    "and start earning as you build your team.",
    "Success here depends on how large a team you can build beneath you.",
    "You'll earn commissions not just from your own sales but from everyone you bring in.",
    "Financial freedom comes from expanding your network of representatives.",
    "Ground floor opportunity — get in early and build your organization.",
    "No boss, no ceiling, just you, your hustle, and your growing team.",
    "We're looking for people to join our distributor network and recruit others.",
    "Passive income comes from building layers of team members beneath you.",
    "Bring three friends on board and your membership pays for itself.",
    "Your income potential is tied directly to the size of the team you build.",
    "This opportunity rewards you for every new recruit who joins your downline.",
]

DISCRIMINATORY_PHRASES = [
    "Looking for young, energetic guys for this role.",
    "This position suits someone without family obligations who can travel anytime.",
    "We're seeking someone from a Christian background who shares our values.",
    "Ideal candidate is a fit, single woman under 25.",
    "We prefer candidates without children given the demanding schedule.",
    "Native English speakers of European descent preferred.",
    "Looking for a young man to represent our brand at events.",
    "Please note this role is not really suitable for older applicants.",
    "We are seeking a clean-cut, unmarried candidate for client-facing work.",
    "Only applicants who are physically fit and clearly under 35 will be considered.",
    "This role is best suited to someone early in life, not looking to start a family soon.",
    "We're building a young team and looking for people who fit that energy.",
]

GHOST_JOB_PHRASES = [
    "Amazing opportunity! Join our growing team today! Flexible schedule, great pay, immediate start!",
    "We are hiring! No experience needed, just a great attitude! Apply now!",
    "Exciting career opportunity with unlimited potential! Don't miss out!",
    "Now hiring motivated individuals for a rewarding opportunity! Get started today!",
    "Join a fast-growing organization! Great culture, great people, great pay!",
    "Multiple positions available now! Fast hiring process! Start this week!",
    "Be part of something big! We're expanding and need people like you!",
    "Work with a dynamic team on exciting projects! Apply within!",
    "Great opportunity for driven individuals! Unlimited growth potential!",
    "Hiring now! Competitive pay! Flexible hours! Apply immediately!",
    "We're on the lookout for great people to join our exciting journey!",
    "Huge opportunity for the right person! Don't wait, apply today!",
]

GHOST_JOB_COMPANY_NAMES = [
    "A Leading Company", "Confidential Employer", "Growing Organization",
    "Premier Enterprises", "A Top Company", "Leading Industry Employer",
]  # fmt: skip

# --- filler / wrapper text, so a trigger phrase reads like a real posting --

INTRO_TEMPLATES = [
    "We're hiring a {role} to join our team.",
    "{company} is looking for a {role}.",
    "Join {company} as our next {role}.",
    "{company} has an opening for a {role} starting immediately.",
    "We need a {role} to start right away.",
]

CLOSER_TEMPLATES = [
    "Apply today to get started.",
    "Reach out if you're interested.",
    "We're moving fast on this one.",
    "Let us know if you'd like to learn more.",
    "",
]

ROLES = [
    "sales associate", "delivery driver", "customer service rep", "warehouse associate",
    "administrative assistant", "field agent", "brand ambassador", "data entry clerk",
    "marketing associate", "account representative", "team member", "coordinator",
]  # fmt: skip

COMPANIES = [
    "Northwind Traders", "Bright Horizons Marketing", "Silverline Logistics", "Crestview Retail",
    "Harborview Group", "Meridian Solutions", "Oakfield Partners", "Riverside Holdings",
    "Summit Ventures", "Lakeside Enterprises", "Cobalt Distribution", "Ashford Brands",
]  # fmt: skip

# --- clean / negative postings ---------------------------------------------

CLEAN_ROLE_BANK = [
    (
        "Backend Engineer",
        "engineering",
        [
            "5+ years of experience with Python or Go.",
            "You'll own services that process millions of requests a day.",
            "Experience with PostgreSQL and distributed systems is a plus.",
        ],
    ),
    (
        "Product Designer",
        "design",
        [
            "A portfolio showing end-to-end product design work.",
            "You'll partner closely with engineering and product management.",
            "Experience with Figma and design systems preferred.",
        ],
    ),
    (
        "Registered Nurse",
        "healthcare",
        [
            "Active RN license in good standing required.",
            "You'll provide direct patient care on our medical-surgical unit.",
            "Prior acute care experience preferred but not required.",
        ],
    ),
    (
        "High School Math Teacher",
        "education",
        [
            "State teaching certification in mathematics required.",
            "You'll teach Algebra II and pre-calculus to grades 10-11.",
            "Experience with project-based learning is a plus.",
        ],
    ),
    (
        "Accountant",
        "finance",
        [
            "CPA or progress toward CPA preferred.",
            "You'll manage month-end close and reconcile general ledger accounts.",
            "Experience with QuickBooks or NetSuite a plus.",
        ],
    ),
    (
        "Warehouse Supervisor",
        "logistics",
        [
            "2+ years supervising a warehouse or distribution team.",
            "You'll manage a team of 10-15 associates across two shifts.",
            "Forklift certification preferred.",
        ],
    ),
    (
        "Marketing Manager",
        "marketing",
        [
            "5+ years running integrated marketing campaigns.",
            "You'll own our paid acquisition strategy across channels.",
            "Experience with HubSpot or similar platforms preferred.",
        ],
    ),
    (
        "Electrician",
        "trades",
        [
            "Journeyman electrician license required.",
            "You'll handle residential and light commercial installations.",
            "Own transportation and tools required.",
        ],
    ),
    (
        "Executive Assistant",
        "administrative",
        [
            "3+ years supporting C-level executives.",
            "You'll manage complex calendars and coordinate travel.",
            "Excellent written and verbal communication skills required.",
        ],
    ),
    (
        "Restaurant Shift Manager",
        "hospitality",
        [
            "2+ years of restaurant management experience.",
            "You'll oversee daily operations during your assigned shift.",
            "Food safety certification required within 30 days of hire.",
        ],
    ),
    (
        "Customer Support Specialist",
        "customer service",
        [
            "1+ years in a customer-facing support role.",
            "You'll resolve tickets via chat and email within SLA.",
            "Experience with Zendesk or similar tools a plus.",
        ],
    ),
    (
        "Civil Engineer",
        "engineering",
        [
            "PE license or actively pursuing one.",
            "You'll design site plans for commercial developments.",
            "Experience with AutoCAD Civil 3D preferred.",
        ],
    ),
    (
        "HR Generalist",
        "human resources",
        [
            "3+ years of HR generalist experience.",
            "You'll support recruiting, onboarding, and employee relations.",
            "SHRM certification a plus.",
        ],
    ),
    (
        "Paralegal",
        "legal",
        [
            "Paralegal certificate or equivalent experience.",
            "You'll support litigation attorneys with case preparation.",
            "Experience with e-discovery tools preferred.",
        ],
    ),
    (
        "Social Media Coordinator",
        "marketing",
        [
            "1-2 years managing brand social accounts.",
            "You'll plan and publish content across Instagram, TikTok, and X.",
            "A strong eye for visual storytelling is a must.",
        ],
    ),
    (
        "Machine Operator",
        "manufacturing",
        [
            "1+ years operating CNC or similar equipment.",
            "You'll run production on our second shift line.",
            "Manufacturing safety training provided on hire.",
        ],
    ),
    (
        "IT Support Technician",
        "IT",
        [
            "2+ years of helpdesk or desktop support experience.",
            "You'll troubleshoot hardware, software, and network issues on-site.",
            "A+ or similar certification a plus.",
        ],
    ),
    (
        "Veterinary Technician",
        "healthcare",
        [
            "Licensed veterinary technician certification required.",
            "You'll assist with exams, surgery prep, and patient monitoring.",
            "Experience with small animal practice preferred.",
        ],
    ),
]

CLEAN_INTRO_TEMPLATES = [
    "{company} is hiring a {role} to join our {industry} team in {location}.",
    "We're looking for an experienced {role} to join {company}.",
    "{company} has an opening for a {role} on our {industry} team.",
]

LOCATIONS = [
    "Austin, TX", "Remote", "Chicago, IL", "Denver, CO", "Seattle, WA",
    "Atlanta, GA", "Boston, MA", "Portland, OR", "Raleigh, NC", "Remote (US)",
]  # fmt: skip

CLEAN_BENEFITS = [
    "We offer medical, dental, and vision coverage plus a 401(k) match.",
    "Benefits include health insurance, paid time off, and a hybrid schedule.",
    "We offer competitive pay, health benefits, and professional development budget.",
    "Full benefits package including health insurance and paid parental leave.",
]


def _rng() -> random.Random:
    return random.Random(RNG_SEED)


def _make_posting(title, company, description, labels, salary=True) -> dict:
    return {
        "title": title,
        "description": description,
        "company_name": company,
        "salary_min": 45_000 if salary else None,
        "salary_max": 85_000 if salary else None,
        "salary_disclosed": salary,
        "labels": labels,
    }


def _generate_category_examples(
    rng: random.Random, phrases: list[str], category: str, target: int
) -> list[dict]:
    examples = []
    combos = [(p, role, company) for p in phrases for role in ROLES for company in COMPANIES]
    rng.shuffle(combos)
    for phrase, role, company in combos[:target]:
        intro = rng.choice(INTRO_TEMPLATES).format(role=role, company=company)
        closer = rng.choice(CLOSER_TEMPLATES)
        description = " ".join(filter(None, [intro, phrase, closer]))
        examples.append(
            _make_posting(role.title(), company, description, [category], salary=rng.random() > 0.4)
        )
    return examples


def _generate_ghost_job_examples(rng: random.Random, target: int) -> list[dict]:
    examples = []
    combos = [(p, role) for p in GHOST_JOB_PHRASES for role in ROLES]
    rng.shuffle(combos)
    for phrase, role in combos[:target]:
        company = rng.choice(GHOST_JOB_COMPANY_NAMES)
        second_phrase = rng.choice([p for p in GHOST_JOB_PHRASES if p != phrase])
        description = f"{phrase} {second_phrase}"
        examples.append(
            _make_posting(role.title(), company, description, ["GHOST_JOB"], salary=False)
        )
    return examples


def _generate_multilabel_examples(rng: random.Random, target: int) -> list[dict]:
    """A smaller slice of postings combining two categories, so the
    multilabel classifier sees co-occurring labels during training, not
    just single-category examples.
    """
    pairs = [
        (MLM_RECRUITMENT_PHRASES, "MLM_RECRUITMENT", GHOST_JOB_PHRASES, "GHOST_JOB"),
        (ILLEGAL_WORK_PHRASES, "ILLEGAL_WORK", GHOST_JOB_PHRASES, "GHOST_JOB"),
        (DISCRIMINATORY_PHRASES, "DISCRIMINATORY", MLM_RECRUITMENT_PHRASES, "MLM_RECRUITMENT"),
    ]
    examples = []
    for _ in range(target):
        phrases_a, cat_a, phrases_b, cat_b = rng.choice(pairs)
        role = rng.choice(ROLES)
        company = rng.choice(COMPANIES + GHOST_JOB_COMPANY_NAMES)
        intro = rng.choice(INTRO_TEMPLATES).format(role=role, company=company)
        description = " ".join([intro, rng.choice(phrases_a), rng.choice(phrases_b)])
        examples.append(
            _make_posting(role.title(), company, description, [cat_a, cat_b], salary=False)
        )
    return examples


def _generate_clean_examples(rng: random.Random, target: int) -> list[dict]:
    examples = []
    combos = [
        (title, industry, detail)
        for title, industry, details in CLEAN_ROLE_BANK
        for detail in details
    ]
    rng.shuffle(combos)
    # cycle through if target exceeds the base combo count
    while len(combos) < target:
        combos.extend(combos)
    for title, industry, detail in combos[:target]:
        company = rng.choice(COMPANIES)
        location = rng.choice(LOCATIONS)
        intro = rng.choice(CLEAN_INTRO_TEMPLATES).format(
            company=company, role=title, industry=industry, location=location
        )
        benefits = rng.choice(CLEAN_BENEFITS)
        description = " ".join([intro, detail, benefits])
        examples.append(_make_posting(title, company, description, [], salary=True))
    return examples


def generate() -> list[dict]:
    rng = _rng()
    examples: list[dict] = []
    examples += _generate_category_examples(rng, ILLEGAL_WORK_PHRASES, "ILLEGAL_WORK", 45)
    examples += _generate_category_examples(rng, MLM_RECRUITMENT_PHRASES, "MLM_RECRUITMENT", 45)
    examples += _generate_category_examples(rng, DISCRIMINATORY_PHRASES, "DISCRIMINATORY", 45)
    examples += _generate_ghost_job_examples(rng, 40)
    examples += _generate_multilabel_examples(rng, 25)
    examples += _generate_clean_examples(rng, 170)
    rng.shuffle(examples)
    return examples


def main():
    examples = generate()
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    counts = {}
    for ex in examples:
        for label in ex["labels"] or ["<clean>"]:
            counts[label] = counts.get(label, 0) + 1
    print(f"Wrote {len(examples)} examples to {OUTPUT_PATH}")
    for label, count in sorted(counts.items()):
        print(f"  {label}: {count}")


if __name__ == "__main__":
    main()
