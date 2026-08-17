from __future__ import annotations

from typing import Any


def parse_reasoning_response_text(text: str) -> dict[str, Any]:
    """Parse a reasoning response text into structured parts.

    Expected keys in text: REASONING:, ANSWER:, CONFIDENCE:, IS_FINAL:, NEXT_QUESTION:
    """
    result: dict[str, Any] = {
        "reasoning": "",
        "answer": "",
        "confidence": 0.5,
        "is_final": False,
        "next_question": None,
    }

    lines = text.strip().split("\n")
    current_key: str | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("REASONING:"):
            current_key = "reasoning"
            result[current_key] = line.replace("REASONING:", "").strip()
        elif line.startswith("ANSWER:"):
            current_key = "answer"
            result[current_key] = line.replace("ANSWER:", "").strip()
        elif line.startswith("CONFIDENCE:"):
            try:
                conf_str = line.replace("CONFIDENCE:", "").strip()
                result["confidence"] = float(conf_str)
            except ValueError:
                result["confidence"] = 0.5
        elif line.startswith("IS_FINAL:"):
            is_final_str = line.replace("IS_FINAL:", "").strip().lower()
            result["is_final"] = is_final_str in ("yes", "true", "1")
        elif line.startswith("NEXT_QUESTION:"):
            current_key = "next_question"
            result[current_key] = line.replace("NEXT_QUESTION:", "").strip()
        elif current_key is not None and line:
            result[current_key] = (
                (result[current_key] + " " + line)
                if isinstance(result[current_key], str)
                else line
            )

    return result
