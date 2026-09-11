"""Prepare, smoke-test, train and evaluate BC with one explicit server command."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
POLICIES = {"transformer": ("bc_transformer_policy", "BCTransformerPolicy"),
            "rnn": ("bc_rnn_policy", "BCRNNPolicy"), "vilt": ("bc_vilt_policy", "BCViLTPolicy")}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=["smoke", "pilot", "full"], default="smoke")
    p.add_argument("--policy", choices=POLICIES, default="transformer")
    p.add_argument("--gpu", type=int, default=0, help="Physical NVIDIA GPU index; single GPU only")
    p.add_argument("--train-seed", type=int, default=10000)
    p.add_argument("--eval-seeds", nargs="+", type=int, default=[10000, 20000, 30000])
    p.add_argument("--epochs", type=int, help="Default: smoke=1, other stages=50")
    p.add_argument("--episodes", type=int, help="Default: smoke=2, other stages=20 per task per eval seed")
    p.add_argument("--model-dir", type=Path, help="Use existing compatible BC weights; skip training")
    p.add_argument("--data-root", type=Path, default=ROOT / "datasets")
    p.add_argument("--assets", type=Path, default=ROOT / "assets")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--dry-run", action="store_true", help="Print commands; no paths/data/GPU required, writes nothing")
    args = p.parse_args(argv)
    if min(args.gpu, args.train_seed, args.workers, *args.eval_seeds) < 0:
        p.error("GPU, workers and seeds must be nonnegative")
    if len(set(args.eval_seeds)) != len(args.eval_seeds):
        p.error("Evaluation seeds must be distinct")
    if (args.epochs is not None and args.epochs < 1) or (args.episodes is not None and args.episodes < 1):
        p.error("epochs and episodes must be positive")
    return args


def build_commands(args, run_id):
    run_dir = ROOT / "results/handoff" / run_id
    version = "handoff_" + run_id
    policy, policy_class = POLICIES[args.policy]
    models = args.model_dir.expanduser().resolve() if args.model_dir else ROOT / "experiments/boss_44" / version / f"{policy_class}_seed{args.train_seed}" / "run_001"
    commands = [
        ("prepare", [sys.executable, "scripts/prepare_handoff.py", "--data-root", str(args.data_root.resolve()), "--assets", str(args.assets.resolve()), "--inspect-data"]),
        ("runtime", [sys.executable, "scripts/check_handoff_runtime.py"]),
    ]
    if args.model_dir is None:
        commands.append(("train", [sys.executable, "-m", "libero.lifelong.train_skills",
            f"policy={policy}", "benchmark_name=boss_44", f"seed={args.train_seed}", "device=cuda:0",
            "folder=null", "bddl_folder=null", "init_states_folder=null", f"version={version}",
            "train_task_ids=null" if args.stage == "full" else "train_task_ids=[2,3,5]",
            f"train.n_epochs={args.epochs or (1 if args.stage == 'smoke' else 50)}",
            "train.batch_size=32", f"train.num_workers={args.workers}", f"eval.num_workers={args.workers}",
            "eval.eval=false", "use_wandb=false", "hydra.run.dir=.", "hydra.output_subdir=null"] ))
    seeds = args.eval_seeds[:1] if args.stage == "smoke" else args.eval_seeds
    singles = ["boss_44", "ch1", "ch2_2_modifications", "ch2_3_modifications"]
    chains = [f"ch3_{i}" for i in range(1, 11)] if args.stage == "full" else ["ch3_1"]
    for seed in seeds:
        for mode in ["original", "none"]:
            name = f"eval_{mode}_seed{seed}"
            command = [sys.executable, "-m", "libero.lifelong.diagnose_handoff", "--model-dir", str(models),
                       "--output", str(run_dir / name), "--seed", str(seed), "--reset-mode", mode,
                       "--episodes", str(args.episodes or (2 if args.stage == "smoke" else 20)),
                       "--max-steps", "20" if args.stage == "smoke" else "400",
                       "--snapshot-episodes", "2", "--video-episodes", "1",
                       "--suites", *(singles + chains if mode == "original" else chains)]
            if args.stage != "full":
                command += ["--task-ids", "2", "3", "5"]
            commands.append((name, command))
    commands.append(("aggregate", [sys.executable, "scripts/summarize_handoff.py", str(run_dir)]))
    return commands


def main():
    args = parse_args()
    run_id = args.stage + "_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    commands = build_commands(args, run_id)
    if args.dry_run:
        for name, cmd in commands:
            print(f"[{name}] {shlex.join(cmd)}")
        return
    if sys.version_info[:2] != (3, 10) or sys.platform != "linux":
        raise RuntimeError("Execute on Ubuntu in the Python 3.10 BC environment; use --dry-run elsewhere")
    run_dir = ROOT / "results/handoff" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES=str(args.gpu), MUJOCO_EGL_DEVICE_ID=str(args.gpu),
               MUJOCO_GL="egl", PYOPENGL_PLATFORM="egl", BOSS_CONFIG_PATH=str(ROOT / ".boss/server"),
               TOKENIZERS_PARALLELISM="false", WANDB_MODE="disabled", PYTHONUNBUFFERED="1",
               OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONPATH=str(ROOT))
    record = dict(status="running", stage=args.stage,
                  args={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                  commands=[dict(name=name, argv=cmd) for name, cmd in commands])
    manifest = run_dir / "pipeline.json"
    manifest.write_text(json.dumps(record, indent=2), encoding="utf-8")
    try:
        for name, cmd in commands:
            print(f"[{name}] {shlex.join(cmd)}", flush=True)
            with (run_dir / f"{name}.log").open("w", encoding="utf-8") as log:
                result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                raise RuntimeError(f"{name} failed (exit {result.returncode}). See {run_dir / (name + '.log')}")
            if name == "prepare":
                for filename in ("config.yaml", "data_inventory.json"):
                    shutil.copy2(ROOT / ".boss/server" / filename, run_dir / filename)
            if name == "runtime":
                shutil.copy2(ROOT / ".boss/server/runtime.json", run_dir / "runtime.json")
                with (run_dir / "installed-packages.txt").open("w", encoding="utf-8") as packages:
                    subprocess.run([sys.executable, "-m", "pip", "freeze"], env=env, stdout=packages, check=True)
            print(f"[{name}] complete", flush=True)
        record["status"] = "complete"
    except Exception:
        record["status"] = "failed"
        raise
    finally:
        manifest.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Results: {run_dir}\nUpload report.md, *.csv, pipeline.json and eval directories for analysis.")


if __name__ == "__main__":
    main()
