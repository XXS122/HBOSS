# BOSS 项目画像与评测审计

核查日期：2026-09-11。证据基准为用户提供的 `C:/Users/13968/Desktop/Boss.pdf`（10 页，首页标注 arXiv:2502.15679v1）、当前工作目录代码，以及作者公开资料。这里的“代码发现”来自静态检查，未运行训练或机器人实验。

## 1. 当前项目是什么

这是 **BOSS: Benchmark for Observation Space Shift in Long-Horizon Task** 的开源实现，README 指向同名论文。它是 LIBERO 上的技能组合鲁棒性基准，不是新的通用技能规划器。规划顺序被假设为已知且正确；核心问题是前序技能留下的场景变化使单独训练的后续视觉策略失效。

论文 §III（PDF p3）采用 POMDP。用 `Pre` 和 `Eff` 表示当前操作的前置条件与效果，将不属于两者的谓词定义为技能无关谓词。它们在符号模型中不影响该技能的可行性，却可能改变图像，例如碗里多了一个已经放好的物体。研究目标应是让移动碗的策略适应这个变化，而非把物体取出来以恢复训练图像。

**分析边界：**“不在符号 Pre/Eff 中”不能自动证明真实动力学无关。质量、碰撞、遮挡和支撑关系可能未被抽象谓词充分表达。这是设计实验时需要检验的建模条件，不是已由 BOSS 证实的因果结论。

## 2. 三类评测及训练链路

| 内容 | 论文描述 | 当前实现定位 |
|---|---|---|
| 原子技能 | 从 LIBERO-100 选 44 个单技能，12 个场景，Franka Panda | `scripts/form_boss_44_dataset.py`；`libero/libero/benchmark/__init__.py:164` |
| CH1 / C1 | 44 个原始任务与 44 个单谓词变体配对 | `libero/mappings/ch1.json`；`libero/lifelong/eval_skills_affected_by_oss.py:89` 根据映射选原技能 checkpoint |
| CH2 / C2 | 每个原技能对应 2 个修改、3 个修改两组，共 88 个变体 | `libero/mappings/ch2_2_modifications.json`、`ch2_3_modifications.json` |
| CH3 / C3 | 10 条手工设计的三技能链 | `libero/lifelong/eval_skill_chain.py:75`；动态注册 `CH3_1` 至 `CH3_10` |
| BC 训练 | BC-ResNet-RNN、BC-ResNet-T、BC-ViT-T，分别学习技能 | `libero/lifelong/train_skills.py:139` 每任务新建 PolicyStarter |
| OpenVLA | 原子任务数据微调的共享 VLA；按任务语言切换调用 | `openvla/experiments/robot/libero/eval_openvla_ch3.py:157`、`:296` |
| 增强 | RAMG 修改 BDDL；在新场景重放原示范动作 | `RAMG/DA_demos_generation.py:76` → `scripts/DemoProcessor.py:173` |

BC 的实际观测由 `libero/configs/data/default.yaml` 的 `obs.modality` 决定：第三人称 RGB、关节角、夹爪状态。文件虽有 `use_eye_in_hand: true`，活动的 RGB 列表仅有 `agentview_rgb`，不能凭前一布尔字段声称用了腕相机。论文 §V-A3（p5）同样排除 BC 腕视图，并说明 OpenVLA 仅用第三人称图像。动作是 7 维相对位移/夹爪控制，论文控制频率 20 Hz。

## 3. Skill handoff 实际发生了什么

```mermaid
flowchart LR
    A[执行当前技能] --> B[环境判定当前技能成功]
    B --> C[提取当前 MuJoCo 状态]
    C --> D[在下一个技能环境中恢复状态]
    D --> E[覆盖机械臂初始姿态及速度切片]
    E --> F[重建观测并执行下一技能]
```

- `SequentialEnv.step`（`libero/libero/envs/env_wrapper.py:329`）在 `done` 后更新任务编号，把前序 `get_sim_state()` 交给下一个环境的 `set_init_state()`（`:345`）。因此它不是在一个任务对象中只改语言；状态跨环境复制还隐含相容的模型/状态布局。
- BC 评测 `initialize_robot_state`（`libero/lifelong/eval_skill_chain.py:43`）以保存的初始化状态覆盖 `[1:10]` 和 `[41:]`；在每次切换后调用（`:237`）。OpenVLA 也有同样逻辑（`eval_openvla_ch3.py:81`、`:303`）。代码是“从初始化样本复制切片”，不是显式将速度设为数值零；“zeroize”只是注释。
- 论文 §IV-E（p5）明确解释：重置机械臂到中立姿态，以排除动态衔接可行性问题。这里的“Real Long-Horizon Task”指实际串联执行的任务，**不等于真机实验**。
- 切换依赖仿真成功判定；并未学习视觉 readiness 检测器。`complete_id` 支持前缀完成率，最终 `done` 支持整链完成率（BC 评测 `:254–271`）。后续技能执行后不会重新逐项检查此前所有目标谓词，因此“历史上各技能曾成功”不自动等于“最终全部成果仍保持”。

结论：原始 BOSS 适合隔离研究场景残留引发的 OSS；若研究接触、抓持或速度连续性，必须另设无重置协议，不能将其结果混入原始 CH3。

