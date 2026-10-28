from __future__ import annotations

import os
from pathlib import Path


def default_data_path(filename: str, base_dir: Path) -> Path:
    data_dir = Path("/tmp") if os.getenv("VERCEL") == "1" else base_dir
    return data_dir / filename


def default_cors_origins() -> list[str]:
    default_origin = (
        "https://trust-trace-ai-jj13.vercel.app"
        if os.getenv("VERCEL") == "1"
        else "http://localhost:3000"
    )
    configured_origins = os.getenv("TRUSTTRACE_CORS_ORIGINS", default_origin)
    return [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]


def default_cors_origin_regex() -> str | None:
    if os.getenv("VERCEL") == "1":
        return r"^https://trust-trace-ai-jj13(?:-[a-z0-9-]+)?\.vercel\.app$"
    return None
