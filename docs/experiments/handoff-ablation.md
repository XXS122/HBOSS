# 技能切换对照实验

**目标：确定技能 2 → 3 失败与机械臂位置、速度及切换前等待的关系。复用 pilot 模型，不重新训练。**

| 组名 | 操作 |
|---|---|
| none | 保留前序技能终止时的位置和速度 |
| position | 仅把机械臂和夹爪关节位置复位到参考初始状态 |
| velocity | 仅把机械臂和夹爪关节速度清零 |
| both | 同时进行位置复位和速度清零 |
| settle | 不修改关节位置或速度，固定当前末端目标位姿、保持夹爪开合，运行仿真等待停止 |
| legacy | 使用现有代码的 `[1:10]`、`[41:]` 复位切片 |

先收集 20 个“下层抽屉打开、上层抽屉尚未打开”的状态，再对每个状态使用 3 个评估 seed 运行六组，共 360 次评估。模型由程序自动切换。

- 各组后续模型最多执行 400 步，控制频率 20 Hz。等待组额外最多 40 步（2 秒），超时计失败。
- 停止条件：机械臂各关节速度不超过 0.02 rad/s、夹爪各关节速度不超过 0.002 m/s，连续满足 5 个控制步。这是本轮操作定义，不是已验证的最佳阈值。
- 等待过程中物体仍可运动。速度组只清零机械臂和夹爪的速度，不清零物体速度。
- 记录后续成功、前序目标在每个控制步是否保持、结束时是否保持、等待时间和执行时间。“始终保持”的采样频率为 20 Hz，未检查每个物理子步。

## 运行

在服务器 HBOSS 根目录、已有 `boss-bc` 环境和 pilot 权重下执行。资产、本地 BERT 和 `.boss/server/config.yaml` 沿用已完成的安装配置。

先检查 2 个状态、1 个 seed（12 次评估）：

```bash
python scripts/run_handoff_ablation.py \
  --model-dir experiments/boss_44/handoff_pilot_20260911_045322_1fa6d774/BCTransformerPolicy_seed10000/run_001 \
  --states 2 --eval-seeds 10000
```

确认没有异常、视频正常后，运行默认规模：

```bash
python scripts/run_handoff_ablation.py \
  --model-dir experiments/boss_44/handoff_pilot_20260911_045322_1fa6d774/BCTransformerPolicy_seed10000/run_001
```

终端实时输出，并保存 `results/handoff_ablation/<运行编号>/ablation.log`。每次运行独立保存，不覆盖已有结果。每次运行只收集一次状态，各组复用。采集轮流使用已有初始状态，每次使用不同的采集 seed。最多尝试目标样本数的 10 倍（默认 200 次），得到 20 个成功终止状态就停止；不足则报错，不生成完整比较结果。

## 返回哪些结果

把整个 `results/handoff_ablation/<运行编号>/` 文件夹发回。`evaluation/` 包含：

- `summary.csv`：分组及分 seed 的成功率、前序目标保持次数、等待超时数。
- `episodes.jsonl`：每次结果；配对键为 `state_id` 和 `evaluation_seed`。
- `collection.jsonl`、`snapshots/`：采集成功与失败记录，每次采集的初始状态编号与 seed，原始状态、参考状态、干预后状态、模型入口状态和最终状态。
- `joint_layout.json`、`manifest.json`：关节地址、协议参数、初始状态数量及各初始状态贡献的成功样本数、模型/代码/初始状态文件哈希。
- 六个 MP4：第一个状态、第一个 seed 的各组视频。等待组视频包含等待阶段。

## 如何解释

先比较 none 与 velocity、position、both，再检查 settle 是否改善成功率且不破坏前序目标。legacy 用于检查旧复位切片与明确的位置/速度操作之间的差别。效果均待实测；位置复位也会改变摄像头图像和接触，不能单凭成功率区分视觉因素和物理因素。

协议 v2 支持重复使用初始状态采集。如果文件中只有 3 个初始状态，20 个终止状态仍来自这 3 个初始场景，不能当作 20 个独立场景。三个评估 seed 还会复用这批终止状态。比较各组时按终止状态配对；估计场景泛化能力时按初始状态分组，不能把 60 次评估当作独立场景。重复采集未强制平衡各场景的成功样本数，具体数量见 manifest.json 的 accepted_by_initial_index。第一轮只涉及一对技能、一个训练 seed，不据此声称解决所有技能组合。

## 实现边界

本实验在独立后续环境中恢复物理状态，并统一初始化 OSC 控制器：末端目标为当前位姿，零空间参考为参考初始关节位置，夹爪累计命令对应当前开合位置；不复制前序控制器历史。仿真控制输入与求解器历史也按统一规则初始化，模型历史清空。等待结束后采用相同的控制器初始化规则。

因此它是物理状态干预的对照实验，不等于同一个环境内连续控制。legacy 保留的是旧状态切片操作，控制器恢复协议统一后，绝对成功率不应直接与旧 pilot 的 48/58 对比。

服务器运行会检查关节布局、Panda 夹爪执行器映射和物理状态复制结果。本地测试不包含真实 MuJoCo、GPU 推理和渲染；小规模服务器运行仍是必要验证。

控制器接口依据 [robosuite 1.4.1 OSC 源码](https://github.com/ARISE-Initiative/robosuite/blob/v1.4.1/robosuite/controllers/osc.py) 和 [夹爪动作缩放源码](https://github.com/ARISE-Initiative/robosuite/blob/v1.4.1/robosuite/robots/manipulator.py)。
