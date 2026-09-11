# 检索、筛选与覆盖日志

检索和复检日期均为2026-09-11（Asia/Shanghai）。首次公开纳入窗口2024-01-01至2026-09-11；优先2024-09-11之后。正式发表和公开预印本均接受；预印本不冒充同行评审结果。不同版本保留首次公开日期与实际阅读版本，按工作去重。

## 1. 实际检索流程

先读用户Boss.pdf与本地README/评测/数据代码，形成BOSS问题边界；随后组合学术检索、arXiv元数据/全文、NeurIPS/PMLR、作者项目页和方法参考文献。检索服务用于发现，结论回到原始论文和官方资料核实。没有订阅数据库、引文数量或聚合网站评分作为筛选门槛。

本研究使用论文调研及系统综述技能的检索/证据提取流程；按用户计划扩展到多官方来源及Markdown研究包。全文提取分三组独立进行，主报告再做口径综合和反例复检。最终候选和所有文件由主任务验收。

| 组 | 实际使用的检索式/入口 | 主要目的与结果 |
|---|---|---|
| S01 学术起检 | arXiv API `skill chaining`；max-results40；relevance；start2024-01-01、end2026-09-11 | 先建立种子集合；网络首次失败后授权重试成功。输出未完整保存为原始命中表，不报告虚构的全部命中数 |
| S02 衔接/年份 | `"skill chaining" "2025" manipulation`；`"skill chaining" "2024" manipulation`；`robot skill handoff chaining "2026" visual policy` | 对齐、恢复、2026新工作 |
| S03 状态分布 | `"robot" "handoff" "2025" policy distribution`；`"robot" "skill chaining" "distribution" "2026" -site:emergentmind.com -site:alphaxiv.org` | 前驱终态/后继可执行性，不依赖精确术语handoff |
| S04 BOSS视觉 | `"observation space shift" robotics 2026`；`"Compose by Focus" arxiv` | BOSS后续和相关对象表示 |
| S05 恢复/系统 | `"RecoveryChaining" arxiv`；`"AtomBridge" arxiv`；`"skill" "handoff" "2026" "manipulation" arxiv` | 局部恢复、状态校准、契约 |
| S06 数据 | `"SkillGen" "2024" "2025"`；`robot "SkillGen" "Data" demonstration`；`"MimicGen" "2024" "DexMimicGen"` | 组合示范、初态增强；同名非机器人项目排除 |
| S07 主动学习/奖励 | `"Planning to Practice" robot 2024`；`"Practice Makes Perfect" arxiv`；`"Auxiliary Reward Generation"` | practice/目标距离旁支，决定优先级 |
| S08 反事实/干预 | `robot skill "counterfactual" "irrelevant" manipulation`；`robot manipulation "counterfactual" "invariance" policy 2024 2025 2026`；`skill chaining "terminal states" "augmentation" visual` | 找到RoCoDA，启动第二轮反例复检 |
| S09 成果 | `robot skill handoff "preserving" predicates effects` | 持续成果、前置和恢复义务 |
| S10 版本/来源 | `"SCaR: Refining" site:openreview.net/forum`；`"SPIN" "distilling" "CoRL" 2025 Jung`；`"Long-VLA" CoRL`；`"AtomSkill" IROS` | 版本/会议信息；OpenReview无精确结果时回NeurIPS正式全文 |
| S11 BOSS与补充 | `"BOSS" "Observation Space Shift" "IEEE" DOI`；`"AtomBridge" "supplementary" "2602.09430"` | BOSS发表与展示年份；AtomBridge补充材料未取得独立文件 |
| S12 最终书目核对 | `"Generative Factor Chaining" site:proceedings.mlr.press`；`"Task-Oriented Hierarchical Object Decomposition" site:proceedings.mlr.press`；`"RecoveryChaining" ICRA 2025` | PMLR原始条目；RecoveryChaining最终核实为IROS2025，未沿用查询中的ICRA假设 |

更细的V01–V11和H01–H09查询、原文段落与改变结论的过程见[视觉复检](gaps-visual-review.md)和[成果复检](gaps-handoff-review.md)。后者包含同义术语、最接近方法、经典因果链接、后续v2及2026年8–9月新版本。

## 2. 超过20篇的初检与排除记录

以下是**可追溯的筛选记录，不是所有搜索结果总数**。正式候选20篇另见[候选表](02-candidates.md)；下面至少5篇在窗口内完成题名/摘要筛查后未进入最终20篇，因此有据可核的初检集合超过20。第二轮补充反例也保留，不强行把所有阅读压进20篇。

