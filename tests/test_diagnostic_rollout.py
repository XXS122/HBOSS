import importlib.util
from pathlib import Path
import unittest


class RolloutTests(unittest.TestCase):
    def runner(self):
        path = Path(__file__).resolve().parents[1] / "libero/lifelong/diagnose_handoff.py"
        self.assertTrue(path.exists(), "diagnostic rollout implementation is missing")
        spec = importlib.util.spec_from_file_location("diagnose_handoff", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_successor_uses_reset_observation_and_stops_on_success(self):
        module = self.runner()

        class Env:
            task_id = 0
            n_tasks = 2
            def step(self, action):
                old = self.task_id
                self.task_id = 1
                return "transferred", 1, old == 1, {"is_init": old == 0, "task_index": 1, "complete_id": old}

        actions, boundaries = [], []
        def act(stage, obs):
            actions.append((stage, obs))
            return None
        def enter(stage, obs, step):
            boundaries.append((stage, step))
            return "reset_observation"
        result = module.rollout(Env(), "initial", act, enter, 8)
        self.assertEqual(actions, [(0, "initial"), (1, "reset_observation")])
        self.assertEqual(boundaries, [(1, 1)])
        self.assertEqual(result["completed"], 2)
        self.assertEqual(result["steps"], 2)
        self.assertEqual(result["stage_steps"], [1, 1])

    def test_timeout_does_not_count_unfinished_skill_as_success(self):
        module = self.runner()
        class Env:
            task_id = 0
            n_tasks = 1
            def step(self, action):
                return "same", 0, False, {"is_init": False, "task_index": 0, "complete_id": -1}
        result = module.rollout(Env(), "initial", lambda *x: None, lambda *x: None, 3)
        self.assertEqual(result["completed"], 0)
        self.assertEqual(result["steps"], 3)
        self.assertEqual(result["termination"], "budget_exhausted")


if __name__ == "__main__":
    unittest.main()
