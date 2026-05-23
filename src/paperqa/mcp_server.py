"""MCP server for paper-qa2 — expose document Q&A as MCP tools.

Usage:
    python -m paperqa.mcp_server
    # or: mcp run src/paperqa/mcp_server.py
    # or via Claude Desktop / Cursor config pointing to this module

Environment:
    DEEPSEEK_API_KEY  — required (or set a different LLM via config)
    PAPERQA_SETTINGS  — optional named config (default: "deepseek")
    PAPERQA_DIRECTORY — optional paper directory to index on startup
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

import anyio
from mcp.server.fastmcp import FastMCP

from paperqa.docs import Docs
from paperqa.settings import Settings
from paperqa.utils import setup_default_logs

if TYPE_CHECKING:
    from paperqa.types import PQASession

logger = logging.getLogger(__name__)
setup_default_logs()

mcp = FastMCP(
    name="paper-qa2",
    instructions=(
        "paper-qa2 is a document Q&A system powered by DeepSeek v4 Pro."
        " Add PDFs, then ask questions about them."
    ),
)

# ── global state ──────────────────────────────────────────────────
_docs: Docs | None = None
_settings: Settings | None = None
_lock = asyncio.Lock()


async def _get_docs() -> Docs:
    global _docs, _settings  # noqa: PLW0603
    if _docs is None or _settings is None:
        async with _lock:
            if _docs is None:
                config_name = os.environ.get("PAPERQA_SETTINGS", "deepseek")
                _settings = Settings.from_name(config_name)
                _docs = Docs()

                # optional: index a directory on startup
                directory = os.environ.get("PAPERQA_DIRECTORY", "")
                if directory:
                    p = Path(directory)
                    if p.is_dir():
                        pdfs = list(p.glob("**/*.pdf"))
                        logger.info(
                            "Indexing %d PDFs from %s ...", len(pdfs), directory
                        )
                        for pdf_path in pdfs:
                            await _docs.aadd(
                                path=str(pdf_path),
                                docname=pdf_path.name,
                                settings=_settings,
                            )
                        logger.info("Indexing complete — %d docs", len(_docs.docs))
    return _docs


async def _get_settings() -> Settings:
    await _get_docs()
    assert _settings is not None  # noqa: S101
    return _settings


# ── tools ─────────────────────────────────────────────────────────


@mcp.tool(
    name="paperqa_query",
    description=(
        "Ask a question about documents in the paper-qa2 index."
        " Returns an evidence-backed answer with citations."
    ),
)
async def paperqa_query(question: str) -> str:
    """Query the document index."""
    docs = await _get_docs()
    settings = await _get_settings()

    result: PQASession = await docs.aquery(question, settings=settings)

    # build a rich response
    lines = [result.answer, "", "**Sources:**"]
    for ctx in result.contexts:
        lines.append(f"- {ctx.id} (score: {ctx.score:.1f})")
    return "\n".join(lines)


@mcp.tool(
    name="paperqa_add_pdf",
    description=(
        "Add a PDF document to the paper-qa2 index."
        " Provide the file path, and optionally a citation string."
    ),
)
async def paperqa_add_pdf(
    path: str,
    citation: str | None = None,
    docname: str | None = None,
) -> str:
    """Add a PDF to the index."""
    docs = await _get_docs()
    settings = await _get_settings()

    p = Path(path)
    if not p.exists():
        return f"Error: file not found: {path}"
    if p.suffix.lower() != ".pdf":
        return f"Error: only PDF files are supported (got {p.suffix})"

    try:
        dockey = await docs.aadd(
            path=str(p),
            citation=citation or "",
            docname=docname or p.name,
            settings=settings,
        )
        return f"Added '{p.name}' to index (dockey={dockey}). Index now has {len(docs.docs)} doc(s), {len(docs.texts)} chunk(s)."
    except Exception as exc:
        logger.exception("Failed to add PDF")
        return f"Error adding PDF: {exc}"


@mcp.tool(
    name="paperqa_status",
    description="Show current status of the paper-qa2 document index.",
)
async def paperqa_status() -> str:
    """Report index status."""
    docs = await _get_docs()
    settings = await _get_settings()
    lines = [
        f"**paper-qa2 Status**",
        f"- LLM: {settings.llm}",
        f"- Embedding: {settings.embedding}",
        f"- Documents indexed: {len(docs.docs)}",
        f"- Text chunks: {len(docs.texts)}",
        f"- Config: {os.environ.get('PAPERQA_SETTINGS', 'deepseek')}",
    ]
    return "\n".join(lines)


# ── entry ─────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for `python -m paperqa.mcp_server`."""
    mcp.run()


if __name__ == "__main__":
    main()
