from __future__ import annotations

import os
from pathlib import Path


def default_data_path(filename: str, base_dir: Path) -> Path:
    data_dir = Path("/tmp") if os.getenv("VERCEL") == "1" else base_dir
    return data_dir / filename
