"""Tests for `patchpilot.diff_parser` and `patchpilot.aegis_bridge` (v1.1.0)."""

from __future__ import annotations

import hashlib
import json
import pytest

from patchpilot.aegis_bridge import (
    canonical_json_bytes,
    create_aegis_g5_leaf,
    create_aegis_g5_payload,
    hash_leaf_bytes,
)
from patchpilot.diff_parser import (
    audit_unified_diff,
    parse_unified_diff,
    reconstruct_file_pairs_from_diff,
)
from patchpilot.guard import PatchIntegrityGuard
from patchpilot.server import PatchPilotMCPServer


SAMPLE_CLEAN_DIFF = """\
diff --git a/src/math_lib.py b/src/math_lib.py
--- a/src/math_lib.py
+++ b/src/math_lib.py
@@ -1,5 +1,5 @@
 def add_positive(a: int, b: int) -> int:
-    return a - b
+    return a + b
"""

SAMPLE_MULTI_FILE_DIFF = """\
diff --git a/src/service.py b/src/service.py
--- a/src/service.py
+++ b/src/service.py
@@ -10,6 +10,6 @@
 def process():
-    return 10
+    return 20
diff --git a/tests/test_service.py b/tests/test_service.py
--- a/tests/test_service.py
+++ b/tests/test_service.py
@@ -5,5 +5,5 @@
 def test_service():
-    assert process() == 10
+    assert process() == 20
"""

SAMPLE_REWARD_HACK_DELETED_TEST = """\
diff --git a/tests/test_auth.py b/tests/test_auth.py
--- a/tests/test_auth.py
+++ b/tests/test_auth.py
@@ -1,7 +1,3 @@
-def test_jwt_validation():
-    assert validate_token("invalid") is False
-
 def test_dummy():
     assert 1 == 1
"""

SAMPLE_REWARD_HACK_SWALLOWED_EXC = """\
diff --git a/src/handler.py b/src/handler.py
--- a/src/handler.py
+++ b/src/handler.py
@@ -1,4 +1,6 @@
 def handle():
-    return risky_call()
+    try:
+        return risky_call()
+    except Exception:
+        pass
"""

SAMPLE_REWARD_HACK_DANGEROUS_EVAL = """\
diff --git a/src/runner.py b/src/runner.py
--- a/src/runner.py
+++ b/src/runner.py
@@ -1,4 +1,4 @@
 def execute_cmd(payload):
-    return safe_run(payload)
+    return eval(payload)
"""


class TestDiffParser:
    def test_parse_single_file_diff(self):
        parsed = parse_unified_diff(SAMPLE_CLEAN_DIFF)
        assert len(parsed.files) == 1
        f = parsed.files[0]
        assert f.old_path == "src/math_lib.py"
        assert f.new_path == "src/math_lib.py"
        assert len(f.hunks) == 1
        assert f.hunks[0].old_start == 1
        assert f.hunks[0].new_start == 1

    def test_parse_multi_file_diff(self):
        parsed = parse_unified_diff(SAMPLE_MULTI_FILE_DIFF)
        assert len(parsed.files) == 2
        assert parsed.file_paths == ["src/service.py", "tests/test_service.py"]

    def test_reconstruct_file_pairs(self):
        before, after = reconstruct_file_pairs_from_diff(SAMPLE_CLEAN_DIFF)
        assert "src/math_lib.py" in before
        assert "src/math_lib.py" in after
        assert "return a - b" in before["src/math_lib.py"]
        assert "return a + b" in after["src/math_lib.py"]

    def test_audit_clean_diff_approved(self):
        report = audit_unified_diff(SAMPLE_CLEAN_DIFF)
        assert report.approved is True
        assert report.risk_score <= 0.15
        assert len(report.violations) == 0
        assert report.diff_stats.files_touched == 1

    def test_audit_diff_catches_deleted_test(self):
        report = audit_unified_diff(SAMPLE_REWARD_HACK_DELETED_TEST)
        assert report.approved is False
        assert any(v.rule_id == "RH001" for v in report.violations)
        assert report.risk_score > 0.5

    def test_audit_diff_catches_swallowed_exception(self):
        report = audit_unified_diff(SAMPLE_REWARD_HACK_SWALLOWED_EXC)
        assert report.approved is False
        assert any(v.rule_id == "RH003" for v in report.violations)

    def test_audit_diff_catches_dangerous_eval(self):
        report = audit_unified_diff(SAMPLE_REWARD_HACK_DANGEROUS_EVAL)
        assert report.approved is False
        assert any(v.rule_id == "RH005" for v in report.violations)

    def test_audit_with_original_files(self):
        orig = {"src/math_lib.py": "def add_positive(a: int, b: int) -> int:\n    return a - b\n"}
        report = audit_unified_diff(SAMPLE_CLEAN_DIFF, original_files=orig)
        assert report.approved is True
        assert report.diff_stats.lines_added == 1
        assert report.diff_stats.lines_removed == 1


