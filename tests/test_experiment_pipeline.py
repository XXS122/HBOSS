import importlib.util
import csv
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def module(self, name):
        path = ROOT / "scripts" / (name + ".py")
        self.assertTrue(path.exists(), f"missing experiment component: {name}")
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_pilot_trains_chain_global_ids_and_evaluates_same_weights(self):
        m = self.module("run_handoff_experiment")
        args = m.parse_args(["--stage", "pilot", "--dry-run"])
        commands = m.build_commands(args, "test_run")
        train = next(cmd for name, cmd in commands if name == "train")
        self.assertIn("train_task_ids=[2,3,5]", train)
        self.assertIn("device=cuda:0", train)
        evals = [cmd for name, cmd in commands if name.startswith("eval_")]
        self.assertEqual(len(evals), 6)
        self.assertEqual(len({cmd[cmd.index("--model-dir")+1] for cmd in evals}), 1)
        self.assertEqual({cmd[cmd.index("--reset-mode")+1] for cmd in evals}, {"original", "none"})

    def test_existing_weights_never_trigger_training(self):
        m = self.module("run_handoff_experiment")
        args = m.parse_args(["--stage", "pilot", "--model-dir", "existing", "--dry-run"])
        self.assertNotIn("train", [name for name, _ in m.build_commands(args, "test_run")])

    def test_comparison_requires_matching_checkpoint_and_budget(self):
        m = self.module("summarize_handoff")
        self.assertTrue(hasattr(m, "compatible"))
        base = dict(checkpoint_hashes={"2": "abc"}, evaluation_seed=1, max_steps=400, init_order="fixed")
        self.assertTrue(m.compatible(base, dict(base)))
        for changed in (dict(base, max_steps=20), dict(base, checkpoint_hashes={"2": "xyz"}), dict(base, evaluation_seed=2)):
            self.assertFalse(m.compatible(base, changed))

    def test_aggregation_pairs_runs_preserves_undefined_rates_and_excludes_failures(self):
        m = self.module("summarize_handoff")
        base = dict(model_ids=[2], training_seeds=[10000], evaluation_seed=20000,
                    max_steps=400, init_order="fixed", episodes=2, success_rate=0.0,
                    prefix_success_rates=[0.0], conditional_success_rates=[0.0],
                    stage_reached_counts=[2], stage_success_counts=[0], mean_steps=400,
                    wall_seconds=1.0, reset_mode="original")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, status, rows in [
                ("original", "complete", [dict(base, name="boss_44/task02"),
                    dict(base, name="ch1/task00", success_rate=0.5),
                    dict(base, name="ch3_1", conditional_success_rates=[0.0, None, None])]),
                ("none", "complete", [dict(base, name="ch3_1", reset_mode="none",
                    conditional_success_rates=[0.0, None, None])]),
                ("failed", "failed", [])]:
                path = root / name
                path.mkdir()
                (path / "manifest.json").write_text(json.dumps(dict(status=status,
                    protocol="boss_bc_diagnostic_v1", checkpoints={"2": {"sha256": "abc"}})))
                if status == "complete":
                    (path / "summary.json").write_text(json.dumps(rows))
            result = m.aggregate(root)
            self.assertEqual(result, dict(complete_task_runs=4, excluded=["failed"], oss_pairs=1, chain_pairs=1))
            with (root / "oss.csv").open(encoding="utf-8-sig", newline="") as f:
                row = next(csv.DictReader(f))
            self.assertEqual(row["rpd"], "")
            self.assertEqual(float(row["drop_pp"]), -50.0)
            self.assertIn("null", (root / "chain_reset_comparison.csv").read_text(encoding="utf-8-sig"))
            # A different checkpoint must not be silently paired, even with the same skill ID.
            path = root / "none/manifest.json"
            manifest = json.loads(path.read_text())
            manifest["checkpoints"]["2"]["sha256"] = "different"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "matched reset baseline"):
                m.aggregate(root)


if __name__ == "__main__":
    unittest.main()
