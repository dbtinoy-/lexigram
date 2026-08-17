"""Built-in skill implementations for the Lexigram skills package."""

from __future__ import annotations

from lexigram.ai.skills.builtin.code_execution import CodeExecutionSkill
from lexigram.ai.skills.builtin.database_query import DatabaseQuerySkill
from lexigram.ai.skills.builtin.datetime_skill import DatetimeSkill
from lexigram.ai.skills.builtin.file_operations import FileReadSkill, FileWriteSkill
from lexigram.ai.skills.builtin.http_request import HTTPRequestSkill
from lexigram.ai.skills.builtin.math_skill import MathSkill
from lexigram.ai.skills.builtin.text_processing import (
    TextSummarizeSkill,
    TextTranslateSkill,
)
from lexigram.ai.skills.builtin.web_search import WebSearchSkill

DateTimeSkill = DatetimeSkill
HttpRequestSkill = HTTPRequestSkill

__all__ = [
    "CodeExecutionSkill",
    "DatabaseQuerySkill",
    "DateTimeSkill",
    "DatetimeSkill",
    "FileReadSkill",
    "FileWriteSkill",
    "HTTPRequestSkill",
    "HttpRequestSkill",
    "MathSkill",
    "TextSummarizeSkill",
    "TextTranslateSkill",
    "WebSearchSkill",
]