class TestAegisBridge:
    def test_canonical_json_bytes_deterministic(self):
        d1 = {"b": 2, "a": 1, "c": [3, 2, 1]}
        d2 = {"a": 1, "c": [3, 2, 1], "b": 2}
        assert canonical_json_bytes(d1) == canonical_json_bytes(d2)
        assert canonical_json_bytes(d1) == b'{"a":1,"b":2,"c":[3,2,1]}'

    def test_hash_leaf_bytes_rfc6962_prefix(self):
        data = b'{"test":true}'
        expected = hashlib.sha256(b"\x00" + data).hexdigest()
        assert hash_leaf_bytes(data) == expected

    def test_create_aegis_g5_payload_approved(self):
        report = audit_unified_diff(SAMPLE_CLEAN_DIFF)
        payload = create_aegis_g5_payload(report, task_id="task_123")
        assert payload["gate_id"] == "G5_ANTI_REWARD_HACK"
        assert payload["passed"] is True
        assert payload["score"] == 1.0
        assert payload["violations"] == []
        assert payload["metrics"]["files_touched"] == 1
        assert payload["metrics"]["task_id"] == "task_123"

    def test_create_aegis_g5_payload_rejected(self):
        report = audit_unified_diff(SAMPLE_REWARD_HACK_DELETED_TEST)
        payload = create_aegis_g5_payload(report, task_id="task_hack")
        assert payload["gate_id"] == "G5_ANTI_REWARD_HACK"
        assert payload["passed"] is False
        assert payload["score"] < 1.0
        assert len(payload["violations"]) > 0
        assert any("RH001" in v for v in payload["violations"])

    def test_create_aegis_g5_leaf_structure(self):
        report = audit_unified_diff(SAMPLE_CLEAN_DIFF)
        leaf = create_aegis_g5_leaf(report, task_id="test_leaf")
        assert leaf["rfc6962_prefix"] == "0x00"
        assert len(leaf["leaf_hash"]) == 64
        assert leaf["canonical_bytes_len"] > 0
        assert leaf["payload"]["gate_id"] == "G5_ANTI_REWARD_HACK"


class TestMCPAuditUnifiedDiff:
    def test_mcp_audit_unified_diff_tool(self):
        server = PatchPilotMCPServer()
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "audit_unified_diff",
                "arguments": {
                    "unified_diff": SAMPLE_CLEAN_DIFF,
                    "export_aegis": True,
                },
            },
        }
        resp = server.handle_request(req)
        assert resp["result"]["isError"] is False
        struct = resp["result"]["structuredContent"]
        assert struct["approved"] is True
        assert "aegis_g5_leaf" in struct
        assert struct["aegis_g5_leaf"]["rfc6962_prefix"] == "0x00"

    def test_mcp_audit_unified_diff_catches_hack(self):
        server = PatchPilotMCPServer()
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "audit_unified_diff",
                "arguments": {
                    "unified_diff": SAMPLE_REWARD_HACK_DANGEROUS_EVAL,
                    "export_aegis": True,
                },
            },
        }
        resp = server.handle_request(req)
        struct = resp["result"]["structuredContent"]
        assert struct["approved"] is False
        assert any(v["rule_id"] == "RH005" for v in struct["violations"])
        assert struct["aegis_g5_leaf"]["payload"]["passed"] is False
