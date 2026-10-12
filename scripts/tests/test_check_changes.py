import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("check_changes", Path(__file__).parents[1] / "check_changes.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def change(self, name="feature", archived=False, scope="server/example.py"):
        folder = self.root / "openspec" / "changes"
        folder = folder / "archive" / name if archived else folder / name
        folder.mkdir(parents=True)
        for filename in ("proposal.md", "design.md", "tasks.md"):
            (folder / filename).write_text("test", encoding="utf-8")
        (folder / "files.txt").write_text(scope, encoding="utf-8")
        return folder

    def test_uncovered_file_fails(self):
        self.change()
        self.assertTrue(module.check(self.root, ["server/new.py"], None))

    def test_active_scope_covers_implementation(self):
        self.change()
        self.assertEqual(module.check(self.root, ["server/example.py"], None), [])

    def test_new_archive_covers_same_change(self):
        folder = self.change(archived=True)
        paths = ["server/example.py", folder.relative_to(self.root).as_posix() + "/proposal.md"]
        self.assertEqual(module.check(self.root, paths, None), [])

    def test_historical_scope_cannot_cover_new_edit(self):
        self.change(archived=True)
        self.assertTrue(module.check(self.root, ["server/example.py"], None))

    def test_root_wildcard_is_rejected(self):
        self.change(scope="**/*")
        self.assertTrue(module.check(self.root, ["server/example.py"], None))

    def test_untracked_files_are_checked(self):
        (self.root / "new.py").write_text("x = 1", encoding="utf-8")
        paths, base = module.changed_files(self.root)
        self.assertIsNone(base)
        self.assertIn("new.py", paths)


if __name__ == "__main__":
    unittest.main()
