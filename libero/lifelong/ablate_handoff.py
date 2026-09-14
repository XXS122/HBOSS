"""Paired, frozen-policy task-2 to task-3 ablation; no training."""
import argparse
import csv
from collections import Counter
import json
import os
from pathlib import Path
import time

from libero.lifelong.diagnose_handoff import file_hash, write_json

ROOT = Path(__file__).resolve().parents[2]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--states', type=int, default=20)
    parser.add_argument('--eval-seeds', type=int, nargs='+', default=[10000, 20000, 30000])
    args = parser.parse_args(argv)
    if args.states < 1 or min(args.eval_seeds) < 0 or max(args.eval_seeds) >= 2**32:
        parser.error('states must be positive; seeds must be in [0, 2**32)')
    if len(set(args.eval_seeds)) != len(args.eval_seeds):
        parser.error('Evaluation seeds must be distinct')
    if args.output.exists():
        parser.error('Output must not already exist')
    return args


def main():
    args = parse_args()
    os.chdir(ROOT)
    os.environ.setdefault('BOSS_CONFIG_PATH', str(ROOT / '.boss/server'))
    os.environ.setdefault('MUJOCO_GL', 'egl')
    os.environ.setdefault('PYOPENGL_PLATFORM', 'egl')
    import numpy as np
    import torch
    import robosuite
    import mujoco
    import imageio.v2 as imageio
    import robomimic.utils.obs_utils as ObsUtils
    from libero.libero import get_libero_path
    from libero.libero.benchmark import get_benchmark
    from libero.libero.envs import OffScreenRenderEnv
    from libero.lifelong.policy_starter import PolicyStarter
    from libero.lifelong.metric import raw_obs_to_tensor_obs
    from libero.lifelong.utils import control_seed, get_task_embs
    from libero.lifelong.handoff_ablation import MODES, joint_layout, intervene, restore, settle, evaluate_stage, collection_attempts

    if not torch.cuda.is_available():
        raise RuntimeError('CUDA is required')
    if robosuite.__version__ != '1.4.1':
        raise RuntimeError('Controller restoration is implemented for robosuite 1.4.1')
    control_seed(10000)
    original = get_benchmark('boss_44')()
    chain = get_benchmark('ch3_1')()
    if list(chain.task_indexes[:2]) != [2, 3]:
        raise ValueError('Expected CH3_1 to start with skills 2 and 3')
    args.output = args.output.resolve()
    checkpoints = {i: args.model_dir.resolve() / f'task{i}_model.pth' for i in [2, 3]}
    for path in checkpoints.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    args.output.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__), ROOT / 'libero/lifelong/handoff_ablation.py',
               ROOT / 'libero/libero/envs/env_wrapper.py', ROOT / 'scripts/run_handoff_ablation.py']
    manifest = dict(status='running', protocol='paired_handoff_ablation_v2',
        states_requested=args.states, eval_seeds=args.eval_seeds, collection_seed=10000,
        policy_budget=400, settle_budget=40, settle_consecutive_steps=5,
        arm_velocity_threshold_rad_s=.02, gripper_velocity_threshold_m_s=.002,
        control_hz=20, modes=list(MODES), tasks=[t.name for t in chain.tasks[:2]],
        torch=torch.__version__, robosuite=robosuite.__version__, mujoco=mujoco.__version__,
        gpu=torch.cuda.get_device_name(0),
        checkpoints={str(i): dict(path=str(p), sha256=file_hash(p)) for i, p in checkpoints.items()},
        code_sha256={str(p.relative_to(ROOT)): file_hash(p) for p in sources})
    write_json(args.output / 'manifest.json', manifest)
    environments = []
    try:
        policies, configs, initial = [], [], []
        for index, task in zip([2, 3], chain.tasks[:2]):
            checkpoint = torch.load(checkpoints[index], map_location='cpu', weights_only=False)
            cfg = checkpoint['cfg']
            cfg.device = 'cuda:0'
            cfg.experiment_dir = str(args.output)
            policy = PolicyStarter(2, cfg).to(cfg.device)
            policy.policy.load_state_dict(checkpoint['state_dict'], strict=True)
            policy.eval()
            policies.append(policy)
            configs.append(cfg)
            path = Path(get_libero_path('init_states')) / task.problem_folder / task.init_states_file
            states = np.asarray(torch.load(path, map_location='cpu', weights_only=False))
            if states.ndim != 2 or not len(states):
                raise ValueError(f'Invalid initial states: {path}')
            initial.append(states)
            manifest.setdefault('init_states_sha256', {})[str(index)] = file_hash(path)
            bddl = Path(get_libero_path('bddl_files')) / task.problem_folder / task.bddl_file
            manifest.setdefault('bddl_sha256', {})[str(index)] = file_hash(bddl)
            environments.append(OffScreenRenderEnv(bddl_file_name=str(bddl),
                camera_heights=cfg.data.img_h, camera_widths=cfg.data.img_w,
                control_freq=20, ignore_done=True))
            del checkpoint
        signature = lambda c: (c.task_embedding_format, c.task_embedding_one_hot_offset,
                               c.data.max_word_len, c.data.obs.modality)
        if signature(configs[0]) != signature(configs[1]):
            raise ValueError('Checkpoint language encodings / observation modalities differ')
        embs = get_task_embs(configs[0], [t.language for t in original.tasks])
        ObsUtils.initialize_obs_utils_with_obs_specs({'obs': configs[0].data.obs.modality})
        manifest['training_seeds'] = [int(c.seed) for c in configs]
        manifest['attempt_limit'] = args.states * 10
        manifest['initial_state_counts'] = [len(states) for states in initial]
        manifest['collection_sampling'] = 'cycle_initial_states_with_new_rollout_seeds'
        source, target = environments
        for env in environments:
            env.reset()
        layout = joint_layout(source)
        if joint_layout(target) != layout:
            raise ValueError('Source and successor state layouts differ')
        write_json(args.output / 'joint_layout.json', layout)
        def check_layout(env):
            if joint_layout(env) != layout:
                raise ValueError('State layout changed after reset')
        def bottom(env):
            return bool(env.env.object_states_dict['wooden_cabinet_1_bottom_region'].is_open())
        def top(env):
            return bool(env.env.object_states_dict['wooden_cabinet_1_top_region'].is_open())
        def action(stage, observation):
            data = raw_obs_to_tensor_obs([observation], embs[[2, 3][stage]], configs[stage])
            with torch.no_grad():
                value = np.asarray(policies[stage].policy.get_action(data))[0]
            if value.shape != (7,) or not np.isfinite(value).all():
                raise ValueError('Invalid policy action')
            return value
        def seed_for(root_seed, index):
            return int(np.random.SeedSequence([root_seed, index]).generate_state(1)[0])
        def append(log, record):
            log.write(json.dumps(record, allow_nan=False) + '\n')
            log.flush()

        pool = []
        snapshots = args.output / 'snapshots'
        snapshots.mkdir()
        with (args.output / 'collection.jsonl').open('w', encoding='utf-8') as log:
            for sample in collection_attempts(len(initial[0]), args.states):
                attempt, initial_index, seed = sample['attempt'], sample['initial_index'], sample['seed']
                control_seed(seed)
                source.seed(seed)
                source.reset()
                check_layout(source)
                obs = source.set_init_state(initial[0][initial_index])
                for _ in range(5):
                    obs, _, _, _ = source.step(np.zeros(7))
                policies[0].reset()
                steps = 0
                initial_valid = not bottom(source) and not top(source)
                if initial_valid:
                    while steps < 400 and not source.check_success():
                        obs, _, _, _ = source.step(action(0, obs))
                        steps += 1
                accepted = initial_valid and bool(source.check_success()) and bottom(source) and not top(source)
                row = dict(**sample, initial_valid=initial_valid, steps=steps, accepted=accepted)
                if accepted:
                    state = source.get_sim_state().copy()
                    reference_index = initial_index % len(initial[1])
                    reference = initial[1][reference_index].copy()
                    state_id = len(pool)
                    filename = f'state{state_id:03d}.npz'
                    np.savez_compressed(snapshots / filename, terminal=state, reference=reference,
                        source_rgb=obs['agentview_image'],
                        source_ctrl=source.sim.data.ctrl.copy(),
                        source_gripper_command=source.robots[0].gripper.current_action.copy())
                    row.update(state_id=state_id, snapshot=filename, sha256=file_hash(snapshots / filename),
                               reference_index=reference_index)
                    pool.append((state, reference, sample))
                append(log, row)
                print(f'[collect] attempt {attempt + 1}/{manifest["attempt_limit"]} initial={initial_index}: {len(pool)}/{args.states} states', flush=True)
                if len(pool) == args.states:
                    break
        manifest['states_collected'] = len(pool)
        manifest['collection_attempts'] = attempt + 1
        counts = Counter(sample['initial_index'] for _, _, sample in pool)
        manifest['accepted_by_initial_index'] = {str(i): counts[i] for i in range(len(initial[0]))}
        if len(pool) != args.states:
            raise RuntimeError(f'Only collected {len(pool)}/{args.states}; collection.jsonl records failures. No partial comparison scored.')
        records = []
        with (args.output / 'episodes.jsonl').open('w', encoding='utf-8') as log:
            for state_id, (state, reference, sample) in enumerate(pool):
                for root_seed in args.eval_seeds:
                    seed = seed_for(root_seed, state_id)
                    for mode in MODES:
                        start = time.perf_counter()
                        control_seed(seed)
                        target.seed(seed)
                        target.reset()
                        check_layout(target)
                        entry = intervene(state, reference, layout, mode)
                        obs, controller = restore(target, entry, reference, layout)
                        capture = state_id == 0 and root_seed == args.eval_seeds[0]
                        video = imageio.get_writer(str(args.output / f'{mode}.mp4'), fps=20) if capture else None
                        def frame(observation):
                            if video:
                                video.append_data(observation['agentview_image'][::-1])
                        frame(obs)
                        settled, wait_steps, preserved = True, 0, bottom(target)
                        try:
                            if mode == 'settle':
                                obs, wait_steps, settled, hold_preserved = settle(target, obs, reference, layout,
                                    lambda: bottom(target), frame)
                                preserved = preserved and hold_preserved
                            policy_entry = target.get_sim_state().copy()
                            successor_at_entry = bool(target.check_success())
                            # Same RNG start and empty policy history for every condition.
                            control_seed(seed)
                            policies[1].reset()
                            def advance(observation):
                                observation, _, _, _ = target.step(action(1, observation))
                                frame(observation)
                                return observation
                            if settled:
                                result, obs = evaluate_stage(obs, advance, target.check_success,
                                    lambda: bottom(target), 400, preserved=preserved)
                            else:
                                result = dict(success=False, policy_steps=0, predecessor_always=preserved,
                                              predecessor_final=bottom(target))
                        finally:
                            if video:
                                video.close()
                        result.update(state_id=state_id, initial_index=sample['initial_index'],
                            collection_seed=sample['seed'], evaluation_seed=root_seed, policy_seed=seed, mode=mode,
                            settle_success=settled, settle_steps=wait_steps, settle_seconds=wait_steps / 20,
                            policy_seconds=result['policy_steps'] / 20,
                            total_seconds=(wait_steps + result['policy_steps']) / 20,
                            wall_seconds=time.perf_counter() - start, successor_at_policy_entry=successor_at_entry,
                            controller_after_restore=controller,
                            termination='settle_timeout' if not settled else ('success' if result['success'] else 'budget_exhausted'),
                            success_with_preservation=result['success'] and result['predecessor_always'])
                        np.savez_compressed(snapshots / f'state{state_id:03d}_seed{root_seed}_{mode}.npz',
                                            after_intervention=entry, policy_entry=policy_entry,
                                            final=target.get_sim_state())
                        append(log, result)
                        records.append(result)
                        print(f'[eval] state {state_id + 1}/{len(pool)} seed {root_seed} {mode}: '
                              f'success={result["success"]} preserved={result["predecessor_always"]} '
                              f'wait={wait_steps} steps={result["policy_steps"]}', flush=True)
        summary = []
        for mode in MODES:
            for seed in [None] + args.eval_seeds:
                rows = [r for r in records if r['mode'] == mode and (seed is None or r['evaluation_seed'] == seed)]
                summary.append(dict(mode=mode, evaluation_seed='all' if seed is None else seed, episodes=len(rows),
                    successes=sum(r['success'] for r in rows),
                    success_rate=sum(r['success'] for r in rows) / len(rows),
                    preserved_successes=sum(r['success_with_preservation'] for r in rows),
                    predecessor_always_count=sum(r['predecessor_always'] for r in rows),
                    predecessor_final_count=sum(r['predecessor_final'] for r in rows),
                    settle_timeouts=sum(not r['settle_success'] for r in rows),
                    mean_total_seconds=sum(r['total_seconds'] for r in rows) / len(rows)))
        with (args.output / 'summary.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(summary[0]))
            writer.writeheader()
            writer.writerows(summary)
        write_json(args.output / 'summary.json', summary)
        manifest['status'] = 'complete'
    except BaseException:
        manifest['status'] = 'failed'
        raise
    finally:
        write_json(args.output / 'manifest.json', manifest)
        for env in environments:
            env.close()
    print(f'Results: {args.output}', flush=True)


if __name__ == '__main__':
    main()
