import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load("ci_base")
changes = load("check_changes")


class BaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for args in (("init", "-q"), ("config", "user.name", "CI test"),
                     ("config", "user.email", "ci-test@example.invalid")):
            base.git(self.root, *args)
        (self.root / "app.py").write_text("original\n")
        archive = self.root / "openspec/changes/archive/2026-01-01-fixture"
        archive.mkdir(parents=True)
        for name in ("proposal.md", "design.md", "tasks.md"):
            (archive / name).write_text("original fixture\n")
        (archive / "files.txt").write_text("app.py\n")
        base.git(self.root, "add", ".")
        base.git(self.root, "commit", "-qm", "fixture")
        self.original = base.git(self.root, "rev-parse", "HEAD")

    def test_pr_and_push_keep_the_original_base(self):
        (self.root / "app.py").write_text("updated\n")
        base.git(self.root, "add", ".")
        base.git(self.root, "commit", "-qm", "update")
        current = base.choose_base(self.root, "workflow_dispatch")
        self.assertNotEqual(current, self.original)
        self.assertEqual(base.choose_base(self.root, "pull_request", pr_base=self.original), self.original)
        self.assertEqual(base.choose_base(self.root, "push", before=self.original), self.original)

    def test_first_push_checks_every_file_against_a_real_empty_tree(self):
        empty = base.choose_base(self.root, "push", before="0" * 40)
        self.assertEqual(base.git(self.root, "cat-file", "-t", empty), "tree")
        files = base.git(self.root, "diff", "--name-only", empty, "HEAD").splitlines()
        self.assertIn("app.py", files)
        self.assertEqual(len(files), 5)

    def test_invalid_missing_or_nonexistent_base_never_falls_back(self):
        for value in ("", "HEAD", "-option", "a" * 39, "a" * 41, "x" * 40):
            with self.subTest(value=value), self.assertRaises(ValueError):
                base.choose_base(self.root, "push", before=value)
        with self.assertRaises(ValueError):
            base.choose_base(self.root, "pull_request", pr_base="0" * 40)
        with self.assertRaises(ValueError):
            base.choose_base(self.root, "pull_request_target", pr_base=self.original)
        with self.assertRaises(subprocess.CalledProcessError):
            base.choose_base(self.root, "push", before="f" * 40)

    def test_blob_cannot_be_used_as_a_comparison_tree(self):
        blob = base.git(self.root, "hash-object", "-w", "--stdin", input_text="blob")
        with self.assertRaisesRegex(ValueError, "commit or tree"):
            base.choose_base(self.root, "push", before=blob)

    def test_archived_history_is_rejected_against_pr_base(self):
        name = "openspec/changes/archive/2026-01-01-fixture/proposal.md"
        (self.root / name).write_text("rewritten history\n")
        revision = base.choose_base(self.root, "pull_request", pr_base=self.original)
        files, _ = changes.changed_files(self.root, revision)
        errors = changes.check(self.root, files, revision)
        self.assertTrue(any("历史变更不可直接修改" in error for error in errors))
