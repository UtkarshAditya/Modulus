import re

from apps.moderation.engine.normalize import NormalizedDoc


def test_html_is_stripped_and_content_offsets_stay_correct():
    doc = NormalizedDoc("<p>Hello <b>world</b></p>")
    assert doc.folded == "hello world"
    span = doc.folded_span_to_original(*re.search("world", doc.folded).span())
    assert doc.original_text(span) == "world"


def test_whitespace_is_collapsed_and_trimmed():
    doc = NormalizedDoc("  Hello    world  \n\tagain  ")
    assert doc.folded == "hello world again"


def test_zero_width_characters_are_dropped():
    doc = NormalizedDoc("whats​app")
    assert doc.folded == "whatsapp"


def test_folded_span_maps_back_to_exact_original_substring():
    original = "Please contact HR about the ROLE today."
    doc = NormalizedDoc(original)
    match = re.search("role", doc.folded)
    span = doc.folded_span_to_original(*match.span())
    assert doc.original_text(span) == "ROLE"


def test_collapsed_view_catches_separator_inserted_evasion():
    doc = NormalizedDoc("reach us on t.e.l.e.g.r.a.m please")
    assert "telegram" in doc.collapsed
    idx = doc.collapsed.index("telegram")
    span = doc.collapsed_span_to_original(idx, idx + len("telegram"))
    assert doc.original_text(span) == "t.e.l.e.g.r.a.m"


def test_collapsed_view_catches_leetspeak_evasion():
    doc = NormalizedDoc("message us on wh@tsapp now")
    assert "whatsapp" in doc.collapsed
    idx = doc.collapsed.index("whatsapp")
    span = doc.collapsed_span_to_original(idx, idx + len("whatsapp"))
    assert doc.original_text(span) == "wh@tsapp"


def test_collapsed_view_does_not_false_positive_on_unrelated_text():
    doc = NormalizedDoc("We offer a great work environment and benefits.")
    assert "whatsapp" not in doc.collapsed
    assert "telegram" not in doc.collapsed


def test_combine_preserves_offsets_across_joined_fields():
    doc = NormalizedDoc.combine("Great Title", "Body mentions WhatsApp contact.")
    idx = doc.folded.index("whatsapp")
    span = doc.folded_span_to_original(idx, idx + len("whatsapp"))
    assert doc.original_text(span) == "WhatsApp"
