"""Check the repository's device-free CI invariants; use actionlint for full syntax."""
from __future__ import annotations

import re
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def command_targets(job: dict, prefix: tuple[str, ...]) -> set[str]:
    """Inspect direct commands in this job; comments are never runnable coverage."""
    targets = set()
    for step in job["steps"]:
        for line in step.get("run", "").splitlines():
            try:
                words = shlex.split(line, comments=True)
            except ValueError:
                continue  # Full shell/YAML syntax is checked by actionlint.
            if tuple(words[:len(prefix)]) == prefix:
                targets.update(words[len(prefix):])
    return targets


def check() -> list[str]:
    errors = []
    workflows = {}
    for filename in ("ci.yml", "portable.yml"):
        value = yaml.safe_load((ROOT / ".github/workflows" / filename).read_text(encoding="utf-8"))
        workflows[filename] = value
        if value.get("permissions") != {"contents": "read"}:
            errors.append(f"{filename}: expected read-only repository permissions")
        if "secrets." in str(value):
            errors.append(f"{filename}: device-free checks must not use secrets")
        for name, job in value["jobs"].items():
            if not isinstance(job.get("timeout-minutes"), int) or job["timeout-minutes"] <= 0:
                errors.append(f"{filename}/{name}: missing bounded timeout")
            if job.get("permissions", {"contents": "read"}) != {"contents": "read"}:
                errors.append(f"{filename}/{name}: job permissions must be read-only")
            for step in job["steps"]:
                if "uses" in step and not re.fullmatch(
                    r"actions/(checkout|setup-python|setup-node|upload-artifact)@[0-9a-f]{40}", step["uses"]
                ):
                    errors.append(f"{filename}/{name}: unpinned or unexpected action")
    ci = workflows["ci.yml"]
    if set(ci["on"]) != {"push", "pull_request", "workflow_dispatch"}:
        errors.append("ci.yml: unexpected triggers")
    jobs = ci["jobs"]
    if not {"governance", "python", "geometry", "firmware"} <= set(jobs):
        errors.append("ci.yml: missing a required check job")
    else:
        matrix = jobs["python"]["strategy"]["matrix"]
        if set(matrix["os"]) != {"ubuntu-latest", "windows-latest"} or set(matrix["python"]) != {"3.10", "3.12"}:
            errors.append("ci.yml: Python/platform coverage changed")
        profiles = {item["profile"] for item in jobs["firmware"]["strategy"]["matrix"]["include"]}
        if profiles != {"esp32dev", "esp32_s3_devkitc", "xiao_esp32s3", "esp32_s3_zero"}:
            errors.append("ci.yml: four-board matrix incomplete")
        governance = str(jobs["governance"])
        for requirement in ("fetch-depth", "ci_base.py", "--base", "--strict", "--archived"):
            if requirement not in governance:
                errors.append(f"ci.yml: missing governance check {requirement}")
        if "python -m unittest discover -s scripts/tests" not in str(jobs["firmware"]):
            errors.append("ci.yml: native/tools tests not included after firmware build")
        if not {"server/tests/geometry.test.mjs", "server/tests/board-status.test.mjs"} <= command_targets(
            jobs["geometry"], ("node", "--test")
        ):
            errors.append("ci.yml: geometry job must run coordinate and board-status tests")
        if not {"server", "scripts", "tools", "packaging"} <= command_targets(
            jobs["python"], ("python", "-m", "ruff", "check", "--config", "server/pyproject.toml")
        ):
            errors.append("ci.yml: Python job must lint server, scripts, tools and packaging with project config")
    portable = workflows["portable.yml"]
    if set(portable["on"]) != {"workflow_dispatch"}:
        errors.append("portable.yml: building the artifact must be manual")
    steps = portable["jobs"]["portable"]["steps"]
    build = next((i for i, step in enumerate(steps) if "build_portable.py" in step.get("run", "")), -1)
    smoke = next((i for i, step in enumerate(steps) if "smoke_portable.py" in step.get("run", "")), -1)
    upload = next((i for i, step in enumerate(steps) if step.get("uses", "").startswith("actions/upload-artifact@")), -1)
    if not 0 <= build < smoke < upload:
        errors.append("portable.yml: build/smoke must precede artifact upload")
    if upload >= 0:
        artifact = steps[upload]
        if artifact.get("if") or artifact["with"].get("if-no-files-found") != "error":
            errors.append("portable.yml: upload must require success and existing artifacts")
        if artifact["with"].get("path", "").splitlines() != ["dist/windows-ci/*.zip", "dist/windows-ci/*.zip.sha256"]:
            errors.append("portable.yml: only ZIP and SHA may be uploaded")
    return errors


if __name__ == "__main__":
    problems = check()
    if problems:
        raise SystemExit("\n".join(problems))
    print("Workflow invariants passed (read-only, pinned, device-free, checked artifacts)")
