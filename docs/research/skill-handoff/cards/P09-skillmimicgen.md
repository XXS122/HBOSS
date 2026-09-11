# P09｜SkillMimicGen：学习技能启动／控制／终止，并用规划完成过渡

## 身份、版本与阅读依据

- **论文**：Caelan Reed Garrett, Ajay Mandlekar, Bowen Wen, Dieter Fox. *SkillMimicGen: Automated Demonstration Generation for Efficient Skill Learning and Deployment*。
- **日期／状态**：[arXiv:2410.18907](https://arxiv.org/abs/2410.18907)，首次公开及所读 v1 均为 **2024-10-24**；CoRL 2024 正式论文，出版记录为 PMLR 270:2750–2790，2025，不能当作两篇工作。[正式记录](https://proceedings.mlr.press/v270/garrett25a.html)
- **精读依据**：固定 arXiv v1 41页，正文 pp.1–8；重点核对附录 C、G–K、L–M、Q、T。所有数值按此版本。[全文](https://arxiv.org/html/2410.18907v1)；本地 [PDF](../sources/P09.pdf)、[逐页文本](../sources/P09.txt)、[Table M.1 页面复核图](../sources/P09-page33.png)。

## 机制与适用前提

SkillGen 将少量示范切为对象相关的接触技能段，在新场景中转换对象坐标系并重放，技能之间用 transit／transfer 运动规划连接。HSP 同时学习启动位姿、闭环控制和终止分类；部署时按给定顺序在规划器与策略之间切换。（§4 pp.4–5）

**Initiation Augmentation 已直接处理后继启动分布偏移**：生成数据时扰动启动位姿，再补一段回到原示范启动位姿的恢复动作，交给闭环技能学习。位置噪声为各轴 ±0.08m，旋转角0–80°；它扩大启动集合，但没有前驱 rollout 条件化的定向采样。（§4.5 p.5；G.3 p.22）

| 项目 | 原文条件 |
|---|---|
| 视觉／特权信息 | 控制网络用前视＋腕视 RGB 与本体状态；仿真84×84，真机120×160。数据生成须知道每技能开始时对象位姿，仿真规划用真实碰撞几何。（§5；H.1） |
| HSP 差异 | Reg 从观察回归启动位姿；Class 选择示范启动候选，并需对象位姿估计做变换；TAMP 还依赖手工规划模型决定启动和终止。（§4.6；B） |
| 训练／在线执行 | 数据生成需要仿真或真机试错交互，只保留成功轨迹；策略离线 BC-RNN，部署保留运动规划。已知技能序列，无在线 RL 微调。（§4；§7） |
| 数据与平台 | MuJoCo／robosuite／Panda，6任务×D0/D1/D2＝18变体；每任务10原始示范，每变体1000成功示范；加6个 Sawyer 变体共24K。（§5；B p.15） |
| 链长／划分 | Square、Threading、Coffee 为2技能；Piece Assembly、Nut Assembly 为4；Coffee Prep 为5。按每个变体分别生成和训练，D1/D2不能笼统称为训练未见测试。（J pp.27–28） |

## 实验与消融

| 实验（成功率%） | MimicGen | HSP-TAMP | HSP-Class | HSP-Reg |
|---|---:|---:|---:|---:|
| 主文18变体平均，单 seed | 59.1 | 85.7 | 82.9 | 72.6 |
| Nut Assembly D1 | 16.0 | 72.0 | 78.0 | 20.0 |
| Coffee Prep D2 | 0.0* | 80.0 | 74.0 | 84.0 |
| 附录3 seeds平均 | 59.6 | 86.0 | 82.1 | 71.0 |

来源：Fig.5 pp.6–7、Table T.1 p.41。*MimicGen 在 Coffee Prep D2 无法生成训练示范；0并非同等数据下训练模型的测试失败。每 checkpoint 默认50 rollout，报告训练期间**最好 checkpoint**，不是固定末次模型；附录T才是3 seeds统计。示例：Nut Assembly D1 的 HSP-Reg 为6.7±9.4、HSP-Class为74.0±7.1，说明单 seed 差距不可忽略。

| 启动增强消融（Table M.1，p.33） | HSP-Reg | 去掉增强 |
|---|---:|---:|
| Square D2 | 52 | 40 |
| Piece Assembly D2 | 50 | 14 |
| Coffee D2 | 98 | 56 |

表格对应降幅12、36、42个百分点。**M.2 文字却将后两项写成26、40%，与表格不一致**；本卡以已视觉复核的表格原值为准，不照抄文字降幅。

真机三个任务各3示范扩至100，每任务20 rollout：Milk-Bin 95%、Butter-Trash 95%、Coffee 65%（MimicGen 14%）；另一项零样本 sim-to-real Nut Assembly 为35%（基线0%）。后者只接收初始对象位姿与持续本体状态、不更新视觉，不能宣传为动态视觉迁移结果。（§6.3 p.8；C p.17；K pp.30–31）

## 作者明确声明的不足

固定技能序列；数据生成依赖对象位姿；主要是准静态刚体；HITL-TAMP 来源示范比普通遥操作更有效；sim-to-real 的观察及动作空间受限。（§7 p.8；C p.17）短引：**“requires knowledge of a fixed sequence of skills”**。

附录G.3还承认强启动噪声使很多目标碰撞或不可达、生成率降低，更聪明的采样留待未来；M.1/Q 指出启动位姿预测比终止预测更困难。普通遥操作来源的平均成功率为 MimicGen 70.0%、HSP-Class 73.8%、HSP-Reg 69.5%，明显缩小主文优势。（Table L.2 p.32）

## 面向 BOSS 的判断（分析者推断）

- **E2直接证据**：启动增强有消融；新工作不能将“给后继技能添加扰动启动与恢复数据”作为首创。应比较与前驱终止分布相关的采样是否比相同预算均匀噪声更有效。
- **移植条件**：可复用 BOSS 的对象状态与离线示范，新增技能段标注、碰撞规划与启动／终止预测。先复用视觉 BC；HSP-Class 需单列 oracle 位姿配置，避免与纯RGB BOSS基线混比。
- **计算**：原文数据生成使用8×V100节点（64CPU、400GB内存），单策略训练1×V100；这是作者配置而非最低硬件要求。（G.5/H.4）BOSS 小规模试验应报告实际有效示范率与交互成本。
- **边界**：恢复片段调整机器人到原技能入口；transfer 会合理移动被握对象。没有证据支持它必然撤销前序任务成果，也没有对所有已达谓词保持的保证。场景位置泛化不能代替 BOSS 的无关谓词偏移评测。

检索记录：2026-09-11；按 arXiv 标识核查版本，官方 HTML 定位 `Initiation Augmentation`、`Limitations`、`M.2`，再用本地 PDF 核验正文与表格；PMLR 用于核实会议信息。
