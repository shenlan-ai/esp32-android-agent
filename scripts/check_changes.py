"""Check that implementation changes belong to an OpenSpec change."""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
from pathlib import Path


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8"
    )


def changed_files(root: Path, base: str | None = None) -> tuple[list[str], str | None]:
    if base is None and git(root, "rev-parse", "--verify", "HEAD").returncode == 0:
        base = "HEAD"
    if base is not None:
        result = git(root, "diff", "--name-only", "--no-renames", base, "--")
        if result.returncode:
            raise ValueError(result.stderr.strip())
        paths = result.stdout.splitlines()
    else:
        paths = git(root, "ls-files", "--cached").stdout.splitlines()
    paths += git(root, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    return sorted(set(paths)), base


def check(root: Path, paths: list[str], base: str | None) -> list[str]:
    errors: list[str] = []
    changes = root / "openspec" / "changes"
    selected: list[Path] = []
    if changes.exists():
        selected.extend(p for p in changes.iterdir() if p.is_dir() and p.name != "archive")
        archive = changes / "archive"
        if archive.exists():
            for folder in archive.iterdir():
                if not folder.is_dir():
                    continue
                prefix = folder.relative_to(root).as_posix() + "/"
                if not any(p.startswith(prefix) for p in paths):
                    continue
                exists = base and git(root, "cat-file", "-e", f"{base}:{prefix}proposal.md").returncode == 0
                if exists:
                    errors.append(f"历史变更不可直接修改: {prefix}")
                else:
                    selected.append(folder)
    scopes: list[str] = []
    metadata: list[str] = []
    for folder in selected:
        manifest = folder / "files.txt"
        missing = [name for name in ("proposal.md", "design.md", "tasks.md", "files.txt")
                   if not (folder / name).is_file()]
        if missing:
            errors.append(f"{folder.name} 缺少 artifacts: {', '.join(missing)}")
            continue
        metadata.append(folder.relative_to(root).as_posix() + "/")
        for line in manifest.read_text(encoding="utf-8").splitlines():
            pattern = line.strip()
            if not pattern or pattern.startswith("#"):
                continue
            if (pattern in ("*", "**", "**/*") or ".." in Path(pattern).parts
                    or Path(pattern).is_absolute() or "\\" in pattern):
                errors.append(f"{folder.name} 非法文件范围: {pattern}")
                continue
            scopes.append(pattern)
    for path in paths:
        if any(path.startswith(prefix) for prefix in metadata):
            continue
        if not any(fnmatch.fnmatchcase(path, pattern) for pattern in scopes):
            errors.append(f"没有对应 OpenSpec 变更范围: {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Git revision to compare; defaults to HEAD/worktree")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if git(root, "rev-parse", "--show-toplevel").returncode:
        parser.error("项目尚未初始化 Git")
    try:
        paths, base = changed_files(root, args.base)
        errors = check(root, paths, base)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if errors:
        print("\n".join(errors))
        return 1
    print(f"OpenSpec 范围检查通过（{len(paths)} 个修改文件）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
