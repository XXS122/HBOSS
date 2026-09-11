# 20篇候选及筛选决定

检索截止2026-09-11；首次公开窗口2024-01-01至截止日，优先2024-09-11之后。BOSS单列，不计入20篇。不同版本和旧标题合并；P07只确认2024年正式发表及10月7日机构存档，未虚构全球首次日期。所列“所查版本”并不等于已完成全文精读，阅读深度见最后一列。

**最终核心10篇：P01、P03、P04、P05、P06、P07、P08、P09、P10、P15。** HODOR有额外支持性全文卡；RoCoDA/MoMaStage用于定向复检。这些额外阅读不重复计入10篇。第二轮发现CoRe后替换弱相关DUSDi候选，并取代HODOR的核心名额；这体现按证据更新筛选，而非固定清单。

| ID / 全名（官方来源） | 首次公开 | 所查版本 / 日期 | 发表状态 | 选择及阅读深度 |
|---|---|---|---|---|
| P01 [Compose by Focus: Scene Graph-based Atomic Skills](https://arxiv.org/abs/2509.16053) | 2025-09-19 | v2 / 2026-03-08 | ICRA 2026 accepted（作者页） | **核心全文**；直接研究组合场景视觉偏移；与BOSS问题最贴近的表示基线。 [证据卡](cards/P01-compose-focus.md) |
| P02 [Task-Oriented Hierarchical Object Decomposition for Visuomotor Control](https://arxiv.org/abs/2411.01284) | 2024-11-02 | v1 / 2024-11-02 | CoRL 2024 | 候选；保留局部/全局视觉的直接近邻；全文支持性阅读，链实验缺少定量统计，核心名额让给CoRe。 [证据卡](supporting/P02-hodor.md) |
| P03 [Foresight Residual RL for Long-Horizon Robot Manipulation with Vision-Language-Action Models](https://arxiv.org/abs/2607.16506) | 2026-07-17 | v1 / 2026-07-17 | IROS 2026 accepted（arXiv作者声明） | **核心全文**；后继成功预测直接优化前驱终态，有同骨干残差消融。 [证据卡](cards/P03-foresight.md) |
| P04 [Don't Drop the BATON: Long-Horizon Robot Manipulation via Agentic Subtask Exploration and Transition-aware Memory](https://arxiv.org/abs/2608.16889) | 2026-08-17 | v1 / 2026-08-17 | 公开预印本 | **核心全文**；入口契约、边界修复和剩余计划约束直接处理handoff。 [证据卡](cards/P04-baton.md) |
| P05 [Diagnosing Semantic Handoff Failures in Agent-Orchestrated Vision-Language-Action Skill Composition](https://arxiv.org/abs/2607.06256) | 2026-07-07 | v2 / 2026-07-15 | RSS 2026 SemRob Workshop | **核心全文**；直接诊断clean/chained落差；小规模、判定器不完全匹配须明示。 [证据卡](cards/P05-semantic-handoff.md) |
| P06 [AtomBridge: Agentic VLA Inference Plugin for Long-Horizon Tasks in Scientific Experiments](https://arxiv.org/abs/2602.09430) | 2026-02-10 | v2 / 2026-08-14 | 公开预印本 | **核心全文**；完成检测、机器人状态校准及技能检索，可检查仿真/真机衔接。 [证据卡](cards/P06-atombridge.md) |
| P07 [SCaR: Refining Skill Chaining for Long-Horizon Robotic Manipulation via Dual Regularization](https://proceedings.neurips.cc/paper_files/paper/2024/hash/ca92ff06d973ece92cecc561757d500e-Abstract-Conference.html) | 2024-10-07（已核实机构存档；全球首次日未确认） | NeurIPS 2024正式版 / 2024正式版 | NeurIPS 2024 | **核心全文**；双向终止—启动分布对齐的必要最近邻；特权状态限制另列。 [证据卡](cards/P07-scar.md) |
| P08 [DeCo: Task Decomposition and Skill Composition for Zero-Shot Generalization in Long-Horizon 3D Manipulation](https://arxiv.org/abs/2505.00527) | 2025-05-01 | v2 / 2026-02-15 | IEEE RA-L 2026 | **核心全文**；3D视觉技能起点桥接；有桥接数量消融及未见组合实验。 [证据卡](cards/P08-deco.md) |
| P09 [SkillMimicGen: Automated Demonstration Generation for Efficient Skill Learning and Deployment](https://arxiv.org/abs/2410.18907) | 2024-10-24 | v1 / 2024-10-24 | CoRL 2024；PMLR 270（2025） | **核心全文**；数据生成、HSP启动条件与初态增强共同作用，有去增强消融。 [证据卡](cards/P09-skillmimicgen.md) |
| P10 [SPIN: distilling Skill-RRT for long-horizon prehensile and non-prehensile manipulation](https://arxiv.org/abs/2502.18015) | 2025-02-25 | v3 / 2025-05-07 | CoRL 2025 | **核心全文**；低物体扰动connector与鲁棒重放，是成果保持泛化批评的反例。 [证据卡](cards/P10-spin.md) |
| P11 [RecoveryChaining: Learning Local Recovery Policies for Robust Manipulation](https://arxiv.org/abs/2410.13979) | 2024-10-17 | v2 / 2025-03-07 | IROS 2025（MERL正式发表记录） | 候选；局部失败恢复直接相关；候选全文可得，机制覆盖由SCaR/DeCo/SPIN/CoRe代表，不列完成精读。 |
| P12 [Generative Factor Chaining: Coordinated Manipulation with Diffusion-based Factor Graph](https://arxiv.org/abs/2409.16275) | 2024-09-24 | v1 / 2024-09-24 | CoRL 2024 | 候选；联合因子约束协调技能参数，偏特权几何规划；全文可得，未列核心精读。 |
| P13 [Long-VLA: Unleashing Long-Horizon Capability of Vision Language Action Model for Robot Manipulation](https://arxiv.org/abs/2508.19958) | 2025-08-27 | v2 / 2025-08-28 | CoRL 2025（作者页） | 候选；阶段相关视觉训练和长任务数据是补充近邻；未单独隔离技能边界对齐。 |
| P14 [Learning Semantic Atomic Skills for Multi-Task Robotic Manipulation](https://arxiv.org/abs/2512.18368) | 2025-12-20 | v2 / 2026-07-02 | IROS 2026 accepted（作者页） | 候选；语义原子技能/关键姿态连接相关；只作元数据与方法摘要筛选，未完成全文审计。 |
| P15 [Imagining Recovery: Inference-Time Counterfactual Realignment for Vision-Language-Action Models](https://arxiv.org/abs/2608.14822) | 2026-08-14 | v1 / 2026-08-14 | 公开预印本 | **核心全文**；第二轮发现的强直接反例：累计成果保护、最小反事实恢复与动作块交接；提升至核心。 [证据卡](cards/P15-core.md) |
| P16 [DexMimicGen: Automated Data Generation for Bimanual Dexterous Manipulation via Imitation Learning](https://arxiv.org/abs/2410.24185) | 2024-10-31 | v2 / 2025-03-06 | ICRA 2025（官方仓库） | 候选；双臂同步与交接示范生成；本题优先单臂串联及观测偏移，SkillMimicGen代表数据主线。 |
| P17 [Auxiliary Reward Generation with Transition Distance Representation Learning](https://arxiv.org/abs/2402.07412) | 2024-02-12 | v1 / 2024-02-12 | 2024公开预印本；后续发表状态未核实 | 候选；BOSS所引过渡距离奖励近邻；在总时间窗内但早于优先24个月，偏目标距离而非组合视觉。 |
| P18 [MoMaStage: Skill-State Graph Guided Planning and Closed-Loop Execution for Long-Horizon Indoor Mobile Manipulation](https://arxiv.org/abs/2603.08383) | 2026-03-09 | v2 / 2026-09-03 | 公开预印本 | 候选；v2累积技能状态和保留已完成任务的恢复很重要；定向全文复检，非十篇统一卡。 |
| P19 [See and Switch: Vision-Based Branching for Interactive Robot-Skill Programming](https://arxiv.org/abs/2603.08057) | 2026-03-09 | v2 / 2026-06-29 | 公开预印本 | 候选；视觉分支/异常检测相关，但用户门控离线决策窗口区别于自主handoff；只作候选。 |
| P20 [RoCoDA: Counterfactual Data Augmentation for Data-Efficient Robot Learning from Demonstrations](https://arxiv.org/abs/2411.16959) | 2024-11-25 | v2 / 2025-05-20 | ICRA 2025 | 候选；阶段因果增强与成功过滤是创新反例；全文定向复检，非十篇统一卡。 |

## 筛选规则与不纳入核心的含义

按直接衔接机制、证据充分度、BOSS视觉适配、时间接近度作定性排序，不用引文量评分。全文可取得只是必要条件；不将下载但未读透的PDF算作精读。核心同时覆盖前驱优化、显式桥接、训练数据和视觉表示，保留两篇诊断/系统工作用于检验接口条件。此选择是透明的主题取样，不能证明它们是唯一或绝对排名前十。

P19采用v2（2026-06-29）：约900次rollout、8名新手、3任务；分支准确率与决策状态的异常检测不能写成自主整链成功率。旧版576次等数字不混入此版本。P10旧题“From planning to policy…”与SPIN去重；P09 SkillGen为SkillMimicGen别称。P16初始workshop与后来的ICRA正式记录分开，不按旧页页眉定当前状态。

初检排除表、检索式及来源覆盖局限见[检索日志](06-search-log.md)。日期/作者来自归档元数据，发表状态的额外依据见[来源索引](07-source-index.md)。