## 4. 指标审计

令原技能成功率为 \(p_i^0\)，修改场景成功率为 \(p_i^m\)。

\[
\mathrm{RPD}_i=(p_i^0-p_i^m)/p_i^0.
\]

论文 p6 的 67%、35%、34%、54% 是**在 RPD>0 的受影响任务中**分别平均，不能写成所有 44 任务的平均成功率损失。对应受影响任务比例为 68%、66%、50%、66%。相对下降也不等于下降了相同数量的百分点。原始成功率为零时该比率未定义，不能解释为无 OSS。

论文把 \(U=\prod_i p_i^0\) 称为 Chain Upper Bound。p5 对 DUBR 的文字顺序存在歧义：文字描述实际率与 U 之差，后续结果却以“越正说明损失越大”为解释。若按后者，应该写成 \((U-p_{chain})/U\)。本报告不声称已核实作者绘图代码；在搜索到的评测入口里只看到成功率落盘，未找到 RPD/DUBR 最终绘图实现。

**本报告的数学分析：**一般情况下 \(\prod_i p_i^0\) 只是独立原始分布成功率的乘积参考值。真实链成功率为条件概率连乘；只有适当分布匹配/独立性或每阶段条件成功率不超过参考率等额外条件成立，它才可视为上界。报告将它称为“论文所称上界”，不给它无条件理论保证。论文 p6 将 U=0 的部分条形显示为 0；重新评估时应报告 NA 和样本数，同时保留作者图示约定的说明。

## 5. 数据与复现条件的静态核查

1. **种子路径。**论文报告三个随机种子的均值。配置默认 `seed:10000`；BC/CH3 入口的 `--seed` 用于目录命名，而 `env.seed` 读取 checkpoint 的 `cfg.seed`，未见用 args.seed 覆盖它。OpenVLA 配置另有固定 `seed=10000`。`SequentialEnv.seed` 的 `seed = np.random.seed(seed)` 会把局部变量变成 `None` 后传给子环境（`env_wrapper.py:318`）。不能仅改 CLI 参数就认定完成独立种子实验；实际影响仍需运行复核。
2. **训练划分。**配置有 `train_dataset_ratio:0.8`，但当前 BC `get_dataset` 调用未传 `filter_key`，数据封装默认也不使用该比例。不能据配置名称宣称已经进行了 80/20 示范划分。新方法必须明确按原始示范及其增强后代分组，避免同源轨迹泄漏。
3. **RAMG 过滤。**论文 p7 说重放后过滤失败示范；当前 `DemoProcessor.py:233` 无条件创建每条轨迹，在 `:267` 才把成功/失败索引写入旁路 pkl，同时所有输出轨迹最后一帧 rewards/dones 被设置为 1。当前所读生成入口未展示后续过滤步骤，故不能把生成目录默认当作已清洗数据。
4. **增强状态的可信度。**同一脚本 `:154` 注释提及外部 robosuite 本地修改；`:178` 的重放状态一致性断言被注释。输出 `states` 是原始轨迹切片，而观测/robot_states 来自重放。若新方法需要交接终态或因果配对，必须从实际重放中重新采集仿真状态并验证对应关系，不能直接把旧 states 当作新场景 ground truth。
5. **本地条件。**当前工作目录没有 `.git`，也未见 README 要求下载的根级 assets、datasets、训练 checkpoints；本次没有取得运行复现实验的证据。README 里还存在三修改命令及 DA 脚本路径与实际文件不一致之处。以上只记录，不在研究任务中顺手修代码。

这些发现是新实验前应核对的条件，不足以证明论文原实验发生了相同问题。

## 6. BOSS 的版本差异与作者不足

本地 PDF p7/§VI 报告原始与增强训练后在修改任务上的成功率：RNN 0.25→0.31、ResNet-T 0.67→0.54、ViT-T 0.74→0.64、OpenVLA 0.54→0.54。这里能支持的是**该 RAMG 增强方案和所测基线未普遍改善 OSS**，不能推出所有数据增强都无效。

作者明确提出的不足（p7）：组合场景难以穷举；RAMG 限于仿真数据生成，不能直接扩展到真实数据；现有架构缺少针对 OSS 的处理。这些是作者解释，而不是经本报告复现确认的机制结论。

[作者项目页](https://boss-benchmark.github.io/) 另列 R3M、LIV 和 3D Diffuser Actor 实验（该页“Other mitigations”），本地 v1 PDF 未包含。这些数字只作为“公开项目页补充结果”，不与本地论文表格合并计算。页面显示 RA-L / ICRA 2026；[作者所在机构的发表记录](https://experts.colorado.edu/display/pubid_391802) 给出 RA-L 10(9):8882–8889，2025，DOI 10.1109/LRA.2025.3585390。发表年份与后续会议展示年份应分开。

最后，BOSS 对早期过渡策略的批评需要限定范围：最小扰动物体的 SPIN connectors、SkillMimicGen 的 free-space transfer，以及 BATON 的下游约束检索，已构成“所有过渡都必须撤销前序成果”这一泛化判断的反例。它们是否解决了 BOSS 的 OSS，仍需单独测试。
