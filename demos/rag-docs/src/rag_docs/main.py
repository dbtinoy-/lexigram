"""Entry point for the docs ask demo (RAG over framework docs).

Usage::

    uv run python -m rag_docs index
    uv run python -m rag_docs ask "how do modules export services?"
    uv run python -m rag_docs ask --strategy mmr "how does routing work?"
    uv run python -m rag_docs demo
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

from lexigram.app import Application
from rag_docs.di.provider import resolve_default_docs_dir
from rag_docs.module import DocsAskModule
from rag_docs.service import DocsAskService

_CANNED_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("how do modules export services?", "vector"),
    ("what do providers register?", "mmr"),
    ("how does the outbox pattern work?", "vector"),
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rag_docs", description="RAG over the Lexigram docs tree"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_docs_dir(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--docs-dir",
            type=Path,
            default=None,
            help="corpus directory (default: repository docs/)",
        )

    p_index = sub.add_parser("index", help="build the index and print corpus stats")
    _add_docs_dir(p_index)

    p_ask = sub.add_parser("ask", help="ask a question with citations")
    p_ask.add_argument("query")
    p_ask.add_argument("--strategy", default="vector", help="vector | mmr")
    _add_docs_dir(p_ask)

    p_demo = sub.add_parser("demo", help="canned questions across strategies")
    _add_docs_dir(p_demo)
    return parser


def _effective_docs_dir(args: argparse.Namespace) -> Path:
    return args.docs_dir or resolve_default_docs_dir()


async def _ask_once(service: DocsAskService, query: str, strategy: str) -> int:
    """Ask one question, print answer + citations; return the exit code."""
    result = await service.ask(query, strategy=strategy)
    if result.is_err():
        print(f"error: {result.unwrap_err()}")
        return 1
    answer = result.unwrap()
    print(answer.answer)
    for number, citation in enumerate(answer.citations, start=1):
        print(f"[{number}] {citation}")
    return 0


async def _run(args: argparse.Namespace) -> int:
    async with Application.boot(
        name="rag-docs",
        modules=[DocsAskModule.configure(docs_dir=_effective_docs_dir(args))],
    ) as app:
        service = await app.container.resolve(DocsAskService)

        if args.command == "index":
            stats = service.corpus_stats
            print(f"indexed {stats.files} files / {stats.chunks} chunks")
            return 0

        if args.command == "ask":
            return await _ask_once(service, args.query, args.strategy)

        # demo
        for question, strategy in _CANNED_QUESTIONS:
            print(f"Q: {question}")
            code = await _ask_once(service, question, strategy)
            if code != 0:
                return code
            print()
    return 0


def main() -> None:
    args = _build_parser().parse_args()
    try:
        code = asyncio.run(_run(args))
    except KeyboardInterrupt:
        sys.exit(130)
    sys.exit(code)


if __name__ == "__main__":
    main()
