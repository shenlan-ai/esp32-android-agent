"""Build a reviewable Windows x64 one-folder distribution (no publishing or flashing)."""
from __future__ import annotations

import argparse
import ast
import io
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from importlib import metadata
from pathlib import Path

from collect_firmware import PROFILES, collect, sha256
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("fastapi", "uvicorn", "httpx", "pillow", "pydantic", "pyserial")
SOURCE_ROOTS = {"server", "hardware", "scripts", "packaging", "docs", "openspec", ".github"}
SOURCE_FILES = {"README.md", "README.en.md", "LICENSE", "NOTICE", "AGENTS.md", "agent.md",
                "CONTRIBUTING.md", ".env.example", ".gitignore"}


def command(*args: str, cwd: Path = ROOT, timeout: int = 300) -> str:
    return subprocess.run(list(args), cwd=cwd, check=True, text=True, encoding="utf-8",
                          capture_output=True, timeout=timeout).stdout.strip()


def dependency_closure(names=RUNTIME) -> list[str]:
    found = {}
    pending = list(names)
    while pending:
        dist = metadata.distribution(pending.pop())
        name = dist.metadata["Name"]
        key = name.lower().replace("_", "-")
        if key in found:
            continue
        found[key] = name
        for text in dist.requires or []:
            requirement = Requirement(text)
            if not requirement.marker or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
    return sorted(found.values(), key=str.lower)


def source_file_allowed(name: str) -> bool:
    parts = Path(name).parts
    return (bool(parts) and not any(part in {".pio", ".git", ".venv", ".runtime-local",
                                           "__pycache__", "traces", "dist", "build"} for part in parts)
            and (parts[0] in SOURCE_ROOTS or name in SOURCE_FILES)
            and not name.endswith((".bin", ".local.json", ".pyc"))
            and ".env" not in parts)


def source_archive(root: Path, target: Path) -> None:
    names = command("git", "ls-files", "--cached", cwd=root).splitlines()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(set(names)):
            if not source_file_allowed(name):
                continue
            path = root / name
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"Unsafe source file: {name}")
            archive.writestr(zipfile.ZipInfo(name), path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    # New implementation files must be staged before building, to include their sources.
    with zipfile.ZipFile(target) as archive:
        if "server/android_agent/launcher.py" not in archive.namelist():
            raise ValueError("Stage or commit new source files before building the source archive")


def collect_licenses(folder: Path, names: list[str], cache: Path) -> list[dict]:
    folder.mkdir()
    entries = []
    for name in [*names, "PyInstaller"]:
        dist = metadata.distribution(name)
        destination = folder / name
        destination.mkdir()
        destination.joinpath("METADATA.txt").write_text(dist.read_text("METADATA") or "", encoding="utf-8")
        licenses = []
        for item in dist.files or []:
            if any(term in item.name.lower() for term in ("license", "copying", "notice")):
                source = Path(dist.locate_file(item))
                # Preserve paths: some packages have several component LICENSE files.
                relative = Path(*item.parts[1:])
                target = destination / relative
                if not target.resolve().is_relative_to(destination.resolve()):
                    raise ValueError(f"Invalid installed license path for {name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                licenses.append({"file": target.relative_to(folder.parent).as_posix(),
                                 "sha256": sha256(target)})
        if not licenses:
            locked = json.loads((ROOT / "packaging/sources.json").read_text(encoding="utf-8"))["sources"]
            fallback = next((item for item in locked if item["name"] == name and item.get("license_fallback")), None)
            if not fallback or fallback["version"] != dist.version:
                raise ValueError(f"No installed license file for {name}; inspect before distributing")
            source = cache / name / fallback["license_fallback"]
            target = destination / "LICENSE.txt"
            shutil.copyfile(source, target)
            licenses.append({"file": target.relative_to(folder.parent).as_posix(), "sha256": sha256(target),
                             "source_commit": fallback["commit"]})
        entries.append({"name": dist.metadata["Name"], "version": dist.version,
                        "license": dist.metadata.get("License-Expression", dist.metadata.get("License", "")),
                        "project_urls": dist.metadata.get_all("Project-URL", []),
                        "licenses": licenses, "build_tool": name == "PyInstaller"})
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise ValueError("The Python runtime license was not found")
    shutil.copyfile(python_license, folder / "Python-LICENSE.txt")
    return entries


