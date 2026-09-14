import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from libero.lifelong.handoff_ablation import joint_layout, intervene, stopped, evaluate_stage, wait_until_stopped, sync_controller, settle


class AblationTests(unittest.TestCase):
    def layout(self):
        return dict(nq=12, nv=11, arm_qpos=[3, 1], gripper_qpos=[8, 6],
                    arm_qvel=[2, 0], gripper_qvel=[7, 5])

    def test_joint_names_determine_addresses(self):
        model = SimpleNamespace(nq=12, nv=11, na=0, joint_names=['object', 'arm', 'finger'],
            get_joint_qpos_addr=lambda n: dict(object=(0, 7), arm=7, finger=8)[n],
            get_joint_qvel_addr=lambda n: dict(object=(0, 6), arm=6, finger=7)[n])
        env = SimpleNamespace(sim=SimpleNamespace(model=model),
            robots=[SimpleNamespace(robot_joints=['arm'], gripper_joints=['finger'])])
        layout = joint_layout(env)
        self.assertEqual(layout['arm_qpos'], [7])
        self.assertEqual(layout['gripper_qvel'], [7])
        self.assertEqual(layout['joints'][0]['qvel'], [0, 6])

    def test_interventions_change_only_named_components(self):
        state = np.arange(24, dtype=float) + 1
        reference = -state
        for mode, positions, velocities in [('none', False, False), ('settle', False, False),
                ('position', True, False), ('velocity', False, True), ('both', True, True)]:
            expected = state.copy()
            if positions:
                expected[[4, 2, 9, 7]] = reference[[4, 2, 9, 7]]
            if velocities:
                expected[[15, 13, 20, 18]] = 0
            actual = intervene(state, reference, self.layout(), mode)
            np.testing.assert_array_equal(actual, expected)
            self.assertFalse(np.shares_memory(actual, state))
        np.testing.assert_array_equal(state, np.arange(24) + 1)

    def test_legacy_preserves_existing_slices(self):
        layout = self.layout() | dict(nq=26, nv=24)
        state = np.arange(51, dtype=float)
        reference = -state
        actual = intervene(state, reference, layout, 'legacy')
        expected = state.copy()
        expected[1:10] = reference[1:10]
        expected[41:] = reference[41:]
        np.testing.assert_array_equal(actual, expected)

    def test_invalid_state_rejected(self):
        for state in [np.zeros(23), np.full(24, np.nan)]:
            with self.assertRaises(ValueError):
                intervene(state, state, self.layout(), 'none')

    def test_stop_checks_arm_and_fingers(self):
        velocities = np.zeros(11)
        self.assertTrue(stopped(velocities, self.layout()))
        velocities[7] = .003
        self.assertFalse(stopped(velocities, self.layout()))
        velocities[7] = 0
        velocities[2] = .03
        self.assertFalse(stopped(velocities, self.layout()))

    def test_goal_recovery_does_not_erase_earlier_violation(self):
        step = [0]
        def advance(obs):
            step[0] += 1
            return step[0]
        row, obs = evaluate_stage(0, advance, lambda: step[0] == 3,
            lambda: step[0] != 1, 4)
        self.assertTrue(row['success'])
        self.assertTrue(row['predecessor_final'])
        self.assertFalse(row['predecessor_always'])
        self.assertEqual(row['policy_steps'], 3)

    def test_budget_and_settle_violation(self):
        row, _ = evaluate_stage(0, lambda obs: obs + 1, lambda: False,
                               lambda: True, 4, preserved=False)
        self.assertEqual(row['policy_steps'], 4)
        self.assertFalse(row['success'])
        self.assertFalse(row['predecessor_always'])

    def test_wait_requires_five_consecutive_steps(self):
        # One moving sample must restart the counter.
        samples = iter([True, True, False, True, True, True, True, True])
        obs, steps, success, preserved = wait_until_stopped(0, lambda x: x + 1,
            lambda: next(samples), lambda: True)
        self.assertEqual((obs, steps, success, preserved), (8, 8, True, True))

    def test_wait_timeout_keeps_failed_goal_measurement(self):
        current = [0]
        def advance(obs):
            current[0] += 1
            return current[0]
        obs, steps, success, preserved = wait_until_stopped(0, advance, lambda: False,
            lambda: current[0] != 2, max_steps=40)
        self.assertEqual((steps, success, preserved), (40, False, False))

    def test_controller_restoration_keeps_physics_and_sets_gripper_hold(self):
        class Controller:
            name = 'OSC_POSE'
            impedance_mode = 'fixed'
            def update(self, force=False):
                self.updated = force
            def update_initial_joints(self, joints):
                self.initial_joint = joints
            def reset_goal(self):
                self.goal_pos = np.array([1., 2., 3.])
        class PandaGripper:
            actuators = ['left_actuator', 'right_actuator']
        controller = Controller()
        robot = SimpleNamespace(controller=controller, gripper=PandaGripper(),
                                gripper_joints=['left', 'right'])
        data = SimpleNamespace(qpos=np.array([9., 8., .01, -.01]),
                               qvel=np.array([1., 2., 3., 4.]), ctrl=np.zeros(2))
        model = SimpleNamespace(actuator_name2id=lambda n: ['left_actuator', 'right_actuator'].index(n),
            joint_name2id=lambda n: ['left', 'right'].index(n),
            actuator_trnid=np.array([[0, -1], [1, -1]]), actuator_trntype=np.zeros(2, dtype=int),
            actuator_gear=np.ones((2, 6)), actuator_ctrlrange=np.array([[0., .04], [-.04, 0.]]))
        env = SimpleNamespace(robots=[robot], sim=SimpleNamespace(model=model, data=data))
        before_pos, before_vel = data.qpos.copy(), data.qvel.copy()
        sync_controller(env, np.array([0., 4., 5., .02, -.02]),
                        dict(arm_qpos=[0, 1], gripper_qpos=[2, 3]))
        np.testing.assert_array_equal(controller.initial_joint, [4., 5.])
        np.testing.assert_allclose(robot.gripper.current_action, [-.5, .5])
        np.testing.assert_allclose(data.ctrl, [.01, -.01])
        np.testing.assert_array_equal(data.qpos, before_pos)
        np.testing.assert_array_equal(data.qvel, before_vel)

    def test_settle_keeps_fixed_target_despite_pose_drift_and_restores_method(self):
        goals = []
        class Controller:
            ee_pos = np.array([1., 2., 3.])
            ee_ori_mat = np.eye(3)
            def update(self, force=False):
                pass
            def update_initial_joints(self, joints):
                pass
            def set_goal(self, action, set_pos=None, set_ori=None):
                goals.append(set_pos.copy())
        controller = Controller()
        original = controller.set_goal
        def step(action):
            np.testing.assert_array_equal(action, np.zeros(7))
            controller.set_goal(action[:6])
            controller.ee_pos = controller.ee_pos + .01
            return 0, 0, False, {}
        env = SimpleNamespace(robots=[SimpleNamespace(controller=controller)], step=step,
            sim=SimpleNamespace(data=SimpleNamespace(qpos=np.zeros(12), qvel=np.zeros(11))))
        with patch('libero.lifelong.handoff_ablation.sync_controller') as sync:
            _, steps, success, _ = settle(env, 0, np.zeros(24), self.layout(), lambda: True)
        self.assertEqual((steps, success), (5, True))
        self.assertEqual(controller.set_goal, original)
        sync.assert_called_once()
        for goal in goals:
            np.testing.assert_array_equal(goal, [1., 2., 3.])


if __name__ == '__main__':
    unittest.main()
