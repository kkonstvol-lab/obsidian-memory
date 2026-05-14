#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "operation_registry.py"
SCRIPTS_DIR = SCRIPT.parent


def load_module():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("operation_registry", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_registry_validates_without_issues() -> None:
    registry = load_module()
    assert registry.validate_registry() == []


def test_mutating_operations_require_approval() -> None:
    registry = load_module()
    for operation in registry.OPERATIONS:
        if operation.mode == "mutating":
            assert operation.approval_required, operation.name


def test_read_only_operations_do_not_require_approval() -> None:
    registry = load_module()
    for operation in registry.OPERATIONS:
        if operation.mode == "read_only":
            assert not operation.approval_required, operation.name


if __name__ == "__main__":
    test_registry_validates_without_issues()
    test_mutating_operations_require_approval()
    test_read_only_operations_do_not_require_approval()
    print("operation_registry tests passed")