def bundled_distributions(toc: Path) -> list[str]:
    """Include licenses for optional imports actually pulled in by freezer hooks."""
    owners = {}
    for dist in metadata.distributions():
        for item in dist.files or []:
            owners[str(Path(dist.locate_file(item)).resolve()).casefold()] = dist.metadata["Name"]
    names = set()

    def visit(value):
        if isinstance(value, (list, tuple)):
            for child in value:
                visit(child)
        elif isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, str) and Path(value).is_absolute():
            key = str(Path(value).resolve()).casefold()
            if key in owners:
                names.add(owners[key])
            elif "site-packages" in Path(value).parts and Path(value).is_file():
                raise ValueError(f"Bundled third-party file has no distribution owner: {value}")

    visit(ast.literal_eval(toc.read_text(encoding="utf-8")))
    return sorted(names, key=str.lower)


def collect_upstream(cache: Path, target: Path) -> list[dict]:
    cache.mkdir(parents=True, exist_ok=True)
    records = []
    for source in json.loads((ROOT / "packaging/sources.json").read_text(encoding="utf-8"))["sources"]:
        checkout = cache / source["name"]
        if not checkout.exists():
            command("git", "clone", "--filter=blob:none", "--depth", "1", "--branch", source["tag"],
                    "--sparse", source["repository"], str(checkout), timeout=600)
            # Root files are always included by cone mode.
            dirs = [p for p in source["paths"] if "." not in Path(p).name]
            command("git", "-C", str(checkout), "sparse-checkout", "set", *dirs, timeout=600)
        commit = command("git", "rev-parse", "HEAD", cwd=checkout)
        if commit != source["commit"]:
            raise ValueError(f"Wrong upstream commit for {source['name']}: {commit}")
        command("git", "diff", "--exit-code", "HEAD", "--", *source["paths"], cwd=checkout)
        filename = f"{source['name']}-{source['version']}-sources.tar"
        output = target / filename
        # git archive in a partial clone may eagerly fetch the entire SDK even
        # with pathspecs. Export only verified, tracked sparse working-tree files.
        selected = command("git", "ls-files", "--cached", "--", *source["paths"], cwd=checkout).splitlines()
        with tarfile.open(output, "w") as archive:
            for name in sorted(selected):
                path = checkout / name
                if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(checkout.resolve()):
                    raise ValueError(f"Unsafe or unavailable upstream source: {name}")
                data = path.read_bytes()
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(data))
        records.append({**source, "archive": filename, "sha256": sha256(output)})
    return records


def collect_relink(root: Path, target: Path) -> None:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, config in PROFILES.items():
            build = root / "hardware" / config[0] / ".pio/build" / name
            objects = [p for p in build.rglob("*") if p.suffix in {".o", ".a", ".elf", ".map"}]
            if not any(p.suffix == ".elf" for p in objects) or not any(p.suffix == ".o" for p in objects):
                raise ValueError(f"Missing relink objects for {name}")
            for path in sorted(objects):
                if path.is_symlink() or not path.resolve().is_relative_to(build.resolve()):
                    raise ValueError(f"Unsafe relink object for {name}")
                archive.write(path, (Path(name) / path.relative_to(build)).as_posix())


def inventory(folder: Path) -> dict:
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink in distribution: {path}")
        if path.is_file() and path != folder / "checksums.json":
            result[path.relative_to(folder).as_posix()] = {"size": path.stat().st_size, "sha256": sha256(path)}
    return result


