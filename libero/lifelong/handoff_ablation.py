"""State interventions and measurements for the paired task-2 to task-3 test."""
import numpy as np

MODES = ('none', 'position', 'velocity', 'both', 'settle', 'legacy')
POSITION_MODES = ('keep_position', 'reset_arm', 'reset_gripper', 'reset_both')


def collection_attempts(n_initial, requested):
    """Cycle initial states with fresh reproducible rollout seeds; bounded retries."""
    for attempt in range(requested * 10):
        yield dict(attempt=attempt, initial_index=attempt % n_initial,
                   seed=int(np.random.SeedSequence([10000, attempt]).generate_state(1)[0]))


def joint_layout(env):
    model, robot = env.sim.model, env.robots[0]
    def address(name, kind):
        value = getattr(model, 'get_joint_' + kind + '_addr')(name)
        return list(map(int, value)) if isinstance(value, tuple) else int(value)
    result = dict(nq=int(model.nq), nv=int(model.nv), na=int(model.na),
                  joints=[dict(name=n, qpos=address(n, 'qpos'), qvel=address(n, 'qvel'))
                          for n in model.joint_names])
    if result['na']:
        raise ValueError('This protocol requires stateless actuators (na=0)')
    for group, names in [('arm', robot.robot_joints), ('gripper', robot.gripper_joints)]:
        result[group + '_names'] = list(names)
        for kind in ['qpos', 'qvel']:
            values = [address(n, kind) for n in names]
            if not values or any(not isinstance(v, int) for v in values):
                raise ValueError('Expected scalar robot and gripper joints')
            result[group + '_' + kind] = values
    return result


def intervene(state, reference, layout, mode):
    if mode not in MODES + POSITION_MODES:
        raise ValueError(mode)
    state, reference = np.asarray(state), np.asarray(reference)
    if (state.shape != (1 + layout['nq'] + layout['nv'],) or reference.shape != state.shape
            or not np.isfinite(state).all() or not np.isfinite(reference).all()):
        raise ValueError('Invalid flattened simulator state')
    result = state.copy()
    if mode in ('position', 'both', 'reset_both'):
        indexes = np.array(layout['arm_qpos'] + layout['gripper_qpos']) + 1
        result[indexes] = reference[indexes]
    elif mode in ('reset_arm', 'reset_gripper'):
        group = 'arm_qpos' if mode == 'reset_arm' else 'gripper_qpos'
        indexes = np.array(layout[group]) + 1
        result[indexes] = reference[indexes]
    if mode in ('velocity', 'both') or mode in POSITION_MODES:
        indexes = np.array(layout['arm_qvel'] + layout['gripper_qvel']) + 1 + layout['nq']
        result[indexes] = 0
    if mode == 'legacy':
        if len(state) < 42:
            raise ValueError('Legacy slices require at least 42 state entries')
        result[1:10] = reference[1:10]
        result[41:] = reference[41:]
    return result


def stopped(qvel, layout):
    return bool(np.max(np.abs(qvel[layout['arm_qvel']])) <= .02
                and np.max(np.abs(qvel[layout['gripper_qvel']])) <= .002)


def wait_until_stopped(obs, advance, is_stopped, predecessor, max_steps=40):
    consecutive = 0
    preserved = bool(predecessor())
    for step in range(1, max_steps + 1):
        obs = advance(obs)
        preserved = bool(predecessor()) and preserved
        consecutive = consecutive + 1 if is_stopped() else 0
        if consecutive >= 5:
            return obs, step, True, preserved
    return obs, max_steps, False, preserved


def evaluate_stage(obs, advance, successor, predecessor, max_steps, preserved=True):
    preserved = bool(predecessor()) and preserved
    success = bool(successor())
    steps = 0
    while not success and steps < max_steps:
        obs = advance(obs)
        steps += 1
        preserved = bool(predecessor()) and preserved
        success = bool(successor())
    return dict(success=success, policy_steps=steps, predecessor_always=preserved,
                predecessor_final=bool(predecessor())), obs


def sync_controller(env, reference, layout):
    """Initialize every branch by the same rule, without taking a physics step.

    OSC nullspace target uses the reference arm configuration. The pose target
    and the Panda gripper's incremental command use the restored current pose.
    This is an explicit evaluation convention, not a clone of controller history.
    """
    robot = env.robots[0]
    controller = robot.controller
    if (controller.name != 'OSC_POSE' or controller.impedance_mode != 'fixed'
            or type(robot.gripper).__name__ != 'PandaGripper'):
        raise ValueError('This experiment supports fixed OSC_POSE and PandaGripper only')
    controller.update(force=True)
    controller.update_initial_joints(reference[1 + np.array(layout['arm_qpos'])].copy())
    controller.reset_goal()
    ids = [env.sim.model.actuator_name2id(n) for n in robot.gripper.actuators]
    joint_ids = [env.sim.model.joint_name2id(n) for n in robot.gripper_joints]
    if (len(ids) != len(joint_ids)
            or not np.array_equal(env.sim.model.actuator_trnid[ids, 0], joint_ids)
            or not np.all(env.sim.model.actuator_trntype[ids] == 0)
            or not np.allclose(env.sim.model.actuator_gear[ids, 0], 1)):
        raise ValueError('Unsupported gripper actuator-to-joint mapping')
    limits = env.sim.model.actuator_ctrlrange[ids]
    midpoint = limits.mean(axis=1)
    half_range = (limits[:, 1] - limits[:, 0]) / 2
    if np.any(half_range <= 0):
        raise ValueError('Invalid gripper control range')
    qpos = env.sim.data.qpos[layout['gripper_qpos']]
    robot.gripper.current_action = np.clip((qpos - midpoint) / half_range, -1, 1)
    env.sim.data.ctrl[ids] = midpoint + half_range * robot.gripper.current_action
    return dict(nullspace_target=controller.initial_joint.tolist(),
                pose_target=controller.goal_pos.tolist(),
                gripper_command=robot.gripper.current_action.tolist())


def restore(env, state, reference, layout):
    env.set_init_state(state)
    # Flat state excludes these inputs / solver history. Normalize all branches.
    env.sim.data.ctrl[:] = 0
    env.sim.data.qfrc_applied[:] = 0
    env.sim.data.xfrc_applied[:] = 0
    env.sim.data.qacc_warmstart[:] = 0
    env.sim.forward()
    metadata = sync_controller(env, reference, layout)
    env.env._update_observables(force=True)
    obs = env.env._get_observations()
    if not np.allclose(env.get_sim_state(), state, atol=1e-10, rtol=0):
        raise RuntimeError('State changed during restoration without a physics step')
    return obs, metadata


def settle(env, obs, reference, layout, predecessor, frame=None):
    controller = env.robots[0].controller
    controller.update(force=True)
    position, orientation = controller.ee_pos.copy(), controller.ee_ori_mat.copy()
    controller.update_initial_joints(env.sim.data.qpos[layout['arm_qpos']].copy())
    original_set_goal = controller.set_goal
    # A zero delta by itself follows the current pose each step. Fix the target.
    def fixed_goal(action, **kwargs):
        return original_set_goal(action, set_pos=position, set_ori=orientation)
    controller.set_goal = fixed_goal
    def advance(observation):
        observation, _, _, _ = env.step(np.zeros(7))
        if frame:
            frame(observation)
        return observation
    try:
        return wait_until_stopped(obs, advance, lambda: stopped(env.sim.data.qvel, layout), predecessor)
    finally:
        controller.set_goal = original_set_goal
        sync_controller(env, reference, layout)
