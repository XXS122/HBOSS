"""Server-only CUDA/EGL/asset/import smoke test before expensive training."""
import json
import os
from pathlib import Path
import platform

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    os.environ.setdefault("BOSS_CONFIG_PATH", str(ROOT / ".boss/server"))
    os.environ.setdefault("MUJOCO_GL", "egl")
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    import numpy as np
    import torch
    import robosuite
    import mujoco
    from libero.libero.benchmark import get_benchmark
    from libero.libero.envs import OffScreenRenderEnv
    from libero.lifelong.policy_starter import PolicyStarter
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; check NVIDIA driver and cu121 PyTorch")
    # Exercise the GPU, not just the discovery API.
    value = (torch.ones((32, 32), device="cuda:0") @ torch.ones((32, 32), device="cuda:0")).mean().item()
    benchmark = get_benchmark("boss_44")()
    env = OffScreenRenderEnv(bddl_file_name=benchmark.get_task_bddl_file_path(2),
                             camera_heights=128, camera_widths=128)
    try:
        env.seed(10000)
        env.reset()
        obs = env.set_init_state(np.asarray(benchmark.get_task_init_states(2)[0]))
        for _ in range(5):
            obs, _, _, _ = env.step(np.zeros(7))
        assert obs["agentview_image"].shape == (128, 128, 3)
        report = dict(python=platform.python_version(), torch=torch.__version__, cuda=torch.version.cuda,
                      gpu=torch.cuda.get_device_name(0), gpu_gib=torch.cuda.get_device_properties(0).total_memory / 2**30,
                      robosuite=robosuite.__version__, mujoco=mujoco.__version__, gpu_matmul=value,
                      rendered_rgb_shape=list(obs["agentview_image"].shape), status="passed")
        directory = ROOT / ".boss/server"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "runtime.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        env.close()


if __name__ == "__main__":
    # Script execution adds scripts/, but upstream imports need repository root.
    import sys
    sys.path.insert(0, str(ROOT))
    main()
