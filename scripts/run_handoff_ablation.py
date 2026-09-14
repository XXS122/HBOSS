"""Run paired handoff tests with existing pilot weights."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import shlex
import sys
import uuid
from run_handoff_experiment import ROOT, run_logged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--states', type=int, default=20)
    parser.add_argument('--position-source', type=Path, help='Reuse a completed v2 evaluation for four position groups')
    parser.add_argument('--eval-seeds', type=int, nargs='+', default=[10000, 20000, 30000])
    parser.add_argument('--gpu', type=int, default=0)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.states < 1 or args.gpu < 0 or min(args.eval_seeds) < 0 or max(args.eval_seeds) >= 2**32:
        parser.error('Invalid state count, GPU index or evaluation seed')
    if len(set(args.eval_seeds)) != len(args.eval_seeds):
        parser.error('Evaluation seeds must be distinct')
    name = datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8]
    directory = ROOT / 'results/handoff_ablation' / name
    command = [sys.executable, '-m', 'libero.lifelong.ablate_handoff',
        '--model-dir', str(args.model_dir.resolve()), '--output', str(directory / 'evaluation'),
        '--states', str(args.states), '--eval-seeds', *map(str, args.eval_seeds)]
    if args.position_source:
        command += ['--position-source', str(args.position_source.resolve())]
    print(shlex.join(command), flush=True)
    if args.dry_run:
        return
    if sys.platform != 'linux' or sys.version_info[:2] != (3, 10):
        raise RuntimeError('Run in the Ubuntu Python 3.10 boss-bc environment')
    directory.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES=str(args.gpu), MUJOCO_EGL_DEVICE_ID=str(args.gpu),
        MUJOCO_GL='egl', PYOPENGL_PLATFORM='egl', BOSS_CONFIG_PATH=str(ROOT / '.boss/server'),
        TOKENIZERS_PARALLELISM='false', WANDB_MODE='disabled', PYTHONUNBUFFERED='1',
        OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONPATH=str(ROOT))
    code = run_logged(command, directory / 'ablation.log', env)
    if code:
        raise RuntimeError(f'Evaluation failed (exit {code}). See {directory / "ablation.log"}')
    print(f'Upload this result directory: {directory}', flush=True)


if __name__ == '__main__':
    main()
