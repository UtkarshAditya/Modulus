"""Golden-corpus tests for the job-board rule pack: every rule gets a
positive case (should flag), a negative case (should not — the false
positive risk that matters most for the CRITICAL/HIGH categories), and,
where the rule reads text, an evasion case (an obfuscated positive that
should still flag, with evidence mapping back to the real substring).
"""

from types import SimpleNamespace

import pytest

from apps.moderation.engine.normalize import NormalizedDoc
from apps.moderation.engine.rules.base import Category
from apps.moderation.engine.rules.packs import jobs as rule_pack


def make_submission(**overrides) -> SimpleNamespace:
    defaults = dict(
        title="Software Engineer",
        description="We are looking for an experienced engineer to join our team.",
        company_name="Acme Co",
        salary_min=80_000,
        salary_max=120_000,
        salary_disclosed=True,
        apply_url="https://example.com/apply",
        contact_email="hiring@example.com",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def run_rule(rule, submission) -> list:
    doc = NormalizedDoc.combine(submission.title, submission.description)
    return rule.evaluate(submission, doc)


def assert_category(hits, category: Category):
    assert any(h.category == category for h in hits), f"expected a {category} hit, got {hits}"


def assert_no_category(hits, category: Category):
    assert not any(h.category == category for h in hits), f"unexpected {category} hit: {hits}"


# --- ADVANCE_FEE -------------------------------------------------------


def test_advance_fee_positive():
    rule = rule_pack.AdvanceFeeRule()
    sub = make_submission(
        description="Please pay a refundable deposit of $50 to secure your starter kit before you start."
    )
    hits = run_rule(rule, sub)
    assert_category(hits, Category.ADVANCE_FEE)
    span = hits[0].evidence[0]
    assert "deposit" in span.text.lower()


def test_advance_fee_negative():
    rule = rule_pack.AdvanceFeeRule()
    sub = make_submission(description="Salary is paid biweekly via direct deposit.")
    assert run_rule(rule, sub) == []


def test_advance_fee_evasion_html_split_and_irregular_whitespace():
    """HTML tags injected mid-phrase and irregular whitespace/case are a
    real evasion technique against naive substring search — `folded`
    strips tags and collapses whitespace, so the phrase should still read
    as one continuous match.
    """
    rule = rule_pack.AdvanceFeeRule()
    sub = make_submission(
        description="Please pay a <b>REFUNDABLE</b>   \n  DEPOSIT before you   start."
    )
    hits = run_rule(rule, sub)
    assert_category(hits, Category.ADVANCE_FEE)


# --- PII_HARVEST ---------------------------------------------------------


def test_pii_harvest_positive():
    rule = rule_pack.PiiHarvestRule()
    sub = make_submission(
        description="To get started, please send us your social security number and bank account."
    )
    hits = run_rule(rule, sub)
    assert_category(hits, Category.PII_HARVEST)


def test_pii_harvest_negative():
    rule = rule_pack.PiiHarvestRule()
    sub = make_submission(
        description="We'll ask for your ID during onboarding, after an offer is signed."
    )
    assert run_rule(rule, sub) == []


def test_pii_harvest_evasion_zero_width_and_html():
    zero_width_space = chr(0x200B)
    description = f"Please <i>send</i> your soc{zero_width_space}ial security number today."
    rule = rule_pack.PiiHarvestRule()
    sub = make_submission(description=description)
    hits = run_rule(rule, sub)
    assert_category(hits, Category.PII_HARVEST)


# --- ILLEGAL_WORK ----------------------------------------------------------


def test_illegal_work_positive():
    rule = rule_pack.IllegalWorkRule()
    sub = make_submission(description="Cash in hand, no taxes, no questions asked.")
    hits = run_rule(rule, sub)
    assert_category(hits, Category.ILLEGAL_WORK)


def test_illegal_work_negative():
    rule = rule_pack.IllegalWorkRule()
    sub = make_submission(
        description="All employees are paid on payroll with full tax withholding."
    )
    assert run_rule(rule, sub) == []


def test_illegal_work_evasion_case_and_whitespace():
    rule = rule_pack.IllegalWorkRule()
    sub = make_submission(description="Paid   UNDER   THE   TABLE, no experience required.")
    hits = run_rule(rule, sub)
    assert_category(hits, Category.ILLEGAL_WORK)


# --- MLM_RECRUITMENT ---------------------------------------------------


def test_mlm_recruitment_positive():
    rule = rule_pack.MlmRecruitmentRule()
    sub = make_submission(
        description="Be your own boss! Recruit your team and grow your downline for unlimited earning potential."
    )
    hits = run_rule(rule, sub)
    assert_category(hits, Category.MLM_RECRUITMENT)


def test_mlm_recruitment_negative():
    rule = rule_pack.MlmRecruitmentRule()
    sub = make_submission(
        description="You'll report to the sales director and manage a small account list."
    )
    assert run_rule(rule, sub) == []


def test_mlm_recruitment_evasion_html_split_across_the_trigger_phrase():
    rule = rule_pack.MlmRecruitmentRule()
    sub = make_submission(
        description="Build your <b>downline</b> and unlock <em>unlimited earning potential</em>."
    )
    hits = run_rule(rule, sub)
    assert_category(hits, Category.MLM_RECRUITMENT)


# --- OFF_PLATFORM_REDIRECT ------------------------------------------------


def test_off_platform_redirect_positive():
    rule = rule_pack.OffPlatformRedirectRule()
    sub = make_submission(
        description="Interested? Message us on WhatsApp to schedule an interview."
    )
    hits = run_rule(rule, sub)
    assert_category(hits, Category.OFF_PLATFORM_REDIRECT)


def test_off_platform_redirect_negative():
    rule = rule_pack.OffPlatformRedirectRule()
    sub = make_submission(
        description="Apply through the link above and our recruiting team will follow up."
    )
    assert run_rule(rule, sub) == []


def test_off_platform_redirect_evasion_leetspeak():
    rule = rule_pack.OffPlatformRedirectRule()
    sub = make_submission(description="Contact us on wh@tsapp for a quick chat.")
    hits = run_rule(rule, sub)
    assert_category(hits, Category.OFF_PLATFORM_REDIRECT)
    evidence_text = hits[0].evidence[0].text
    assert evidence_text == "wh@tsapp"


def test_off_platform_redirect_evasion_separators():
    rule = rule_pack.OffPlatformRedirectRule()
    sub = make_submission(description="Reach out via t.e.l.e.g.r.a.m once you've applied.")
    hits = run_rule(rule, sub)
    assert_category(hits, Category.OFF_PLATFORM_REDIRECT)
    evidence_text = hits[0].evidence[0].text
    assert evidence_text == "t.e.l.e.g.r.a.m"


# --- DISCRIMINATORY ---------------------------------------------------


def test_discriminatory_positive():
    rule = rule_pack.DiscriminatoryRule()
    sub = make_submission(
        description="We prefer male candidates for this physically demanding role."
    )
    hits = run_rule(rule, sub)
    assert_category(hits, Category.DISCRIMINATORY)


def test_discriminatory_negative():
    rule = rule_pack.DiscriminatoryRule()
    sub = make_submission(
        description="We are an equal opportunity employer and welcome all applicants."
    )
    assert run_rule(rule, sub) == []


def test_discriminatory_evasion_irregular_whitespace_and_case():
    rule = rule_pack.DiscriminatoryRule()
    sub = make_submission(description="Applicants   MUST BE   UNDER 30   years old.")
    hits = run_rule(rule, sub)
    assert_category(hits, Category.DISCRIMINATORY)


# --- MISLEADING_COMP (field-based, no text evasion) -----------------------


def test_misleading_comp_contradictory_range():
    rule = rule_pack.MisleadingCompRule()
    sub = make_submission(salary_min=90_000, salary_max=60_000)
    hits = run_rule(rule, sub)
    assert_category(hits, Category.MISLEADING_COMP)


def test_misleading_comp_implausible_spread():
    rule = rule_pack.MisleadingCompRule()
    sub = make_submission(salary_min=1_000, salary_max=500_000)
    hits = run_rule(rule, sub)
    assert_category(hits, Category.MISLEADING_COMP)


def test_misleading_comp_negative():
    rule = rule_pack.MisleadingCompRule()
    sub = make_submission(salary_min=80_000, salary_max=120_000)
    assert run_rule(rule, sub) == []


# --- NO_COMP_DISCLOSURE (field-based) -----------------------------------


def test_no_comp_disclosure_positive():
    rule = rule_pack.NoCompDisclosureRule()
    sub = make_submission(salary_min=None, salary_max=None, salary_disclosed=False)
    hits = run_rule(rule, sub)
    assert_category(hits, Category.NO_COMP_DISCLOSURE)


def test_no_comp_disclosure_negative_when_disclosed():
    rule = rule_pack.NoCompDisclosureRule()
    sub = make_submission(salary_min=80_000, salary_max=120_000, salary_disclosed=True)
    assert run_rule(rule, sub) == []


# --- KEYWORD_STUFFING (statistical) --------------------------------------


def test_keyword_stuffing_positive():
    rule = rule_pack.KeywordStuffingRule()
    stuffed = " ".join(["urgent"] * 10 + ["hiring", "now", "apply", "today"])
    sub = make_submission(title="Urgent urgent urgent", description=stuffed)
    hits = run_rule(rule, sub)
    assert_category(hits, Category.KEYWORD_STUFFING)


def test_keyword_stuffing_negative_on_normal_description():
    rule = rule_pack.KeywordStuffingRule()
    sub = make_submission(
        description=(
            "We are looking for a product manager to own our checkout experience, "
            "work closely with engineering and design, and ship improvements every sprint."
        )
    )
    assert run_rule(rule, sub) == []


# --- run_rules end to end ------------------------------------------------


def test_run_rules_skips_disabled_rules():
    from apps.moderation.engine.rules.base import RuleConfig, run_rules

    sub = make_submission(
        description="Please pay a refundable deposit of $50 to secure your starter kit before you start."
    )
    doc = NormalizedDoc.combine(sub.title, sub.description)

    all_hits = run_rules(rule_pack.JOB_RULES, sub, doc)
    assert_category(all_hits, Category.ADVANCE_FEE)

    disabled_hits = run_rules(
        rule_pack.JOB_RULES,
        sub,
        doc,
        rule_config={"job.advance_fee": RuleConfig(enabled=False)},
    )
    assert_no_category(disabled_hits, Category.ADVANCE_FEE)


@pytest.mark.parametrize("rule", rule_pack.JOB_RULES, ids=lambda r: r.id)
def test_every_rule_is_quiet_on_a_boring_clean_posting(rule):
    """A single, deliberately unremarkable posting should not trip any
    rule — the cheapest possible guard against an over-eager pattern.
    """
    sub = make_submission()
    hits = run_rule(rule, sub)
    assert hits == [], f"{rule.id} incorrectly flagged a clean posting: {hits}"
