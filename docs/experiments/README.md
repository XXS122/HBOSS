# BOSS 第一轮 Skill Handoff 实验

目标是先测清楚原始技能能力、观测偏移下的性能下降和链式执行的交接敏感性，再决定研究方法。默认使用仓库的 **BC-ResNet-Transformer**，从示范训练独立技能；本轮没有新增策略架构或训练目标，也没有已验证的新方法效果。

## 1. 上传代码与放置数据

把修改后的项目上传 Ubuntu 22.04 服务器，在项目根目录执行后文命令。按原 README 放置解压文件：

```text
BOSS-main/
├── assets/
│   ├── articulated_objects/
│   ├── stable_hope_objects/
│   └── stable_scanned_objects/
├── datasets/
│   └── libero_90/                 # 也识别 LIBERO-90
│       └── <任务名>_demo.hdf5
├── benchmark_scripts/install_bc_a100.sh
└── scripts/run_handoff_experiment.py
```

若已经整理为 `datasets/boss_44/`，可以直接使用。目录内应直接包含 HDF5 文件，不能多套一层解压目录。来源为原 README 的 [assets](https://drive.google.com/file/d/1Rh24XyUy7Y5aE1jhiW2sZmpNh90-4s02/view?usp=sharing) 和 [LIBERO-100](https://utexas.box.com/shared/static/cv73j8zschq8auh9npzt876fdc1akvmk.zip)。只需其中 LIBERO-90 的示范。

**本流程不需要执行旧的 `form_boss_44_dataset.py`。** 新准备脚本按实际技能注册表选取 44 个文件，默认建立软链接并保留全部原始示范；已有 `boss_44` 不覆盖。同时将根目录 assets 链接到原对象代码硬编码的 `libero/libero/assets`，生成当前服务器的 `.boss/server/config.yaml`。这些步骤每次启动自动检查，原 `.boss/config.yaml` 不修改。

不需要先下载 BOSS 策略权重，本流程会训练并保存它们。语言编码器改为**仅从本地目录加载**，训练和评测共用同一路径，不再自动联网下载 BERT。

在 [google-bert/bert-base-cased 官方文件页](https://huggingface.co/google-bert/bert-base-cased/tree/main) 下载以下五个文件，名称保持不变：

- [config.json](https://huggingface.co/google-bert/bert-base-cased/resolve/main/config.json?download=true)
- [pytorch_model.bin](https://huggingface.co/google-bert/bert-base-cased/resolve/main/pytorch_model.bin?download=true)
- [tokenizer_config.json](https://huggingface.co/google-bert/bert-base-cased/resolve/main/tokenizer_config.json?download=true)
- [tokenizer.json](https://huggingface.co/google-bert/bert-base-cased/resolve/main/tokenizer.json?download=true)
- [vocab.txt](https://huggingface.co/google-bert/bert-base-cased/resolve/main/vocab.txt?download=true)

权重 `pytorch_model.bin` 约 436 MB，下载实际文件而非 Git LFS 指针。当前固定的 Transformers 4.21.1 环境使用这个 PyTorch 文件，不用下载 TensorFlow/Flax 权重，也不要只放 `model.safetensors`。

上传后的默认目录如下（项目名为 HBOSS 或 BOSS-main 均可，路径由代码位置计算）：

```text
HBOSS/bert/bert-base-cased/
├── config.json
├── pytorch_model.bin
├── tokenizer_config.json
├── tokenizer.json
└── vocab.txt
```

这是一份直接包含模型文件的目录，不是 Hugging Face 的 `blobs/snapshots` 缓存父目录。按默认位置放好后，直接使用后文的 smoke/pilot 命令。若放在其他位置，在同一终端设置：

```bash
export BOSS_BERT_PATH=/data/models/bert-base-cased
python scripts/run_handoff_experiment.py --stage smoke
```

启动器的子进程会继承此路径。运行预检检查五个文件是否齐全，实际模型/分词器加载使用 `local_files_only=True`；缺文件直接报错，不回退到在线下载。`runtime.json` 记录解析后的路径。BERT 文件仍被 `bert/` 的 Git 忽略规则排除，需单独传输。

若只下载了 LIBERO-100 压缩包，仍需先解压，将其中的 `libero_90` 目录放到 `datasets/libero_90/`（里面直接是 HDF5 文件）。`run_handoff_experiment.py` 会调用 `prepare_handoff.py` 自动建立 `datasets/boss_44/`；不用额外执行旧的 `form_boss_44_dataset.py`。也可以先单独运行 `python scripts/prepare_handoff.py --inspect-data` 检查整理结果。

## 2. 安装 BC 环境

假设使用单张 A100 80GB，服务器已有可用 NVIDIA 驱动和 conda。先用 `nvidia-smi` 确认 GPU。BC 单独建环境：

```bash
conda create -n boss-bc python=3.10 -y
conda activate boss-bc
cd /你的路径/BOSS-main
bash benchmark_scripts/install_bc_a100.sh
```

安装脚本固定 PyTorch 2.4.1 / torchvision 0.19.1 的 CUDA 12.1 wheel，并安装 `requirements-bc-a100.txt`，最后执行 `pip check`。PyTorch 组合取自[官方历史版本安装说明](https://pytorch.org/get-started/previous-versions/)，其余依赖从仓库环境约束整理。**依赖清单尚未在真实 Ubuntu 环境完成安装验证**，服务器上的安装与下一步运行预检才是验收；本地单元测试不能代替它们。

无桌面服务器需要 EGL/OpenGL 运行库；若镜像缺少这些库，由有权限的管理员安装：

```bash
sudo apt-get update
sudo apt-get install -y libegl1 libgl1 libglvnd0 libgles2 libglfw3 libglib2.0-0 ffmpeg
```

启动器设置 EGL 离屏渲染，运行 GPU 矩阵计算、资产加载、128×128 图像渲染和 5 步仿真检查，全部通过才进入训练。不会静默回退 CPU，也不需要 W&B 登录。首轮不安装 OpenVLA/TensorFlow 环境。

## 3. 先跑通，再获得可分析的结果

```bash
# 只打印将执行的命令，不读数据、不启动训练
python scripts/run_handoff_experiment.py --stage pilot --dry-run

# 管线检查：3 技能各 1 epoch，2 回合，单技能预算 20 步
python scripts/run_handoff_experiment.py --stage smoke

# 第一轮可分析实验：3 技能各 50 epochs，20 回合 × 3 个评估 seed
python scripts/run_handoff_experiment.py --stage pilot

# pilot 原始技能学会且日志正常之后，再运行全量
python scripts/run_handoff_experiment.py --stage full
```

每个命令依次完成准备、CUDA/EGL 预检、训练、评测和汇总。各步骤的标准输出和错误输出逐行实时显示到终端，同时即时写入对应 `.log`；阶段失败立即停止，错误日志保留。smoke 的低训练量和低步数专门检查管线，**成功率不能用于论文或判断方法效果**。pilot 与 full 默认每技能 400 步预算；三技能链共用 1200 步总预算，不是每阶段单独超时。

| 阶段 | 训练范围 | 评测范围 | 评估根 seed |
|---|---|---|---|
| smoke | 全局 ID 2、3、5 | 对应原始/CH1/CH2，以及 CH3-1 | 10000 |
| pilot | 全局 ID 2、3、5 | 同上，正常预算 | 10000、20000、30000 |
| full | 全部 44 个技能 | 全部原始/CH1/CH2，全部 10 条 CH3 链 | 10000、20000、30000 |

ID 保留原 benchmark 编号，不会把 2、3、5 重编号成 0、1、2。每阶段新建实验目录；pilot 不自动复用 smoke 模型，full 默认重新训练。训练采用原 BC 配置（batch size 32、原数据增强和单相机输入），保存最后 epoch 的 checkpoint，不按 CH 测试成绩选模型。50 epochs 是本轮起点，未承诺足够收敛，应结合原任务成功率及训练日志判断。

可以指定 `--gpu 1` 使用物理 GPU 1；进程内部仍使用 `cuda:0`。`--workers 4` 控制数据加载，内存压力较大时可降低。80GB 显存不代表主机内存必然足够：原数据加载器会缓存示范，full 启动会加载多个技能数据，本地未测出峰值内存和耗时，不给未经实测的完成时间。

默认只训练一个 seed，三个评估 seed **不等于三个独立训练 seed**。需要独立重复训练时：

```bash
python scripts/run_handoff_experiment.py --stage pilot --train-seed 20000
```

已有本流程训练的对应模型时，可以跳过训练。目录内需要 `task2_model.pth`、`task3_model.pth`、`task5_model.pth`；full 需要全部 44 个：

```bash
python scripts/run_handoff_experiment.py --stage pilot --model-dir /绝对路径/run_001
```

训练模型实际路径记录在 `pipeline.json` 的命令中，形式为 `experiments/boss_44/handoff_<运行ID>/BCTransformerPolicy_seed10000/run_001/`。只载入自己训练或可信来源的 checkpoint。

## 4. 如何读取与返回结果

每次执行建立 `results/handoff/<阶段_时间_随机后缀>/`：

| 文件 | 用途 |
|---|---|
| `pipeline.json`、各步骤 `.log` | 完整命令、参数、完成状态、错误与训练 loss |
| `runtime.json`、`installed-packages.txt`、`data_inventory.json` | 实际硬件/版本、渲染检查、示范清单 |
| `report.md`、`runs.csv` | 逐任务/逐 seed 成功率、阶段到达数、阶段成功数、耗时 |
| `oss.csv` | 同技能同权重的原始与 CH1/CH2 对比、百分点下降、RPD |
| `chain_reset_comparison.csv` | CH3 传统归位与取消归位的配对结果 |
| `eval_*/manifest.json` | checkpoint SHA256、关键代码哈希、版本、执行状态 |
| `eval_*/<任务>/episodes.jsonl` | 每回合 seed、初态索引、完成阶段、步数和交接事件 |
| `eval_*/<任务>/episode*.npz` / `.mp4` | 前两回合交接/终止快照、首回合视频 |

先发回运行目录内 `report.md`、三个 CSV、`pipeline.json`、`runtime.json` 和 `train.log`。发现特定任务异常后，再看该任务的 `episodes.jsonl`、视频及 NPZ；不必先传几 GB 模型。若运行失败，发回对应失败步骤的 `.log` 和 `pipeline.json`。

RPD 定义为 `(原始成功率 - 偏移成功率) / 原始成功率`，原始为 0 时写空值；百分点下降依然保留。前缀成功率以全部回合为分母，条件后继成功率以到达该阶段的回合数为分母，未到达写 `null`。聚合器只纳入完成运行，并核对权重哈希、评估 seed、回合数、步预算和初态顺序；缺少配对基线会报错。不同运行不要直接合并成“独立样本”来计算显著性。

## 5. 本轮能回答什么，以及还不能回答什么

1. **原始技能是否学会？** 原始任务成功率过低时，先检查数据、训练收敛和模型，不把后续下降解释为交接问题。
2. **谓词变化是否伴随性能下降？** CH1/CH2 与对应原技能用同一权重比较；场景初态不同，属于匹配比较，不是同一物理状态上的纯视觉因果干预。
3. **链式执行在哪一阶段失败？** 用阶段到达数、条件成功率和视频定位；后继样本受前驱成功筛选，不能单看条件率证明某方法改善。
4. **传统归位影响多大？** `original` 沿用原脚本对扁平状态 `[1:10]`、`[41:]` 的覆盖，其中后一段包含全部速度分量；`none` 取消这些覆盖。两者仍跨独立环境传递状态，尚不等于完整连续物理控制。

新诊断修复了 SequentialEnv 的 seed 覆写、reset 残留完成标记、技能切换后返回旧观测三个问题，并使用稳定的任务名称映射模型、显式初态索引和热身后的新观测。逐回合评测替代旧脚本 20 份并行模型，随机数消费方式与旧脚本不同，因此结果标注为**修正后的诊断协议**，不直接声称严格复现论文表格。

本轮未自动判定前驱成果是否被撤销，未建立纯视觉/前置条件/物理不兼容的因果分类，也未计算未经假设证明的“链成功率理论上界”。若结果确实显示有诊断价值的下降，再设计同一交接快照上的配对干预或恢复实验；目前不预先声称创新点成立。

## 6. 本地与服务器验收边界

本地以 stdlib/NumPy 替身环境测试状态切换、统计分母、非破坏性数据准备、命令构建及汇总配对，并检查 Python 语法和 CLI。当前 Windows 环境未安装完整 Torch/MuJoCo 栈，也没有本地示范、资产或 GPU 训练结果。服务器的依赖安装、CUDA/EGL 预检、smoke 和 pilot 是后续实际验收步骤。

```bash
python -m unittest discover -s tests -v
```
