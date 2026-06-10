"""testbed `docs/reference/` → 본 프로젝트 `docs/references/testbed-snapshot/` 복사.

Usage:
    uv run python scripts/sync_testbed_snapshot.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path

DEFAULT_SRC = Path(
    os.environ.get(
        "ISAAC_SIM_TESTBED_REFERENCE_DIR",
        "C:/workspace/isaac-sim-testbed/docs/reference",
    )
)
DEFAULT_DST = (
    Path(__file__).resolve().parents[1]
    / "docs" / "references" / "testbed-snapshot"
)


def _count_and_size(root: Path) -> tuple[int, int]:
    files = [p for p in root.rglob("*") if p.is_file()]
    total_size = sum(p.stat().st_size for p in files)
    return len(files), total_size


def _write_readme(dst: Path, src: Path, file_count: int, byte_size: int) -> None:
    readme = dst / "README.md"
    readme.write_text(
        f"""# testbed-snapshot (읽기 전용)

- **원본**: `{src.as_posix()}`
- **복사 일시**: {dt.datetime.now(dt.UTC).isoformat()}
- **파일 개수**: {file_count}
- **용량**: {byte_size / (1024 * 1024):.2f} MiB
- **복사 방법**: `uv run python scripts/sync_testbed_snapshot.py`

> 이 디렉토리는 **읽기 전용**. 수정하면 재동기화 시 손실됨.
> 원본 업데이트 시 이 스크립트 재실행으로 대상 디렉토리 전체 교체.
""",
        encoding="utf-8",
    )


def sync(src: Path = DEFAULT_SRC, dst: Path = DEFAULT_DST) -> None:
    if not src.exists():
        raise FileNotFoundError(f"testbed source not found: {src}")

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=False)

    file_count, byte_size = _count_and_size(dst)
    _write_readme(dst, src, file_count, byte_size)


def _update_progress(file_count: int, byte_size: int) -> None:
    progress_path = (
        Path(__file__).resolve().parents[1]
        / "docs" / "references" / "harvest-progress.json"
    )
    if not progress_path.exists():
        return
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    progress["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
    progress["phases"]["sync_testbed_snapshot"] = {
        "status": "complete",
        "completed_at": dt.datetime.now(dt.UTC).isoformat(),
        "files_copied": file_count,
        "bytes_copied": byte_size,
    }
    progress_path.write_text(
        json.dumps(progress, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--dst", type=Path, default=DEFAULT_DST)
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="harvest-progress.json 업데이트 건너뛰기 (테스트용)",
    )
    args = parser.parse_args()

    sync(src=args.src, dst=args.dst)
    file_count, byte_size = _count_and_size(args.dst)
    print(f"Copied {file_count} files ({byte_size / (1024*1024):.2f} MiB)")

    if not args.no_progress:
        _update_progress(file_count, byte_size)

    return 0


if __name__ == "__main__":
    sys.exit(main())
