"""Aggregate complete diagnostic runs; never silently score missing checkpoints/runs."""
import argparse
import csv
import json
from pathlib import Path


def compatible(left, right):
    return all(left.get(k) == right.get(k) for k in
               ("checkpoint_hashes", "evaluation_seed", "max_steps", "init_order", "episodes"))


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def aggregate(root):
    all_rows, excluded, oss = [], [], []
    for path in sorted(root.rglob("manifest.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("protocol") != "boss_bc_diagnostic_v1":
            continue
        if manifest["status"] != "complete":
            excluded.append(str(path.parent.relative_to(root)))
            continue
        rows = json.loads((path.parent / "summary.json").read_text(encoding="utf-8"))
        for row in rows:
            row["run"] = str(path.parent.relative_to(root))
            row["checkpoint_hashes"] = {str(i): manifest["checkpoints"][str(i)]["sha256"] for i in row["model_ids"]}
        originals = {r["model_ids"][0]: r for r in rows if r["name"].startswith("boss_44/")}
        for row in rows:
            if row["name"].startswith(("ch1/", "ch2_")):
                original = originals.get(row["model_ids"][0])
                if original is None or not compatible(original, row):
                    raise ValueError(f"No compatible original baseline for {row['run']}:{row['name']}")
                p0, pm = original["success_rate"], row["success_rate"]
                oss.append(dict(run=row["run"], name=row["name"], model_id=row["model_ids"][0],
                                evaluation_seed=row["evaluation_seed"], original=p0, modified=pm,
                                drop_pp=100*(p0-pm), rpd=(p0-pm)/p0 if p0 else None,
                                original_n=original["episodes"], modified_n=row["episodes"]))
        all_rows.extend(rows)
    if not all_rows:
        raise ValueError("No complete diagnostic runs found")
    comparison = []
    for row in all_rows:
        if not row["name"].startswith("ch3_") or row["reset_mode"] != "none":
            continue
        matches = [r for r in all_rows if r["name"] == row["name"] and r["reset_mode"] == "original" and compatible(r, row)]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one matched reset baseline for {row['name']}; found {len(matches)}")
        reference = matches[0]
        comparison.append(dict(chain=row["name"], evaluation_seed=row["evaluation_seed"],
            original_run=reference["run"], none_run=row["run"],
            original_success=reference["success_rate"], none_success=row["success_rate"],
            original_conditional=json.dumps(reference["conditional_success_rates"]),
            none_conditional=json.dumps(row["conditional_success_rates"]),
            delta_pp=100*(row["success_rate"]-reference["success_rate"])))
    flat = [dict(run=r["run"], task=r["name"], model_ids=json.dumps(r["model_ids"]),
                 training_seeds=json.dumps(r["training_seeds"]), evaluation_seed=r["evaluation_seed"],
                 reset_mode=r["reset_mode"], episodes=r["episodes"], success_rate=r["success_rate"],
                 prefix_rates=json.dumps(r["prefix_success_rates"]), conditional_rates=json.dumps(r["conditional_success_rates"]),
                 reached=json.dumps(r["stage_reached_counts"]), successful=json.dumps(r["stage_success_counts"]),
                 mean_steps=r["mean_steps"], wall_seconds=r["wall_seconds"]) for r in all_rows]
    write_csv(root / "runs.csv", flat)
    write_csv(root / "oss.csv", oss)
    write_csv(root / "chain_reset_comparison.csv", comparison)
    text = ["# BOSS 第一轮诊断结果", "", "以下来自实际完成的运行；smoke仅测管线，不能作为性能结果。", "",
            "| Run | Task | n | Success | Conditional stage success |", "|---|---|---:|---:|---|"]
    for r in all_rows:
        text.append(f"| {r['run']} | {r['name']} | {r['episodes']} | {r['success_rate']:.3f} | {r['conditional_success_rates']} |")
    text += ["", "- 原始、CH1及CH2是不同初始化场景的匹配比较，不是相同物理快照上的纯视觉因果干预。",
             "- 条件后继成功率的分母是到达该阶段的回合数；未到达为null，不填0。不同reset模式可能产生不同幸存样本。",
             "- reset=none取消传统切片覆盖，但仍跨环境转移MuJoCo state；不是已验证的无缝物理执行。",
             "- RPD在原始成功率为0时留空；未把原始成功率乘积称为理论上界。",
             "- 多个评估seed不等于多个训练seed；原子技能的训练seed在runs.csv单列。",
             f"- 未纳入失败/未完成运行：{excluded or '无'}。", "",
             "下一步先检查原始技能是否学会，再看CH1/CH2下降、链各位置失败和归位敏感性；不能只凭这些相关性判定失败原因。"]
    (root / "report.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    return dict(complete_task_runs=len(all_rows), excluded=excluded, oss_pairs=len(oss), chain_pairs=len(comparison))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    print(json.dumps(aggregate(parser.parse_args().results.resolve()), indent=2))