def build(output: Path, cache: Path, framework: Path) -> Path:
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise ValueError("Build the portable application on Windows x64")
    if metadata.version("PyInstaller") != "6.16.0":
        raise ValueError("Install ./server[build] with fixed PyInstaller 6.16.0")
    package = json.loads((framework / "package.json").read_text(encoding="utf-8"))
    if package["version"] != "3.20017.241212+sha.dcc1105b":
        raise ValueError("The installed Arduino framework differs from the pinned build")
    for name, config in PROFILES.items():
        library = ROOT / "hardware" / config[0] / ".pio/libdeps" / name / "ArduinoJson/library.json"
        if json.loads(library.read_text(encoding="utf-8"))["version"] != "7.4.2":
            raise ValueError(f"Unexpected ArduinoJson version for {name}")
    output.mkdir(parents=True, exist_ok=False)
    names = dependency_closure()
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--console",
            "--name", "esp32-android-agent", "--distpath", str(output),
            "--workpath", str(output / "build"), "--specpath", str(output / "build"),
            "--paths", str(ROOT / "server"), "--add-data", f"{ROOT / 'server/android_agent/static'};android_agent/static"]
    for name in names:
        args += ["--copy-metadata", name]
    for module in ("pytest", "_pytest", "IPython", "tkinter", "numpy", "matplotlib", "setuptools", "ruff", "PyInstaller",
                   "rich", "pygments", "wsproto", "websockets", "watchfiles", "gunicorn",
                   "uvloop", "httptools", "trio", "orjson", "ujson", "brotli", "zstandard", "socksio", "yaml"):
        args += ["--exclude-module", module]
    # Dynamic backends are explicitly selected by launcher.py.
    args += ["--hidden-import", "uvicorn.logging", "--hidden-import", "uvicorn.loops.asyncio",
             "--hidden-import", "uvicorn.protocols.http.h11_impl", "--hidden-import", "uvicorn.lifespan.on",
             str(ROOT / "packaging/windows_entry.py")]
    subprocess.run(args, cwd=ROOT, check=True, timeout=900)
    names = sorted(set(names) | set(bundled_distributions(output / "build/esp32-android-agent/Analysis-00.toc")),
                   key=str.lower)
    # PyInstaller's runtime hooks are covered separately; it is not an app dependency.
    names = [name for name in names if name.lower() != "pyinstaller"]
    folder = output / "esp32-android-agent"
    for filename in ("LICENSE", "NOTICE"):
        shutil.copyfile(ROOT / filename, folder / filename)
    shutil.copyfile(ROOT / "docs/PORTABLE.md", folder / "START-HERE.md")
    sources = folder / "sources"
    sources.mkdir()
    source_archive(ROOT, sources / "project.zip")
    upstream = collect_upstream(cache, sources)
    deps = collect_licenses(folder / "licenses", names, cache)
    collect_relink(ROOT, sources / "firmware-relink.zip")
    firmware = collect(ROOT, framework, folder / "firmware")
    release = {"schema": 1, "version": metadata.version("esp32-android-agent"),
               "git_revision": command("git", "rev-parse", "HEAD"),
               "dirty": bool(command("git", "status", "--porcelain")),
               "python": platform.python_version(), "python_source": "https://www.python.org/downloads/source/",
               "platform": platform.platform(), "dependencies": deps, "firmware": firmware,
               "upstream_sources": upstream, "adb_bundled": False,
               "adb_source": "https://developer.android.com/tools/releases/platform-tools",
               "validation": "Built firmware and offline app; Android/S3 real input pending"}
    (folder / "release.json").write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
    (folder / "requirements-installed.txt").write_text(
        "\n".join(f"{name}=={metadata.version(name)}" for name in names) + "\n", encoding="utf-8")
    (folder / "checksums.json").write_text(json.dumps(inventory(folder), indent=2) + "\n", encoding="utf-8")
    filename = output / f"esp32-android-agent-{release['version']}-windows-x64.zip"
    with zipfile.ZipFile(filename, "x", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, (Path(folder.name) / path.relative_to(folder)).as_posix())
    filename.with_suffix(".zip.sha256").write_text(f"{sha256(filename)}  {filename.name}\n", encoding="utf-8")
    print(json.dumps({"zip": str(filename), "sha256": sha256(filename)}, indent=2))
    return filename


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New build output directory")
    parser.add_argument("--source-cache", type=Path, default=ROOT / "build/upstream-sources")
    parser.add_argument("--framework", type=Path,
                        default=Path.home() / ".platformio/packages/framework-arduinoespressif32")
    args = parser.parse_args()
    try:
        build(args.output.resolve(), args.source_cache.resolve(), args.framework.resolve())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Build failed; no release was published: {exc}\n")


if __name__ == "__main__":
    main()
