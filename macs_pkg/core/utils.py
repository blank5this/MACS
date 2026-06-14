"""Shared utilities for agent implementations.

Currently exposes JSON-parsing helpers that tolerate the common shapes
LLMs return content in (markdown-fenced JSON, trailing prose, plain text).

Centralising these helpers means every role agent (planner/executor/
reviewer/tool) handles malformed responses the same way.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional, Union

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging
    logger = logging.getLogger("core.utils")


JsonValue = Union[dict, list]


def _strip_markdown_fence(content: str) -> str:
    """Remove a surrounding ```json ... ``` or ``` ... ``` fence if present."""
    s = content.strip()
    if not s.startswith("```"):
        return s
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def extract_json(content: str) -> Optional[JsonValue]:
    """Try hard to recover a dict/list from an LLM response.

    Strategy (in order):
      1. Strip whitespace + any ```json``` markdown fence.
      2. ``json.loads`` directly.
      3. Take the substring from the first ``{`` / ``[`` to the last matching
         ``}`` / ``]`` and ``json.loads`` that. Lets us salvage JSON when the
         model wrapped it in prose like "Here's the answer: { ... } Hope this
         helps!".

    Returns the parsed object on success, ``None`` on failure. Never raises.
    Failures are logged at ``warning`` level — callers should fall back.
    """
    if not content:
        return None

    s = _strip_markdown_fence(content)
    if not s:
        return None

    # 1) direct parse
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 2) substring extraction — pick the broadest bracket span we can find
    candidates = []
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = s.find(open_ch)
        end = s.rfind(close_ch)
        if start != -1 and end > start:
            candidates.append(s[start : end + 1])

    for snippet in candidates:
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            continue

    logger.warning(
        "extract_json: could not parse content as JSON "
        f"(first 80 chars: {s[:80]!r})"
    )
    return None


def parse_json_content(
    content: str,
    *,
    plain_text_key: str = "final_output",
) -> dict:
    """Parse an LLM response as a dict, degrading gracefully.

    On success — returns the parsed dict (or wraps a parsed list in
    ``{plain_text_key: [...]}``).
    On failure — returns ``{plain_text_key: content_stripped}`` so the caller
    still gets the model's text output instead of an empty dict.

    Use this when the caller really needs a dict and JSON is the *preferred*
    but not *required* format. Use :func:`extract_json` when you'd rather get
    ``None`` and pick your own fallback.
    """
    if not content:
        return {plain_text_key: ""}

    parsed = extract_json(content)
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        return {plain_text_key: parsed}

    logger.debug("parse_json_content: response not JSON, returning as plain text")
    return {plain_text_key: _strip_markdown_fence(content)}


__all__ = ["extract_json", "parse_json_content"]
