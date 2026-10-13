"""Reject CI regressions using mutations of the real, device-free workflows."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

spec = importlib.util.spec_from_file_location("check_workflows", Path(__file__).parents[1] / "check_workflows.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WorkflowCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        destination = self.root / ".github/workflows"
        destination.mkdir(parents=True)
        for filename in ("ci.yml", "portable.yml"):
            source = module.ROOT / ".github/workflows" / filename
            (destination / filename).write_bytes(source.read_bytes())
        self.path = destination / "ci.yml"
        self.workflow = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        self.patcher = patch.object(module, "ROOT", self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def save(self):
        self.path.write_text(yaml.safe_dump(self.workflow), encoding="utf-8")

    def test_current_workflows_pass(self):
        self.assertEqual(module.check(), [])

    def test_missing_board_status_is_rejected(self):
        for step in self.workflow["jobs"]["geometry"]["steps"]:
            if "run" in step:
                step["run"] = step["run"].replace(" server/tests/board-status.test.mjs", "")
        self.save()
        self.assertIn("ci.yml: geometry job must run coordinate and board-status tests", module.check())

    def test_commented_command_is_not_coverage(self):
        for step in self.workflow["jobs"]["geometry"]["steps"]:
            if "run" in step:
                step["run"] = "# " + step["run"]
        self.save()
        self.assertIn("ci.yml: geometry job must run coordinate and board-status tests", module.check())

    def test_wrong_job_is_not_coverage(self):
        steps = self.workflow["jobs"]["geometry"]["steps"]
        command = next(step for step in steps if "run" in step)
        steps.remove(command)
        self.workflow["jobs"]["governance"]["steps"].append(command)
        self.save()
        self.assertIn("ci.yml: geometry job must run coordinate and board-status tests", module.check())

    def test_missing_tool_lint_is_rejected(self):
        for step in self.workflow["jobs"]["python"]["steps"]:
            if "ruff check" in step.get("run", ""):
                step["run"] = step["run"].replace(" tools", "")
        self.save()
        self.assertIn("ci.yml: Python job must lint server, scripts, tools and packaging with project config", module.check())

    def test_missing_project_config_is_rejected(self):
        for step in self.workflow["jobs"]["python"]["steps"]:
            if "ruff check" in step.get("run", ""):
                step["run"] = step["run"].replace(" --config server/pyproject.toml", "")
        self.save()
        self.assertIn("ci.yml: Python job must lint server, scripts, tools and packaging with project config", module.check())


if __name__ == "__main__":
    unittest.main()
