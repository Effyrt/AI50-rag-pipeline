"""Guard that every third-party package the test suite imports is declared.

A missing declaration passes locally, where the package happens to already be
installed, and fails only in CI on a clean runner. That is what happened with PyYAML:
`pip install pyyaml` in a dev shell, never added to requirements-dev.txt, green
locally, red in CI.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "tests"

# Import name -> distribution name, where they differ.
IMPORT_TO_DISTRIBUTION = {
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
    "bs4": "beautifulsoup4",
}

# Provided by the test runner itself or by the repo, so not declared as dependencies.
NOT_DEPENDENCIES = {"src", "tests", "conftest"}


def declared_distributions() -> set[str]:
    names = set()
    for req in ("requirements-dev.txt", "requirements.txt"):
        path = REPO_ROOT / req
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                names.add(line.split("==")[0].split(">=")[0].split("[")[0].strip().lower())
    return names


def imported_top_level_modules() -> set[str]:
    modules = set()
    for path in TESTS_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                modules.add(node.module.split(".")[0])
    return modules


def test_every_test_import_is_declared():
    third_party = {
        m for m in imported_top_level_modules()
        if m not in sys.stdlib_module_names and m not in NOT_DEPENDENCIES
    }
    declared = declared_distributions()

    missing = {
        m for m in third_party
        if IMPORT_TO_DISTRIBUTION.get(m, m).lower() not in declared
    }

    assert not missing, (
        f"tests import {sorted(missing)} but no requirements file declares them. "
        f"CI installs only requirements-dev.txt, so this passes locally and fails "
        f"on a clean runner."
    )


def test_pyyaml_specifically_declared():
    """The concrete regression: tests/test_deployment_config.py imports yaml."""
    assert "pyyaml" in declared_distributions()
