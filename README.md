# PaperQA2 + DeepSeek v4 Pro

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/ph7klw76/paper-qa2/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Server-black?logo=anthropic)](https://modelcontextprotocol.io)

High-accuracy retrieval augmented generation (RAG) on PDFs and documents, powered by **DeepSeek v4 Pro** — with native **MCP server** support for AI agent integration (Claude Desktop, Cursor, etc.).

Forked and adapted from [Future-House/paper-qa](https://github.com/Future-House/paper-qa) with DeepSeek-specific optimizations and MCP layer.

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/ph7klw76/paper-qa2.git
cd paper-qa2
pip install -e ".[pypdf]"

# For local embeddings (no OpenAI key needed):
pip install sentence-transformers
```

### 2. Set API Key

```bash
export DEEPSEEK_API_KEY="sk-..."
```

### 3. Run via CLI

```bash
pqa ask --settings deepseek "What is CRISPR-Cas9?"
```

Or in Python:

```python
import asyncio
from paperqa.settings import Settings
from paperqa.docs import Docs

async def main():
    settings = Settings.from_name("deepseek")
    docs = Docs()
    await docs.aadd(path="paper.pdf", citation="Smith et al. (2021). Nature.", settings=settings)
    result = await docs.aquery("What is the main finding?", settings=settings)
    print(result.answer)

asyncio.run(main())
```

---

## MCP Server

paper-qa2 exposes itself as a **Model Context Protocol (MCP) server**, allowing AI agents (Claude Desktop, Cursor, Continue, etc.) to directly query your document index.

### Tools

| Tool | Description |
|------|-------------|
| `paperqa_query` | Ask a question about indexed documents. Returns evidence-backed answers with citations. |
| `paperqa_add_pdf` | Add a PDF to the index by file path. Optionally provide citation and docname. |
| `paperqa_status` | Show current index status: document count, active LLM, embedding model. |

### Configuration

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "paper-qa2": {
      "command": "python",
      "args": ["-m", "paperqa.mcp_server"],
      "env": {
        "DEEPSEEK_API_KEY": "sk-...",
        "PAPERQA_SETTINGS": "deepseek",
        "PAPERQA_DIRECTORY": "/path/to/papers/"
      }
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "paper-qa2": {
      "command": "python",
      "args": ["-m", "paperqa.mcp_server"],
      "env": {
        "DEEPSEEK_API_KEY": "sk-...",
        "PAPERQA_SETTINGS": "deepseek"
      }
    }
  }
}
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | Yes | — | DeepSeek API key |
| `PAPERQA_SETTINGS` | No | `deepseek` | Named config (`deepseek`, `high_quality`, `fast`) |
| `PAPERQA_DIRECTORY` | No | — | Auto-index all PDFs from this directory on startup |

### Running Standalone

```bash
# Stdio transport (for Claude Desktop / Cursor):
python -m paperqa.mcp_server

# Or with mcp CLI:
mcp run src/paperqa/mcp_server.py
```

---

## Configuration

### Built-in Configs

| Config | LLM | Embedding | Best for |
|--------|-----|-----------|----------|
| `deepseek` | deepseek-v4-pro | local MiniLM | DeepSeek users (no OpenAI key) |
| `high_quality` | GPT-4o | text-embedding-3-small | Maximum accuracy |
| `fast` | GPT-4o | text-embedding-3-small | Quick results |

### Custom Settings

```python
from paperqa.settings import Settings

settings = Settings(
    llm="deepseek/deepseek-v4-pro",
    summary_llm="deepseek/deepseek-v4-pro",
    agent={"agent_llm": "deepseek/deepseek-v4-pro"},
    embedding="st-multi-qa-MiniLM-L6-cos-v1",  # local, free
    temperature=0.0,
    answer={"evidence_k": 20, "answer_max_sources": 5},
)
```

---

## DeepSeek-Specific Notes

### What works
- Text-based Q&A, summarization, evidence gathering
- PDF parsing via PyPDF/PyMuPDF (independent of LLM)
- Metadata inference (titles, DOIs, authors)
- All agent-based tool use

### What doesn't work
- Image/multimedia enrichment (DeepSeek v4 Pro is text-only)
- Embeddings (DeepSeek has no embedding API — use `st-*` local models instead)

### Model name
The LiteLLM model identifier is `deepseek/deepseek-v4-pro`. If using a different DeepSeek model:

```python
settings = Settings(
    llm="deepseek/deepseek-chat",        # DeepSeek-V3
    summary_llm="deepseek/deepseek-chat",
    agent={"agent_llm": "deepseek/deepseek-chat"},
)
```

---

## Supported Document Types

- **PDF** (via `paper-qa-pypdf` or `paper-qa-pymupdf`)
- **Text files** (`.txt`, `.md`)
- **Microsoft Office** (`.docx`, `.pptx`, `.xlsx`) — requires `paper-qa[office]`
- **HTML** — built-in
- **Source code** — built-in

---

## Architecture

```
┌─────────────────────────────────────────┐
│  MCP Server (mcp_server.py)            │
│  ┌─────────┬──────────┬──────────┐     │
│  │  query  │ add_pdf  │  status  │     │
│  └────┬────┴────┬─────┴────┬─────┘     │
│       │         │           │           │
│  ┌────▼─────────▼───────────▼────┐     │
│  │         Docs (RAG)            │     │
│  │  ┌──────────┐  ┌──────────┐  │     │
│  │  │ PDF Parse│  │  Search   │  │     │
│  │  │ (PyPDF)  │  │ (tantivy) │  │     │
│  │  └──────────┘  └──────────┘  │     │
│  │  ┌──────────────────────┐    │     │
│  │  │  DeepSeek v4 Pro LLM │    │     │
│  │  │  (via LiteLLM)       │    │     │
│  │  └──────────────────────┘    │     │
│  └──────────────────────────────┘     │
└─────────────────────────────────────────┘
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

*This is an independent fork of [Future-House/paper-qa](https://github.com/Future-House/paper-qa). Not affiliated with FutureHouse Inc.*
