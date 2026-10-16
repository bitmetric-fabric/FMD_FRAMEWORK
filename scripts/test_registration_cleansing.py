"""Check that the registration editor knows the built-in cleansing functions. No dependencies, no network.

    python3 scripts/test_registration_cleansing.py

The editor lists the functions from CLEANSING_FUNCTIONS in NB_FMD_REGISTRATION_FUNCTIONS, a hand-kept mirror of the
built-ins that NB_FMD_DQ_CLEANSING registers. A built-in missing from the mirror cannot be picked in the dropdown.
"""

import ast
import json
import re
import sys
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
EDITOR = REPO / "src/NB_FMD_REGISTRATION_FUNCTIONS.Notebook/notebook-content.py"
CLEANSING = REPO / "src/NB_FMD_DQ_CLEANSING.Notebook/notebook-content.py"


def load_editor():
    """CLEANSING_FUNCTIONS and validate_rule, taken from the notebook without running the rest of it."""
    tree = ast.parse(EDITOR.read_text(encoding="utf-8"))
    wanted = []
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "CLEANSING_FUNCTIONS" for t in n.targets):
            wanted.append(n)
        if isinstance(n, ast.FunctionDef) and n.name == "validate_rule":
            wanted.append(n)
    namespace = {"re": re, "json": json}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(EDITOR), "exec"), namespace)
    return namespace


def test_every_built_in_is_in_the_editor():
    built_in = set(re.findall(r'^register_cleansing_function\("(\w+)"', CLEANSING.read_text(encoding="utf-8"), re.M))
    assert built_in, "no built-in functions found in NB_FMD_DQ_CLEANSING"
    missing = built_in - set(load_editor()["CLEANSING_FUNCTIONS"])
    assert not missing, f"missing from CLEANSING_FUNCTIONS in NB_FMD_REGISTRATION_FUNCTIONS: {sorted(missing)}"


def test_exclude_rows_needs_values():
    validate_rule = load_editor()["validate_rule"]

    def errors(rule):
        return [m for level, m in validate_rule(rule) if level == "error"]

    ok = {"function": "exclude_rows", "columns": "EVENT_CRUD", "parameters": {"values": ["delete"]}}
    assert errors(ok) == []
    assert errors({**ok, "parameters": {}}), "values missing must be an error"
    assert errors({**ok, "parameters": {"values": []}}), "empty values must be an error"
    assert errors({**ok, "columns": ""}), "no columns must be an error"


def test_other_functions_do_not_need_values():
    validate_rule = load_editor()["validate_rule"]
    rule = {"function": "normalize_text", "columns": "Name", "parameters": {"case": "upper"}}
    assert [m for level, m in validate_rule(rule) if level == "error"] == []


def test_list_placeholder_is_not_date_specific():
    source = EDITOR.read_text(encoding="utf-8")
    assert "placeholder='yyyy-MM-dd, dd/MM/yyyy'" not in source, "list placeholder must come from the parameter"


if __name__ == "__main__":
    failed = 0
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            try:
                test()
                print(f"ok    {name}")
            except AssertionError as e:
                failed += 1
                print(f"FAIL  {name}: {e}")
    sys.exit(1 if failed else 0)
