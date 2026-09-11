"""Build review tables from archived primary metadata plus explicit screening decisions."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
META = {r['id']: r for r in json.loads((ROOT/'sources/metadata.json').read_text(encoding='utf-8'))}
# Status is verified publication information, not inferred from an arXiv year.
DECISIONS = [
('P01','Compose by Focus','ICRA 2026 accepted（作者页）','cards/P01-compose-focus.md','直接研究组合场景视觉偏移；与BOSS问题最贴近的表示基线。'),
('P02','HODOR','CoRL 2024','supporting/P02-hodor.md','保留局部/全局视觉的直接近邻；全文支持性阅读，链实验缺少定量统计，核心名额让给CoRe。'),
('P03','Foresight Residual RL','IROS 2026 accepted（arXiv作者声明）','cards/P03-foresight.md','后继成功预测直接优化前驱终态，有同骨干残差消融。'),
('P04','BATON','公开预印本','cards/P04-baton.md','入口契约、边界修复和剩余计划约束直接处理handoff。'),
('P05','Semantic Handoff','RSS 2026 SemRob Workshop','cards/P05-semantic-handoff.md','直接诊断clean/chained落差；小规模、判定器不完全匹配须明示。'),
('P06','AtomBridge','公开预印本','cards/P06-atombridge.md','完成检测、机器人状态校准及技能检索，可检查仿真/真机衔接。'),
('P07','SCaR','NeurIPS 2024','cards/P07-scar.md','双向终止—启动分布对齐的必要最近邻；特权状态限制另列。'),
('P08','DeCo','IEEE RA-L 2026','cards/P08-deco.md','3D视觉技能起点桥接；有桥接数量消融及未见组合实验。'),
('P09','SkillMimicGen','CoRL 2024；PMLR 270（2025）','cards/P09-skillmimicgen.md','数据生成、HSP启动条件与初态增强共同作用，有去增强消融。'),
('P10','SPIN','CoRL 2025','cards/P10-spin.md','低物体扰动connector与鲁棒重放，是成果保持泛化批评的反例。'),
('P11','RecoveryChaining','IROS 2025（MERL正式发表记录）',None,'局部失败恢复直接相关；候选全文可得，机制覆盖由SCaR/DeCo/SPIN/CoRe代表，不列完成精读。'),
('P12','Generative Factor Chaining','CoRL 2024',None,'联合因子约束协调技能参数，偏特权几何规划；全文可得，未列核心精读。'),
('P13','Long-VLA','CoRL 2025（作者页）',None,'阶段相关视觉训练和长任务数据是补充近邻；未单独隔离技能边界对齐。'),
('P14','AtomSkill','IROS 2026 accepted（作者页）',None,'语义原子技能/关键姿态连接相关；只作元数据与方法摘要筛选，未完成全文审计。'),
('P15','CoRe','公开预印本','cards/P15-core.md','第二轮发现的强直接反例：累计成果保护、最小反事实恢复与动作块交接；提升至核心。'),
('P16','DexMimicGen','ICRA 2025（官方仓库）',None,'双臂同步与交接示范生成；本题优先单臂串联及观测偏移，SkillMimicGen代表数据主线。'),
('P17','TDRP','2024公开预印本；后续发表状态未核实',None,'BOSS所引过渡距离奖励近邻；在总时间窗内但早于优先24个月，偏目标距离而非组合视觉。'),
('P18','MoMaStage','公开预印本',None,'v2累积技能状态和保留已完成任务的恢复很重要；定向全文复检，非十篇统一卡。'),
('P19','See and Switch','公开预印本',None,'视觉分支/异常检测相关，但用户门控离线决策窗口区别于自主handoff；只作候选。'),
('P20','RoCoDA','ICRA 2025',None,'阶段因果增强与成功过滤是创新反例；全文定向复检，非十篇统一卡。'),
]
rows=[]
for key, short, status, card, reason in DECISIONS:
    if key=='P07':
        row=dict(id=key,title='SCaR: Refining Skill Chaining for Long-Horizon Robotic Manipulation via Dual Regularization',authors=['Chen, Zixuan','Ji, Ze','Huo, Jing','Gao, Yang'],first_public='2024-10-07（已核实机构存档；全球首次日未确认）',version='NeurIPS 2024正式版',read_date='2024正式版',url='https://proceedings.neurips.cc/paper_files/paper/2024/hash/ca92ff06d973ece92cecc561757d500e-Abstract-Conference.html',arxiv=None)
    else:
        m=META[key]
        versions=re.findall(r'\[v(\d+)\]',m['history'])
        row=dict(id=key,title=m['citation_title'][0],authors=m['citation_author'],first_public=m['citation_date'][0].replace('/','-'),version='v'+versions[-1],read_date=m['citation_online_date'][0].replace('/','-'),url='https://arxiv.org/abs/'+m['citation_arxiv_id'][0],arxiv=m['citation_arxiv_id'][0])
    row.update(short=short,status=status,card=card,core=bool(card and card.startswith('cards/')),reason=reason)
    rows.append(row)
(ROOT/'sources/candidates.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
out=['# 20篇候选及筛选决定','', '检索截止2026-09-11；首次公开窗口2024-01-01至截止日，优先2024-09-11之后。BOSS单列，不计入20篇。不同版本和旧标题合并；P07只确认2024年正式发表及10月7日机构存档，未虚构全球首次日期。所列“所查版本”并不等于已完成全文精读，阅读深度见最后一列。','', '**最终核心10篇：P01、P03、P04、P05、P06、P07、P08、P09、P10、P15。** HODOR有额外支持性全文卡；RoCoDA/MoMaStage用于定向复检。这些额外阅读不重复计入10篇。第二轮发现CoRe后替换弱相关DUSDi候选，并取代HODOR的核心名额；这体现按证据更新筛选，而非固定清单。','', '| ID / 全名（官方来源） | 首次公开 | 所查版本 / 日期 | 发表状态 | 选择及阅读深度 |','|---|---|---|---|---|']
for r in rows:
    title=r['title'].replace('$','').replace('\\texttt{SPIN}','SPIN').replace('\\texttt{Skill-RRT}','Skill-RRT')
    detail=('**核心全文**；' if r['core'] else '候选；')+r['reason']
    if r['card']: detail+=' [证据卡]('+r['card']+')'
    out.append(f"| {r['id']} [{title}]({r['url']}) | {r['first_public']} | {r['version']} / {r['read_date']} | {r['status']} | {detail} |")
out += ['', '## 筛选规则与不纳入核心的含义','', '按直接衔接机制、证据充分度、BOSS视觉适配、时间接近度作定性排序，不用引文量评分。全文可取得只是必要条件；不将下载但未读透的PDF算作精读。核心同时覆盖前驱优化、显式桥接、训练数据和视觉表示，保留两篇诊断/系统工作用于检验接口条件。此选择是透明的主题取样，不能证明它们是唯一或绝对排名前十。','', 'P19采用v2（2026-06-29）：约900次rollout、8名新手、3任务；分支准确率与决策状态的异常检测不能写成自主整链成功率。旧版576次等数字不混入此版本。P10旧题“From planning to policy…”与SPIN去重；P09 SkillGen为SkillMimicGen别称。P16初始workshop与后来的ICRA正式记录分开，不按旧页页眉定当前状态。','', '初检排除表、检索式及来源覆盖局限见[检索日志](06-search-log.md)。日期/作者来自归档元数据，发表状态的额外依据见[来源索引](07-source-index.md)。']
(ROOT/'02-candidates.md').write_text('\n'.join(out)+'\n',encoding='utf-8')
bib=['% BOSS Skill Handoff review; retrieved 2026-09-11. arXiv entries retain first-public year and read-version notes.']
for r in rows:
    title=r['title'].replace('$','').replace('\\texttt{SPIN}','SPIN').replace('\\texttt{Skill-RRT}','Skill-RRT')
    fields={'title':'{'+title+'}','author':' and '.join(r['authors']),'year':r['first_public'][:4], 'url':r['url'],'note':f"Read {r['version']}, {r['read_date']}; {r['status']}; accessed 2026-09-11"}
    if r['arxiv']: fields.update(eprint=r['arxiv'],archivePrefix='arXiv')
    else: fields.update(booktitle='Advances in Neural Information Processing Systems',volume='37',pages='111679--111714')
    typ='misc' if r['arxiv'] else 'inproceedings'
    bib.append('@'+typ+'{'+r['id']+',\n'+',\n'.join('  '+k+' = {'+v+'}' for k,v in fields.items())+'\n}')
# Baseline is excluded from the candidate count.
bib.append('@misc{BOSS,\n  title = {{BOSS: Benchmark for Observation Space Shift in Long-Horizon Task}},\n  year = {2025},\n  eprint = {2502.15679},\n  archivePrefix = {arXiv},\n  url = {https://arxiv.org/abs/2502.15679},\n  note = {Local supplied v1 read; later RA-L 10(9), 8882--8889, DOI 10.1109/LRA.2025.3585390}\n}')
(ROOT/'references.bib').write_text('\n\n'.join(bib)+'\n',encoding='utf-8')
print('Built 20 candidates,',sum(r['core'] for r in rows),'core cards, and bibliography.')
