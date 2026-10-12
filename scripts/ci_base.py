"""Select a fail-closed OpenSpec comparison base from GitHub event SHAs."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path


def git(root: Path, *args: str, input_text: str | None = None) -> str:
    return subprocess.run(["git", *args], cwd=root, input=input_text, check=True,
                          capture_output=True, text=True, encoding="utf-8", timeout=30).stdout.strip()


def choose_base(root: Path, event: str, pr_base: str = "", before: str = "") -> str:
    if event == "workflow_dispatch":
        return git(root, "rev-parse", "--verify", "HEAD")
    if event not in {"push", "pull_request"}:
        raise ValueError("Unsupported event; no comparison was run")
    value = pr_base if event == "pull_request" else before
    if not re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", value):
        raise ValueError("Missing or invalid event base SHA; refusing to skip changes")
    if set(value) == {"0"}:
        if event != "push":
            raise ValueError("A pull request requires a real base SHA")
        return git(root, "hash-object", "-w", "-t", "tree", "--stdin", input_text="")
    object_type = git(root, "cat-file", "-t", value)
    if object_type not in {"commit", "tree"}:
        raise ValueError("The base must be a Git commit or tree")
    return value.lower()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--pr-base", default=os.getenv("PR_BASE_SHA", ""))
    parser.add_argument("--before", default=os.getenv("PUSH_BEFORE_SHA", ""))
    args = parser.parse_args()
    try:
        value = choose_base(Path(__file__).resolve().parents[1], args.event, args.pr_base, args.before)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Cannot determine OpenSpec base: {exc}\n")
    if os.getenv("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write(f"base={value}\n")
    print(value)


if __name__ == "__main__":
    main()
