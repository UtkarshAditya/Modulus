"""Text normalization for the rules engine.

Produces two views of a submission's text, each carrying an offset map back
to the original string so that a rule match — however it was found — can be
reported as an evidence span against what the moderator actually sees:

- `folded`: NFKC-folded, lowercased, zero-width-stripped, HTML-stripped,
  whitespace-collapsed. Used by most rules; word-boundary regexes on this
  view still line up with real words in the original text.
- `collapsed`: `folded` with every remaining non-alphanumeric character
  removed. Used by rules that need to survive an evader inserting
  separators between letters (`wh@tsapp`, `t.e.l.e.g.r.a.m`,
  `w h a t s a p p`) — a fixed keyword becomes a plain substring search.

Both views expose `*_span_to_original`, which is the piece that matters:
without it, "de-obfuscate the text" and "highlight what the moderator sees"
are in tension, since the de-obfuscated text isn't what's on screen.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

_ZERO_WIDTH = {
    chr(0x200B),  # zero width space
    chr(0x200C),  # zero width non-joiner
    chr(0x200D),  # zero width joiner
    chr(0xFEFF),  # BOM / zero width no-break space
    chr(0x2060),  # word joiner
}


@dataclass(frozen=True)
class Span:
    start: int
    end: int


def _strip_html(text: str) -> tuple[str, list[int]]:
    """Drop tags, keep content 1:1 so offsets stay trivial."""
    out_chars: list[str] = []
    offsets: list[int] = []
    in_tag = False
    for i, ch in enumerate(text):
        if ch == "<":
            in_tag = True
            continue
        if ch == ">":
            in_tag = False
            continue
        if in_tag:
            continue
        out_chars.append(ch)
        offsets.append(i)
    return "".join(out_chars), offsets


def _fold(text: str, offsets_in: list[int]) -> tuple[str, list[int]]:
    """NFKC + lowercase + zero-width strip, char by char so offsets stay exact."""
    out_chars: list[str] = []
    offsets: list[int] = []
    for i, ch in enumerate(text):
        if ch in _ZERO_WIDTH:
            continue
        for out_ch in unicodedata.normalize("NFKC", ch).lower():
            out_chars.append(out_ch)
            offsets.append(offsets_in[i])
    return "".join(out_chars), offsets


def _collapse_whitespace(text: str, offsets_in: list[int]) -> tuple[str, list[int]]:
    out_chars: list[str] = []
    offsets: list[int] = []
    prev_was_space = False
    for ch, off in zip(text, offsets_in, strict=False):
        is_space = ch.isspace()
        if is_space:
            ch = " "
            if prev_was_space:
                continue
        out_chars.append(ch)
        offsets.append(off)
        prev_was_space = is_space
    while out_chars and out_chars[0] == " ":
        out_chars.pop(0)
        offsets.pop(0)
    while out_chars and out_chars[-1] == " ":
        out_chars.pop()
        offsets.pop()
    return "".join(out_chars), offsets


_LEET_MAP = {
    "@": "a",
    "4": "a",
    "3": "e",
    "1": "l",
    "!": "i",
    "0": "o",
    "$": "s",
    "5": "s",
    "7": "t",
    "+": "t",
}


def _leet_substitute(text: str, offsets_in: list[int]) -> tuple[str, list[int]]:
    """Map common leetspeak substitutions (`wh@tsapp`, `t3legram`) back to
    letters. Only feeds the `collapsed` view — folding these into the main
    `folded` view would make ordinary word-boundary rules match inside
    numbers and prices, which is not worth the trade.
    """
    out_chars = [_LEET_MAP.get(ch, ch) for ch in text]
    return "".join(out_chars), list(offsets_in)


def _strip_non_alnum(text: str, offsets_in: list[int]) -> tuple[str, list[int]]:
    out_chars: list[str] = []
    offsets: list[int] = []
    for ch, off in zip(text, offsets_in, strict=False):
        if ch.isalnum():
            out_chars.append(ch)
            offsets.append(off)
    return "".join(out_chars), offsets


class NormalizedDoc:
    """A submission's text plus both normalized views, each able to map a
    match span in that view back to a span in the original text.
    """

    def __init__(self, original: str):
        self.original = original

        no_html, offsets = _strip_html(original)
        folded, offsets = _fold(no_html, offsets)
        folded, offsets = _collapse_whitespace(folded, offsets)
        self.folded = folded
        self._folded_offsets = offsets

        leet, leet_offsets = _leet_substitute(folded, offsets)
        collapsed, collapsed_offsets = _strip_non_alnum(leet, leet_offsets)
        self.collapsed = collapsed
        self._collapsed_offsets = collapsed_offsets

    def _to_original(self, offsets: list[int], start: int, end: int) -> Span:
        if not offsets:
            return Span(0, 0)
        if start >= end:
            idx = offsets[min(start, len(offsets) - 1)]
            return Span(idx, idx)
        orig_start = offsets[start]
        orig_end = offsets[end - 1] + 1
        return Span(orig_start, orig_end)

    def folded_span_to_original(self, start: int, end: int) -> Span:
        return self._to_original(self._folded_offsets, start, end)

    def collapsed_span_to_original(self, start: int, end: int) -> Span:
        return self._to_original(self._collapsed_offsets, start, end)

    def original_text(self, span: Span) -> str:
        return self.original[span.start : span.end]

    @classmethod
    def combine(cls, *parts: str, joiner: str = "\n") -> NormalizedDoc:
        """Build a doc from several fields (e.g. title + description) while
        keeping evidence spans valid against `joiner.join(parts)` as the
        "original" text.
        """
        return cls(joiner.join(parts))
