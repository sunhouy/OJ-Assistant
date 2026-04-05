from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root_dir = Path(__file__).resolve().parent
    build_script = root_dir / "scripts" / "build_release.py"
    cmd = [sys.executable, str(build_script), *sys.argv[1:]]

    print("Running:", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=str(root_dir), check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())