| 工作/官方来源 | 首次公开/范围 | 筛选决定和理由 |
|---|---|---|
| [Practice Makes Perfect: Planning to Learn Skill Parameter Policies](https://arxiv.org/abs/2402.15025) | 2024-02-22；v2 2024-05-18 | 窗口内；主动练习/参数学习而非直接视觉组合偏移，被RoCoDA替换；保留无reset practice背景 |
| [DUSDi](https://arxiv.org/abs/2410.11251) | 2024-10-15；v2 2026-07-11；NeurIPS2024 | 初期候选，偏解耦技能发现；被第二轮更直接的CoRe替换。旧元数据保留为X03 |
| [BestMan](https://arxiv.org/abs/2410.13407) | 2024-10-17 | 平台/统一接口；出现skill chain不足以提供本题所需的分布兼容机制证据 |
| [DETACH](https://arxiv.org/abs/2508.07842) | 2025-08公开 | 混合解耦专家与跨域学习；按摘要的本题直接性弱于明确handoff工作，不计全文精读 |
| [Mixed Discrete and Continuous Planning using Shortest Walks in Graphs of Convex Sets](https://arxiv.org/abs/2507.10878) | 2025-07公开 | 几何/混合规划；非本题视觉技能组合主线，不从标题推断已解决OSS |
| [CAIAC](https://arxiv.org/abs/2405.18917) | 2024-05-29；v2 2024-12-12 | 二轮近邻；局部因果影响已有，定向读方法/边界；不重复计入20 |
| [AFP](https://arxiv.org/abs/2607.10655) | 2026-07-12；v2 2026-09-07 | 二轮最新近邻；注意力监督/梯度冲突机制反证，定向全文段落 |
| [Embodied Interpretability](https://arxiv.org/abs/2605.00321) | 2026-05-01；v2 2026-06-10 | 遮蔽前后动作差异反例；定向方法阅读 |
| [Inverse Manipulation through Symbolic Planning and Residual Operator Learning](https://arxiv.org/abs/2606.05248) | 2026-06-03 v1 | 二轮强反例，predicate fences已实现；窄任务与向前BOSS不同，仍承认机制重叠 |
| [Self-Evolving Just-In-Time Memory](https://arxiv.org/abs/2607.16247) | 2026-07公开 | 关系记忆/时序义务旁证；只读相关段落，不冒充实验全面审计 |

以上初检并非严格PRISMA全自动数据库导出，没有可靠的“总命中→去重→排除”流水数字。可确认的是最终20个不同工作和10个核心全文；不把未保存/被截断的工具输出补写成看似精确的计数。

## 3. 更早的奠基工作单列

| 背景工作 | 对本题的概念作用 | 不计入理由 |
|---|---|---|
| [T-STAR / Adversarial Skill Chaining](https://arxiv.org/abs/2111.07999) | 终止分布正则已有，SCaR的重要前驱 | 2021，早于窗口 |
| [Sequential Dexterity](https://arxiv.org/abs/2309.00987) | 灵巧操作长链先例，用于防止“技能串联首次”式主张 | 2023，早于窗口；非本次完整证据卡 |
| [ASC: Adaptive Skill Coordination](https://arxiv.org/abs/2304.00410) | 视觉技能协调与OOD纠正已有 | 首发2023-04-01，v2 2023-11-19 |
| [经典因果链接/Planning by Rewriting](https://www.cs.cmu.edu/afs/cs/project/jair/pub/volume15/ambite01a-html/node7.html) | 条件生产、消费、威胁和合法义务消解不是新概念 | 奠基背景，仅核对相关理论段落 |

LIBERO与OpenVLA作为BOSS依赖/基线背景，不占候选。BOSS的具体实现与论文版本单列，不按“引用次数最高”选择核心。

## 4. 引用追踪、版本与停止条件

从BOSS所引过渡方法、SCaR所引T-STAR、DeCo所引连接方法等参考文献向后追踪；通过题名/BOSS/机制关键词向前找新工作，核对arXiv版本和官方出版/作者页。向前检索**没有**取得一个完整、可导出的所有被引文献图，因此不能声称穷尽引用网络。

第二轮发现RoCoDA阶段过滤、MoMaStage v2、Inverse Manipulation fences、AFP九月v2和CoRe后，撤销相应初步空白。最终停止在20候选/10核心证据卡可核查、剩余方向明确N1且所有强反例已纳入比较；并非停止在“搜不到新论文”。

局限：未取得所有独立补充视频/数据/作者代码；未重跑任何论文实验；部分发表状态只能核作者声明；SCaR全球首次日未知；最新预印本可能后续改动。原文数值不一致、统计缺失和未经验证的作者解释均保留，不以猜测填表。
