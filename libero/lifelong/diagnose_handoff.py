"""BC diagnostic evaluation: explicit protocol, per-episode records, boundary states.

Run from repository root with python -m libero.lifelong.diagnose_handoff.
Torch and MuJoCo are deliberately imported only after CLI parsing.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import time

from libero.lifelong.handoff_metrics import model_index, reset_robot_state, select_task_ids, summarize

ROOT = Path(__file__).resolve().parents[2]
SUITES = ["boss_44", "ch1", "ch2_2_modifications", "ch2_3_modifications"] + [f"ch3_{i}" for i in range(1, 11)]


def rollout(env, obs, act, enter_next, max_steps, frame=None):
    stage_steps = [0] * env.n_tasks
    completed = 0
    done = False
    for step in range(1, max_steps + 1):
        stage = env.task_id
        action = act(stage, obs)
        obs, _, done, info = env.step(action)
        stage_steps[stage] += 1
        completed = int(info["complete_id"]) + 1
        if info["is_init"]:
            obs = enter_next(info["task_index"], obs, step)
        if frame:
            frame(obs)
        if done:
            break
    return dict(completed=completed, steps=step, stage_steps=stage_steps,
                termination="success" if done else "budget_exhausted")


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True, help="Must not already exist")
    p.add_argument("--suites", nargs="+", choices=SUITES, default=SUITES)
    p.add_argument("--task-ids", nargs="+", type=int, help="Filter singles by ORIGINAL skill IDs")
    p.add_argument("--seed", type=int, default=10000, help="Evaluation seed; does not change training seed")
    p.add_argument("--episodes", type=int, default=20)
    p.add_argument("--max-steps", type=int, default=400, help="Single-skill limit; chain total is this times chain length")
    p.add_argument("--reset-mode", choices=["original", "none"], default="original")
    p.add_argument("--init-order", choices=["fixed", "shuffle"], default="fixed")
    p.add_argument("--snapshot-episodes", type=int, default=2)
    p.add_argument("--video-episodes", type=int, default=0)
    args = p.parse_args()
    if min(args.episodes, args.max_steps) <= 0 or min(args.snapshot_episodes, args.video_episodes, args.seed) < 0:
        p.error("episodes/max-steps must be positive, seeds and capture counts nonnegative")
    if len(args.suites) != len(set(args.suites)):
        p.error("Duplicate suites would overwrite individual results")
    if args.output.exists():
        p.error(f"Refusing to overwrite results: {args.output}")
    return args


def main():
    args = parse_args()
    os.chdir(ROOT)  # Upstream benchmark mapping paths are relative to repository root.
    os.environ.setdefault("BOSS_CONFIG_PATH", str(ROOT / ".boss/server"))
    os.environ.setdefault("MUJOCO_GL", "egl")
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    config_path = Path(os.environ["BOSS_CONFIG_PATH"]) / "config.yaml"
    if not config_path.is_file():
        raise FileNotFoundError("Run scripts/prepare_handoff.py on this server first")

    import numpy as np
    import torch
    import robomimic.utils.obs_utils as ObsUtils
    from libero.libero import get_libero_path
    from libero.libero.benchmark import get_benchmark
    from libero.libero.envs import SequentialEnv
    from libero.lifelong.policy_starter import PolicyStarter
    from libero.lifelong.metric import raw_obs_to_tensor_obs
    from libero.lifelong.utils import control_seed, get_task_embs
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; refusing silent CPU evaluation")
    control_seed(args.seed)
    original = get_benchmark("boss_44")()
    original_names = original.get_task_names()
    allowed = select_task_ids(original.n_tasks, args.task_ids)
    jobs = []
    for suite in args.suites:
        benchmark = get_benchmark(suite)()
        if suite.startswith("ch3_"):
            jobs.append((suite, list(benchmark.tasks), list(benchmark.task_indexes)))
        else:
            mapping = None if suite == "boss_44" else json.loads((ROOT / "libero/mappings" / f"{suite}.json").read_text())
            for i in range(benchmark.n_tasks):
                task = benchmark.get_task(i)
                index = original_names.index(task.name) if mapping is None else model_index(task.bddl_file, original_names, mapping)
                if index in allowed:
                    jobs.append((f"{suite}/task{i:02d}", [task], [index]))
    required = sorted({i for _, _, ids in jobs for i in ids})
    model_dir = args.model_dir.expanduser().resolve()
    checkpoints = {i: model_dir / f"task{i}_model.pth" for i in required}
    for path in checkpoints.values():
        if not path.is_file():
            raise FileNotFoundError(f"Missing checkpoint {path}; no partial benchmark is scored")
    for _, tasks, _ in jobs:
        for task in tasks:
            for kind, name in [("bddl_files", task.bddl_file), ("init_states", task.init_states_file)]:
                path = Path(get_libero_path(kind)) / task.problem_folder / name
                if not path.is_file():
                    raise FileNotFoundError(path)
    args.output = args.output.expanduser().resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = dict(status="running", protocol="boss_bc_diagnostic_v1", args={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                    python=platform.python_version(), torch=torch.__version__, cuda=torch.version.cuda,
                    gpu=torch.cuda.get_device_name(0), checkpoints={str(i): dict(path=str(p), sha256=file_hash(p)) for i, p in checkpoints.items()},
                    code_sha256={str(p.relative_to(ROOT)): file_hash(p) for p in [Path(__file__), ROOT / "libero/libero/envs/env_wrapper.py", ROOT / "libero/lifelong/handoff_metrics.py"]})
    write_json(args.output / "manifest.json", manifest)
    embedding_cache = {}
    summaries = []
    try:
        for name, tasks, ids in jobs:
            directory = args.output / name
            directory.mkdir(parents=True)
            configs, policies, initial = [], [], []
            for index, task in zip(ids, tasks):
                # BOSS checkpoints contain EasyDict config. Load only trusted own/author files.
                checkpoint = torch.load(checkpoints[index], map_location="cpu", weights_only=False)
                cfg = checkpoint["cfg"]
                if cfg is None:
                    raise ValueError(f"Checkpoint {index} has no training config")
                cfg.device = "cuda:0"
                cfg.experiment_dir = str(directory)
                policy = PolicyStarter(len(ids), cfg).to(cfg.device)
                policy.policy.load_state_dict(checkpoint["state_dict"], strict=True)
                policy.eval()
                configs.append(cfg)
                policies.append(policy)
                path = Path(get_libero_path("init_states")) / task.problem_folder / task.init_states_file
                states = torch.load(path, map_location="cpu", weights_only=False)
                states = np.asarray(states)
                if states.ndim != 2 or not len(states):
                    raise ValueError(f"Invalid initial-state array: {path}")
                initial.append(states)
                del checkpoint
            cfg = configs[0]
            signature = (cfg.task_embedding_format, cfg.task_embedding_one_hot_offset, cfg.data.max_word_len)
            if any((c.task_embedding_format, c.task_embedding_one_hot_offset, c.data.max_word_len) != signature for c in configs):
                raise ValueError("Incompatible language encodings across chain checkpoints")
            if signature not in embedding_cache:
                embedding_cache[signature] = get_task_embs(cfg, [t.language for t in original.tasks])
            embs = embedding_cache[signature]
            ObsUtils.initialize_obs_utils_with_obs_specs({"obs": cfg.data.obs.modality})
            if any(c.data.obs.modality != cfg.data.obs.modality for c in configs):
                raise ValueError("Incompatible observation modalities across chain checkpoints")
            environment = SequentialEnv(len(tasks), initial,
                bddl_file_name=[str(Path(get_libero_path("bddl_files")) / t.problem_folder / t.bddl_file) for t in tasks],
                camera_heights=[c.data.img_h for c in configs], camera_widths=[c.data.img_w for c in configs])
            records = []
            orders = []
            for states in initial:
                indices = np.arange(len(states))
                if args.init_order == "shuffle":
                    indices = np.random.default_rng(args.seed).permutation(indices)
                orders.append(indices)
            try:
                with (directory / "episodes.jsonl").open("w", encoding="utf-8") as log:
                    for episode in range(args.episodes):
                        seed = int(np.random.SeedSequence([args.seed, episode]).generate_state(1)[0])
                        control_seed(seed)
                        environment.seed(seed)
                        environment.reset()
                        # Detect state-layout incompatibility before flat transfer.
                        signatures = [(e.sim.model.nq, e.sim.model.nv, tuple(e.sim.model.joint_names)) for e in environment.env_ls]
                        if len(set(signatures)) != 1:
                            raise ValueError("Chain MuJoCo state layouts differ; cannot transfer flattened state")
                        for policy in policies:
                            policy.reset()
                        init_indices = [int(order[episode % len(order)]) for order in orders]
                        obs = environment.set_init_state(initial[0][init_indices[0]])
                        # Warm up the first environment only; never auto-switch during settling.
                        for _ in range(5):
                            obs, _, _, _ = environment.env_ls[0].step(np.zeros(7))
                        boundaries = []
                        capture = episode < args.snapshot_episodes
                        video = None
                        if episode < args.video_episodes:
                            import imageio.v2 as imageio
                            video = imageio.get_writer(str(directory / f"episode{episode:03d}.mp4"), fps=20)
                        def act(stage, observation):
                            data = raw_obs_to_tensor_obs([observation], embs[ids[stage]], configs[stage])
                            action = np.asarray(policies[stage].policy.get_action(data))[0]
                            if action.shape != (7,) or not np.isfinite(action).all():
                                raise ValueError("Policy produced invalid action")
                            return action
                        def enter_next(stage, observation, step):
                            before = environment.get_sim_state().copy()
                            entry = reset_robot_state(before, initial[stage][init_indices[stage]], args.reset_mode)
                            updated = environment.set_init_state(entry)
                            event = dict(step=step, from_stage=stage-1, to_stage=stage,
                                         before_after_l2=float(np.linalg.norm(entry-before)))
                            if capture:
                                filename = f"episode{episode:03d}_boundary{stage}.npz"
                                np.savez_compressed(directory / filename,
                                    predecessor_terminal=environment.env_ls[stage-1].get_sim_state(),
                                    transferred_state=before, policy_entry_state=entry,
                                    before_rgb=observation["agentview_image"], after_rgb=updated["agentview_image"])
                                event["snapshot"] = filename
                            boundaries.append(event)
                            return updated
                        start = time.perf_counter()
                        try:
                            with torch.no_grad():
                                record = rollout(environment, obs, act, enter_next, args.max_steps * len(tasks),
                                    frame=(lambda observation: video.append_data(observation["agentview_image"][::-1])) if video else None)
                        finally:
                            if video:
                                video.close()
                        record.update(episode=episode, evaluation_seed=seed, init_indices=init_indices,
                                      wall_seconds=time.perf_counter()-start, boundaries=boundaries)
                        if capture:
                            np.savez_compressed(directory / f"episode{episode:03d}_final.npz", state=environment.get_sim_state())
                        log.write(json.dumps(record, allow_nan=False) + "\n")
                        log.flush()
                        records.append(record)
                        print(f"{name} {episode+1}/{args.episodes}: {record['completed']}/{len(tasks)} stages", flush=True)
            finally:
                environment.close()
            result = summarize(records, len(tasks))
            result.update(name=name, model_ids=ids, tasks=[t.name for t in tasks], reset_mode=args.reset_mode,
                          training_seeds=[int(c.seed) for c in configs], evaluation_seed=args.seed,
                          max_steps=args.max_steps, init_order=args.init_order,
                          wall_seconds=sum(r["wall_seconds"] for r in records))
            write_json(directory / "summary.json", result)
            summaries.append(result)
            del policies, environment, policy
            torch.cuda.empty_cache()
        write_json(args.output / "summary.json", summaries)
        manifest["status"] = "complete"
    except Exception:
        manifest["status"] = "failed"
        raise
    finally:
        write_json(args.output / "manifest.json", manifest)


if __name__ == "__main__":
    main()
