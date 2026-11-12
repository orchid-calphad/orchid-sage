import io
import json
import os
import subprocess
import sys
import unittest

from sage_mcp import server
from sage_mcp.tests.helpers import CRNI, REPO, SageTestCase

EXPECTED = {
    "list_protocols", "get_protocol", "get_steps", "get_step", "get_run_cards", "get_decisions", "get_evidence_manifest", "get_evidence_links",
    "get_dashboard_data", "get_open_questions", "validate", "verify_inputs", "plan_reproduction", "run_step", "start_step", "step_status", "compare_outputs",
    "new_assessment", "gather_evidence", "next_step", "record_decision", "record_external_run", "modify_protocol",
    "propose_general_change", "migrate", "get_history", "package", "list_backends", "compute_ids",
}


def _rpc(proc, mid, method, params=None):
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": mid, "method": method, "params": params or {}}) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


class Server(SageTestCase):
    def test_tool_schemas(self):
        tools = {t["name"]: t for t in server.tool_descriptions()}
        self.assertEqual(set(tools), EXPECTED)
        rs = tools["run_step"]["inputSchema"]
        self.assertEqual(rs["required"], ["protocol", "step_id", "run_root"])
        self.assertEqual(rs["properties"]["confirm"]["default"], False)
        self.assertEqual(rs["properties"]["allow_long"]["default"], False)
        self.assertEqual(tools["modify_protocol"]["inputSchema"]["properties"]["change"]["type"], "object")

    def test_resources(self):
        res = server.resources()
        self.assertIn("sage://protocol/orchid-calphad-fit@2.0.0.yaml", res)
        self.assertIn(f"sage://protocol/{CRNI}.md", res)
        self.assertIn("sage://schema/protocol.schema.json", res)
        self.assertIn("sage://evidence/crni-paper-fit-step4-s1/manifest", res)
        self.assertTrue(any(u.startswith("sage://run-card/") for u in res))
        self.assertTrue(any(u.startswith("sage://dashboard/") for u in res))

    def test_fallback_survives_bad_messages(self):
        out = io.StringIO()
        server.run_fallback_stdio(io.StringIO('[1]\n{"jsonrpc": "2.0", "id": 1, "method": "ping"}\n'), out)
        lines = [json.loads(x) for x in out.getvalue().splitlines()]
        self.assertEqual(lines[0]["error"]["code"], -32600)
        self.assertEqual(lines[1]["result"], {})
        bad = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": ["x"]}})
        self.assertEqual(bad["error"]["code"], -32602)

    def _smoke(self, fallback):
        env = {**os.environ, "PYTHONPATH": str(REPO)}
        cmd = [sys.executable, "-m", "sage_mcp"] + (["--fallback"] if fallback else [])
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=str(self.tmp))
        try:
            init = _rpc(proc, 1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}})
            self.assertEqual(init["result"]["serverInfo"]["name"], "orchid-sage")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            tools = _rpc(proc, 2, "tools/list")["result"]["tools"]
            self.assertEqual({t["name"] for t in tools}, EXPECTED)
            call = _rpc(proc, 3, "tools/call", {"name": "get_step", "arguments": {"protocol": CRNI, "step_id": "step4"}})
            payload = json.loads(call["result"]["content"][0]["text"])
            self.assertEqual(payload["reproduce_item"]["kind"], "numerical")
            bad = _rpc(proc, 4, "tools/call", {"name": "get_protocol", "arguments": {"protocol": "no-such@1.0.0"}})
            self.assertTrue(bad["result"]["isError"])
            res = _rpc(proc, 5, "resources/list")["result"]["resources"]
            self.assertIn("sage://schema/common.schema.json", {r["uri"] for r in res})
            txt = _rpc(proc, 6, "resources/read", {"uri": "sage://docs/SCHEMA.md"})["result"]["contents"][0]["text"]
            self.assertIn("orchid-assessment-schema", txt)
            pr = _rpc(proc, 7, "prompts/list")["result"]["prompts"]
            self.assertEqual({p["name"] for p in pr}, {"reproduce_assessment", "explain_assessment", "run_fresh_assessment"})
            msg = _rpc(proc, 8, "prompts/get", {"name": "reproduce_assessment", "arguments": {"protocol": CRNI, "run_root": "/tmp/x"}})
            self.assertIn("plan_reproduction", msg["result"]["messages"][0]["content"]["text"])
        finally:
            proc.stdin.close()
            proc.wait(timeout=20)
            proc.stdout.close()
            proc.stderr.close()

    def test_stdio_fallback(self):
        self._smoke(True)

    @unittest.skipUnless(server.sdk_available(), "mcp SDK not installed in this interpreter")
    def test_stdio_sdk(self):
        self._smoke(False)


if __name__ == "__main__":
    unittest.main()
