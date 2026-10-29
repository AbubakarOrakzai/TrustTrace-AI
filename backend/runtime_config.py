from __future__ import annotations

import os
from pathlib import Path


def data_path(environment_key: str, filename: str, base_dir: Path) -> Path:
    if os.getenv("VERCEL") == "1":
        return Path("/tmp") / filename
    return Path(os.getenv(environment_key, str(base_dir / filename)))
