"""Explicit trust labels for model-visible context."""

from __future__ import annotations


def partition_observation(observation: str) -> str:
    elements_marker = "Elements:\n"
    text_marker = "\n\nVisible text:\n"
    if elements_marker not in observation or text_marker not in observation:
        return "[UNTRUSTED_PAGE_TEXT]\n" + observation
    prefix, rest = observation.split(elements_marker, 1)
    elements, visible_text = rest.split(text_marker, 1)
    return "\n".join(
        [
            "[TOOL_RESULT]",
            prefix.rstrip(),
            "[UNTRUSTED_PAGE_ELEMENTS]",
            elements.rstrip(),
            "[UNTRUSTED_PAGE_TEXT]",
            visible_text,
        ]
    )
