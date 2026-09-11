"""Non-destructive BOSS paths/data preparation, runnable before ML installation."""
import argparse
import ast
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def boss_names(root):
    tree = ast.parse((root / "libero/libero/benchmark/boss_task_map.py").read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "boss_task_map" for t in n.targets))
    return ast.literal_eval(node.value)["boss_44"]


def prepare_dataset(source, destination, names, mode):
    files = [source / f"{name}_demo.hdf5" for name in names]
    missing = [str(p) for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing demonstrations:\n" + "\n".join(missing))
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Will not overwrite {destination}")
    destination.mkdir(parents=True)
    for src in files:
        dst = destination / src.name
        if mode == "copy":
            shutil.copy2(src, dst)
        elif mode == "symlink":
            dst.symlink_to(src.resolve())
        else:
            raise ValueError(mode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=ROOT / "datasets", help="Parent directory of boss_44")
    parser.add_argument("--dataset-source", type=Path, help="Existing libero_90 directory, not ZIP")
    parser.add_argument("--assets", type=Path, default=ROOT / "assets", help="Unpacked asset root")
    parser.add_argument("--mode", choices=["symlink", "copy"], default="symlink")
    parser.add_argument("--inspect-data", action="store_true", help="Validate HDF5 observations; needs h5py")
    args = parser.parse_args()
    names = boss_names(ROOT)
    assets = args.assets.expanduser().resolve()
    for subdir in ("articulated_objects", "stable_hope_objects", "stable_scanned_objects"):
        if not (assets / subdir).is_dir():
            parser.error(f"Asset directory missing: {assets / subdir}")
    data_root = args.data_root.expanduser().resolve()
    destination = data_root / "boss_44"
    if not destination.exists() and args.dataset_source is None:
        candidates = [p for p in (data_root / "libero_90", data_root / "LIBERO-90") if p.is_dir()]
        if len(candidates) == 1:
            args.dataset_source = candidates[0]
    if args.dataset_source:
        prepare_dataset(args.dataset_source.expanduser().resolve(), destination, names, args.mode)
    missing = [str(destination / f"{name}_demo.hdf5") for name in names
               if not (destination / f"{name}_demo.hdf5").is_file()]
    if missing:
        parser.error("Missing data (no training started):\n" + "\n".join(missing))
    # Several upstream object classes hard-code this asset path, ignoring config.yaml.
    local_assets = ROOT / "libero/libero/assets"
    if local_assets.exists() or local_assets.is_symlink():
        if local_assets.resolve() != assets:
            parser.error(f"{local_assets} already exists and differs from --assets; will not replace it")
    else:
        local_assets.symlink_to(assets, target_is_directory=True)
    config = dict(benchmark_root=str(ROOT / "libero/libero"),
                  bddl_files=str(ROOT / "libero/libero/bddl_files"),
                  init_states=str(ROOT / "libero/libero/init_files"),
                  datasets=str(data_root), assets=str(assets))
    config_dir = ROOT / ".boss/server"
    config_dir.mkdir(parents=True, exist_ok=True)
    # JSON is valid YAML and avoids requiring PyYAML for preparation.
    (config_dir / "config.yaml").write_text(json.dumps(config, indent=2), encoding="utf-8")
    records = []
    if args.inspect_data:
        import h5py
        for name in names:
            path = destination / f"{name}_demo.hdf5"
            with h5py.File(path, "r") as f:
                demos = list(f["data"].keys())
                if not demos:
                    raise ValueError(f"Empty dataset: {path}")
                for demo in demos:
                    group = f["data"][demo]
                    if group["actions"].shape[-1] != 7:
                        raise ValueError(f"Expected 7D actions: {path}:{demo}")
                    for key in ("agentview_rgb", "joint_states", "gripper_states"):
                        if len(group["obs"][key]) != len(group["actions"]):
                            raise ValueError(f"Observation/action length mismatch: {path}:{demo}:{key}")
                records.append(dict(task=name, demonstrations=len(demos), bytes=path.stat().st_size))
        (config_dir / "data_inventory.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Ready: {len(names)} dataset files; BOSS_CONFIG_PATH={config_dir}")
    print("Paths are machine-specific: rerun this command after transferring to Ubuntu.")


if __name__ == "__main__":
    main()
