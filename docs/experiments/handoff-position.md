# 机械臂与夹爪位置对照

**目标：判断位置复位带来的改善，主要来自机械臂姿态还是夹爪开合。**

| 组名 | 机械臂位置 | 夹爪位置 | 机械臂及夹爪速度 |
|---|---|---|---|
| keep_position | 保留 | 保留 | 清零 |
| reset_arm | 复位 | 保留 | 清零 |
| reset_gripper | 保留 | 复位 | 清零 |
| reset_both | 复位 | 复位 | 清零 |

所有组保留物体位置和速度，使用相同模型、终止状态、参考状态和评估 seed，Task 2 最多 400 步。控制器恢复规则沿用上一轮，机械臂参考姿态相同；末端目标与夹爪命令对应各组的入口位置。

实现检查：按关节地址修改指定位置；核对源实验的完成状态、模型与状态文件哈希、仿真版本和关节布局；比较新旧两个对照组的入口状态是否相同。

## 在服务器运行

复用上一轮 `20260914_084357_06db03c5/evaluation` 中的状态，不训练模型、不重新采集 Task 1。

先检查 2 个状态、1 个 seed，共 8 次评估：

```bash
python scripts/run_handoff_ablation.py \
  --model-dir experiments/boss_44/handoff_pilot_20260911_045322_1fa6d774/BCTransformerPolicy_seed10000/run_001 \
  --position-source results/handoff_ablation/20260914_084357_06db03c5/evaluation \
  --states 2 --eval-seeds 10000
```

正常后，运行 20 个状态 × 3 个 seed × 4 组，共 240 次评估：

```bash
python scripts/run_handoff_ablation.py \
  --model-dir experiments/boss_44/handoff_pilot_20260911_045322_1fa6d774/BCTransformerPolicy_seed10000/run_001 \
  --position-source results/handoff_ablation/20260914_084357_06db03c5/evaluation
```

开始时应出现 `[replay] loaded ... verified terminal states`；每次评估实时输出并保存日志。新结果仍写到独立的 `results/handoff_ablation/<运行编号>/`，不会覆盖源实验。

## 返回结果

把新结果整个文件夹发回。`evaluation/report.md` 自动输出四列：操作、Task 1 打开下层抽屉成功、Task 2 打开上层抽屉成功、执行期间下层抽屉保持打开。

Task 1 列表示复用的成功样本，本轮没有重新执行 Task 1。源实验完整采集记录保存在 `source_collection.jsonl`；本轮所用样本记录在 `collection.jsonl`；源目录及哈希在 `manifest.json` 的 `source_evaluation` 中。

## 如何判断

- keep_position 与 reset_arm：检验夹爪位置保留时，机械臂位置复位的作用。
- reset_gripper 与 reset_both：检验夹爪位置复位时，机械臂位置复位的作用。
- keep_position 与 reset_gripper、reset_arm 与 reset_both：分别检验夹爪位置复位的作用。

keep_position 对应上一轮的 velocity，reset_both 对应上一轮的 both。两组入口状态应一致；在服务器检查具体结果是否也能重现，出现差异时先排查评估流程。

四组仍使用来自 3 个初始场景的终止状态。位置变化还会改变观测、控制器目标和接触关系；本轮只能区分两类位置复位操作的效果，不能单独确定视觉或接触机制。新组的实际效果仍待服务器实验。
