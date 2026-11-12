"""The frozen-record guard of the protocol builders (protocols/tools/frozen.py)."""
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "protocols" / "tools"))
import frozen  # noqa: E402


class FrozenGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "protocols/specific").mkdir(parents=True)
        (self.repo / "protocols/run_cards").mkdir()
        self.card = self.repo / "protocols/run_cards/card.json"
        self.card.write_text('{"a": 1}\n')
        h = hashlib.sha256(self.card.read_bytes()).hexdigest()
        (self.repo / "protocols/specific/p@0.1.0-draft.yaml").write_text(
            f"status: draft\nrun_cards:\n  - {{path: protocols/run_cards/card.json, sha256: {h}}}\n")
        (self.repo / "protocols/specific/q@1.0.0.yaml").write_text("status: approved\n")
        self.old = (frozen.REPO, frozen._pins, os.environ.pop("ORCHID_FROZEN_CHECK", None), os.environ.pop("ORCHID_FROZEN_LOG", None))
        frozen.REPO = self.repo
        frozen._pins = frozen.pins(repo=self.repo)

    def tearDown(self):
        frozen.REPO, frozen._pins = self.old[0], self.old[1]
        for k, v in (("ORCHID_FROZEN_CHECK", self.old[2]), ("ORCHID_FROZEN_LOG", self.old[3])):
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
        self.tmp.cleanup()

    def test_pinned_file_is_frozen(self):
        self.assertIn("pinned by protocols/specific/p@0.1.0-draft.yaml", frozen.frozen_reason(self.card))
        self.assertIn("approved", frozen.frozen_reason(self.repo / "protocols/specific/q@1.0.0.yaml"))
        self.assertIsNone(frozen.frozen_reason(self.repo / "protocols/specific/p@0.1.0-draft.yaml"))
        self.assertIsNone(frozen.frozen_reason(self.repo / "missing.json"))

    def test_refusal_writes_nothing_and_names_files(self):
        other = self.repo / "protocols/run_cards/new.json"
        log = self.repo / "frozen.log"
        os.environ["ORCHID_FROZEN_LOG"] = str(log)
        w = frozen.Writes("test")
        w.add(other, "{}\n")                    # not frozen, but in the same batch
        w.add(self.card, '{"a": 2}\n')          # frozen, would change
        with self.assertRaises(SystemExit) as e:
            w.commit()
        self.assertEqual(e.exception.code, frozen.EXIT_FROZEN)
        self.assertEqual(self.card.read_text(), '{"a": 1}\n')
        self.assertFalse(other.exists())
        self.assertIn("protocols/run_cards/card.json", log.read_text())

    def test_identical_rewrite_and_new_files_pass(self):
        w = frozen.Writes("test")
        w.add(self.card, '{"a": 1}\n')
        w.add(self.repo / "protocols/run_cards/new.json", "{}\n")
        self.assertEqual(w.commit(), [self.repo / "protocols/run_cards/new.json"])
        self.assertTrue((self.repo / "protocols/run_cards/new.json").exists())

    def test_approved_protocol_cannot_change(self):
        with self.assertRaises(SystemExit):
            frozen.write(self.repo / "protocols/specific/q@1.0.0.yaml", "status: approved\nx: 1\n")

    def test_check_mode_writes_nothing(self):
        os.environ["ORCHID_FROZEN_CHECK"] = "1"
        p = self.repo / "protocols/run_cards/new.json"
        self.assertEqual(frozen.Writes("test").commit(), [])
        frozen.write(p, "{}\n")
        self.assertFalse(p.exists())

    def test_cli_reports(self):
        r = subprocess.run([sys.executable, str(ROOT / "protocols/tools/frozen.py"), str(ROOT / "README.md")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("README.md", r.stdout)


class PinnedRationale(unittest.TestCase):
    """orchid-calphad-fit@2.0.0 and @2.1.0 pin earlier texts of docs/fit_protocol.md; the validator resolves them by hash."""

    def test_frozen_versions_resolve(self):
        import validate
        import orchidproto as op
        for v in ("2.0.0", "2.1.0", "2.1.1", "2.1.2"):
            g = op.load_doc(ROOT / f"protocols/general/orchid-calphad-fit@{v}.yaml")
            r = g["rationale_document"]
            f = op.expand(r["path"])
            h = op.sha256_file(f)
            if h == r["sha256"] or validate.public_copies().get("docs/fit_protocol.md") == (r["sha256"], h):
                continue                              # the living text (or, in a public copy, its sanitized copy)
            fv = validate.frozen_version(f, r["sha256"])
            self.assertIsNotNone(fv, v)
            self.assertEqual(fv.name, f"fit_protocol@{v}.md")

    def test_unknown_hash_not_resolved(self):
        import validate
        self.assertIsNone(validate.frozen_version(ROOT / "docs/fit_protocol.md", "0" * 64))


if __name__ == "__main__":
    unittest.main()
