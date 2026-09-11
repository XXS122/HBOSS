# 本地验证记录

日期：2026-09-11。环境：Windows，Codex 附带 Python，stdlib/NumPy。没有运行 Torch 训练、MuJoCo 仿真或服务器安装。

| 检查 | 结果 | 证据范围 |
|---|---|---|
| `python -m unittest discover -s tests -v` | 17 tests，OK，exit 0 | 真实类方法加替身环境验证 seed/reset/切换观测；统计边界；非破坏性文件准备；命令构建；汇总文件配对和错误拒绝 |
| `python -m py_compile`（9 个新增或修改的 Python 业务文件） | exit 0 | 仅语法，不执行重依赖导入 |
| `python scripts/run_handoff_experiment.py --stage pilot --dry-run` | exit 0 | 生成准备、预检、训练、6 次评估及汇总命令；三技能全局 ID 和模型路径一致 |
| `python -m libero.lifelong.diagnose_handoff --help` | exit 0 | CLI 可在不加载 Torch/MuJoCo 的情况下显示参数 |
| 独立代码审查 | 未发现确认缺陷 | 静态审查训练/评测接口、Hydra 路径、汇总配对、GPU 编号设置和安装脚本；不代替服务器测试 |

最初三个 SequentialEnv 回归测试在旧实现上分别复现 seed 传 None、reset 保留完成标记、交接返回前一环境观测的问题；修复后通过。新增汇总测试使用人工构造的小型结果文件，验证零基线 RPD 留空、未到达阶段保留 null、失败运行排除，以及不同 checkpoint 不被配对。这些测试数据不是机器人实验结果。

待服务器执行：安装固定依赖与 pip check、真实 CUDA 运算、assets/EGL 渲染、HDF5 检查、smoke、pilot。尚无成功率、资源峰值或训练耗时实测；没有声称复现 BOSS。
