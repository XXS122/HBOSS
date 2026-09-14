import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from libero.lifelong.diagnose_handoff import file_hash
from libero.lifelong.handoff_ablation import POSITION_MODES, intervene
from libero.lifelong.handoff_pool import load_replay_pool


class PositionTests(unittest.TestCase):
    def test_four_groups_only_change_selected_positions_and_robot_velocities(self):
        layout = dict(nq=12, nv=11, arm_qpos=[3, 1], gripper_qpos=[8, 6],
                      arm_qvel=[2, 0], gripper_qvel=[7, 5])
        state = np.arange(24, dtype=float) + 1
        reference = -state
        groups = dict(keep_position=[], reset_arm=[4, 2], reset_gripper=[9, 7],
                      reset_both=[4, 2, 9, 7])
        self.assertEqual(set(POSITION_MODES), set(groups))
        for mode, indexes in groups.items():
            expected = state.copy()
            expected[[15, 13, 20, 18]] = 0
            expected[indexes] = reference[indexes]
            np.testing.assert_array_equal(intervene(state, reference, layout, mode), expected)
        np.testing.assert_array_equal(intervene(state, reference, layout, 'keep_position'),
                                      intervene(state, reference, layout, 'velocity'))
        np.testing.assert_array_equal(intervene(state, reference, layout, 'reset_both'),
                                      intervene(state, reference, layout, 'both'))
        np.testing.assert_array_equal(state, np.arange(24) + 1)

    def make_source(self, root):
        layout = dict(nq=12, nv=11)
        manifest = dict(status='complete', protocol='paired_handoff_ablation_v2',
            states_collected=3, tasks=['bottom', 'top'], policy_budget=400, control_hz=20,
            torch='2.4.1', robosuite='1.4.1', mujoco='3.2.3', training_seeds=[10000, 10000],
            initial_state_counts=[3, 3], init_states_sha256={'2': 'init2', '3': 'init3'},
            bddl_sha256={'2': 'bddl2', '3': 'bddl3'}, eval_seeds=[10000, 20000, 30000],
            checkpoints={'2': {'sha256': 'model2'}, '3': {'sha256': 'model3'}},
            code_sha256={'libero/libero/envs/env_wrapper.py': 'wrapper'})
        (root / 'manifest.json').write_text(json.dumps(manifest))
        (root / 'joint_layout.json').write_text(json.dumps(layout))
        (root / 'snapshots').mkdir()
        rows = []
        for i in range(3):
            path = root / 'snapshots' / f'state{i:03d}.npz'
            np.savez(path, terminal=np.arange(24.) + i, reference=-np.arange(24.))
            rows.append(dict(accepted=True, initial_valid=True, state_id=i, initial_index=i,
                seed=10+i, attempt=i, reference_index=i, snapshot=path.name, sha256=file_hash(path)))
        (root / 'collection.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
        return manifest, layout

    def test_replay_preserves_state_ids_seeds_and_source_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, layout = self.make_source(root)
            before = {str(p): file_hash(p) for p in root.rglob('*') if p.is_file()}
            pool, provenance = load_replay_pool(root, 2, manifest, layout, [10000])
            self.assertEqual([r['state_id'] for _, _, r in pool], [0, 1])
            self.assertEqual([r['seed'] for _, _, r in pool], [10, 11])
            np.testing.assert_array_equal(pool[1][0], np.arange(24.) + 1)
            self.assertEqual(provenance['source_states_collected'], 3)
            self.assertEqual(before, {str(p): file_hash(p) for p in root.rglob('*') if p.is_file()})

    def test_replay_rejects_changed_weights_seed_or_missing_states(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, layout = self.make_source(root)
            changed = json.loads(json.dumps(manifest))
            changed['checkpoints']['3']['sha256'] = 'different-model'
            for count, current, seeds in [(2, changed, [10000]), (4, manifest, [10000]),
                                          (2, manifest, [999])]:
                with self.assertRaises(ValueError):
                    load_replay_pool(root, count, current, layout, seeds)

    def test_replay_rejects_modified_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, layout = self.make_source(root)
            np.savez(root / 'snapshots/state000.npz', terminal=np.zeros(24), reference=np.zeros(24))
            with self.assertRaises(ValueError):
                load_replay_pool(root, 2, manifest, layout, [10000])

    def test_replay_rejects_incomplete_source_and_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, layout = self.make_source(root)
            incomplete = dict(manifest, status='running')
            (root / 'manifest.json').write_text(json.dumps(incomplete))
            with self.assertRaises(ValueError):
                load_replay_pool(root, 2, manifest, layout, [10000])
            (root / 'manifest.json').write_text(json.dumps(manifest))
            log = root / 'collection.jsonl'
            lines = log.read_text().splitlines()
            log.write_text('\n'.join([lines[0], lines[0], lines[2]]))
            with self.assertRaises(ValueError):
                load_replay_pool(root, 2, manifest, layout, [10000])


if __name__ == '__main__':
    unittest.main()
