"""CPU regression tests; execute actual SequentialEnv methods without MuJoCo."""
import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


class FakeEnv:
    def __init__(self, **kwargs):
        self.value = 0
        self.seeds = []

    def reset(self):
        self.value = 0
        return {"value": self.value}

    def seed(self, seed):
        self.seeds.append(seed)

    def set_init_state(self, state):
        self.value = state
        return {"value": self.value, "fresh": True}

    def get_sim_state(self):
        return self.value

    def step(self, action):
        self.value += 1
        return {"value": self.value}, 1, True, {}


def sequential_class():
    path = ROOT / "libero/libero/envs/env_wrapper.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SequentialEnv")
    namespace = {"np": np, "OffScreenRenderEnv": FakeEnv}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["SequentialEnv"]


class SequentialTests(unittest.TestCase):
    def make_env(self):
        return sequential_class()(2, [], bddl_file_name=["a", "b"],
                                  camera_heights=[128, 128], camera_widths=[128, 128])

    def test_seed_reaches_children_as_integer(self):
        env = self.make_env()
        env.seed(123)
        self.assertEqual([e.seeds for e in env.env_ls], [[123], [123]])

    def test_reset_clears_previous_episode_success(self):
        env = self.make_env()
        env.reset()
        env.step(None)
        env.step(None)
        env.reset()
        self.assertEqual(env.task_dones, [False, False])
        self.assertEqual(env.complete_task, [])
        self.assertEqual(env.complete_id, -1)
        self.assertIsInstance(env.reset(), dict)

    def test_handoff_returns_successor_observation(self):
        env = self.make_env()
        env.reset()
        obs, _, done, info = env.step(None)
        self.assertTrue(obs.get("fresh"), "successor state must be rendered before its first action")
        self.assertFalse(done)
        self.assertEqual(info["task_index"], 1)
        self.assertEqual(info["complete_id"], 0)


class DiagnosticHelpersTests(unittest.TestCase):
    def helper(self):
        path = ROOT / "libero/lifelong/handoff_metrics.py"
        self.assertTrue(path.exists(), "diagnostic metrics implementation is missing")
        spec = importlib.util.spec_from_file_location("handoff_metrics", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_conditional_rate_uses_reached_boundary_denominator(self):
        m = self.helper()
        rows = [{"completed": n, "steps": 10} for n in [0, 1, 2, 3]]
        result = m.summarize(rows, 3)
        self.assertEqual(result["prefix_success_rates"], [0.75, 0.5, 0.25])
        self.assertEqual(result["conditional_success_rates"], [0.75, 2/3, 0.5])
        self.assertEqual(result["success_rate"], 0.25)

    def test_unreached_stage_and_zero_baseline_are_null(self):
        m = self.helper()
        self.assertEqual(m.summarize([{"completed": 0, "steps": 1}], 3)["conditional_success_rates"], [0.0, None, None])
        self.assertIsNone(m.rpd(0.0, 0.0))
        self.assertAlmostEqual(m.rpd(0.8, 0.6), 0.25)

    def test_original_reset_copies_only_legacy_slices(self):
        m = self.helper()
        current = np.arange(77, dtype=float)
        reference = np.full(77, -1.0)
        result = m.reset_robot_state(current, reference, "original")
        np.testing.assert_array_equal(result[10:41], current[10:41])
        np.testing.assert_array_equal(result[1:10], reference[1:10])
        np.testing.assert_array_equal(result[41:], reference[41:])
        np.testing.assert_array_equal(current, np.arange(77))
        np.testing.assert_array_equal(m.reset_robot_state(current, reference, "none"), current)
        with self.assertRaises(ValueError):
            m.reset_robot_state(current, reference[:70], "original")

    def test_mapping_matches_names_not_dictionary_order(self):
        m = self.helper()
        mapping = {"B.bddl": ["B_changed.bddl"], "A.bddl": ["A_changed.bddl"]}
        self.assertEqual(m.model_index("A_changed.bddl", ["A", "B"], mapping), 0)
        with self.assertRaises(ValueError):
            m.model_index("missing.bddl", ["A", "B"], mapping)

    def test_training_task_selection_preserves_global_ids(self):
        m = self.helper()
        self.assertTrue(hasattr(m, "select_task_ids"), "global training task selection is missing")
        self.assertEqual(m.select_task_ids(44, [2, 3, 5]), [2, 3, 5])
        self.assertEqual(m.select_task_ids(3, None), [0, 1, 2])
        for bad in ([44], [-1], [2, 2], []):
            with self.assertRaises(ValueError):
                m.select_task_ids(44, bad)


if __name__ == "__main__":
    unittest.main()
