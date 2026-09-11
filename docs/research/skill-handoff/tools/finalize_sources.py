"""Finalize source index and supplementary bibliography; only writes research artifacts."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import re
import runpy
import shutil
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'tools/build_registry.py'),run_name='__main__')
class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.m={}
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='meta' and d.get('name','').startswith('citation_'):
            self.m.setdefault(d['name'],[]).append(d.get('content',''))

boss=Path('C:/Users/13968/Desktop/Boss.pdf')
shutil.copyfile(boss,ROOT/'sources/BOSS.pdf')
reader=PdfReader(boss)
(ROOT/'sources/BOSS.txt').write_text('\n\n'.join(f'=== PDF PAGE {i+1} ===\n{p.extract_text()}' for i,p in enumerate(reader.pages)),encoding='utf-8')
extra=[]
for path in sorted((ROOT/'sources').glob('X*-metadata.html')):
    p=Parser(); raw=path.read_text(encoding='utf-8'); p.feed(raw)
    if 'citation_arxiv_id' not in p.m: continue
    m=p.m; versions=re.findall(r'\[v(\d+)\]',raw)
    extra.append(dict(id=path.name.split('-')[0],title=m['citation_title'][0],authors=m['citation_author'],first=m['citation_date'][0].replace('/','-'),latest=m['citation_online_date'][0].replace('/','-'),arxiv=m['citation_arxiv_id'][0],version='v'+versions[-1],file=path.name))
bib=(ROOT/'references.bib').read_text(encoding='utf-8')
bib=bib.replace('@misc{BOSS,','@misc{BOSS,\n  author = {Yang, Yue and Zhao, Linfeng and Ding, Mingyu and Bertasius, Gedas and Szafir, Daniel},')
for r in extra:
    fields={'title':'{'+r['title']+'}','author':' and '.join(r['authors']),'year':r['first'][:4],'eprint':r['arxiv'],'archivePrefix':'arXiv','url':'https://arxiv.org/abs/'+r['arxiv'],'note':f"Supplementary/background source, {r['version']} ({r['latest']}); accessed 2026-09-11; not part of 20 candidates"}
    bib+='\n@misc{'+r['id']+',\n'+',\n'.join('  '+k+' = {'+v+'}' for k,v in fields.items())+'\n}\n'
(ROOT/'references.bib').write_text(bib,encoding='utf-8')
rows=json.loads((ROOT/'sources/candidates.json').read_text(encoding='utf-8'))
manifest={r['id']:r for r in json.loads((ROOT/'sources/manifest.json').read_text(encoding='utf-8'))}
out=['# 来源索引、版本与归档','', '检索日2026-09-11。候选/核心编号以[候选表](02-candidates.md)为准；所有论文结果的准确页/节见证据卡。PDF页码按阅读器从1计数，不一定等于页脚印刷页码。','', '## 1. BOSS与本地代码','', '用户文件复制为[BOSS.pdf](sources/BOSS.pdf)，10页v1；[分页文本](sources/BOSS.txt)。用户文档作为研究证据，未把其中的行动性文字当作新用户指令。','', '- [arXiv版本记录](https://arxiv.org/abs/2502.15679)；[作者项目页](https://boss-benchmark.github.io/)；[机构正式发表记录](https://experts.colorado.edu/display/pubid_391802)。','- RA-L DOI：[10.1109/LRA.2025.3585390](https://doi.org/10.1109/LRA.2025.3585390)。本地v1、后续正式发表和网站补充不混为一个版本。','- 当前代码定位见[项目画像](01-boss-project.md)；所引文件哈希见[code-snapshot.json](sources/code-snapshot.json)。它是静态取证快照，不是已执行环境或Git提交。','', '## 2. 二十篇候选的原文入口与阅读深度','', '| ID | 官方版本/全文入口 | 本地归档 | 阅读类别 |','|---|---|---|---|']
for r in rows:
    key=r['id']; m=manifest[key]
    fixed='https://arxiv.org/html/'+r['arxiv']+r['version'] if r['arxiv'] else r['url']
    links=f"[元数据]({r['url']})；[所查版本]({fixed})"
    local=f"[PDF](sources/{key}.pdf) / [文本](sources/{key}.txt)，{m['pages']}页" if 'pages' in m else f"[元数据](sources/{key}-metadata.html)；未本地归档全文"
    kind='核心全文＋可获附录' if r['core'] else ('支持性全文卡' if key=='P02' else ('定向全文复检' if key in ['P18','P20'] else '候选筛选，非完成精读'))
    out.append(f'| {key} | {links} | {local} | {kind} |')
out+=['', 'P18通过官方在线v2全文完成定向复检，未本地归档PDF。P11/P12/P13/P17下载全文不代表完成统一精读。P06正文提及的独立supplement未取得；其主文9页可核查，不声称读取不存在的附录。','', '## 3. 出版状态的独立核实入口','', '| 工作 | 依据 |','|---|---|','| P01 | [作者项目页](https://computationalrobotics.seas.harvard.edu/SkillComposition/)；ICRA 2026 accepted |','| P02 | [PMLR官方](https://proceedings.mlr.press/v270/qian25b.html)，CoRL2024，PMLR2025 |','| P07 | [NeurIPS正式记录](https://proceedings.neurips.cc/paper_files/paper/2024/hash/ca92ff06d973ece92cecc561757d500e-Abstract-Conference.html)；[作者机构库日期](https://orca.cardiff.ac.uk/id/eprint/172654/) |','| P08 | [作者项目页](https://deco226.github.io/)，PDF首页accepted日期 |','| P09 | [PMLR官方](https://proceedings.mlr.press/v270/garrett25a.html) |','| P10 | [作者项目页](https://sites.google.com/view/skill-rrt)，v3首页 |','| P11 | [MERL正式发表记录](https://www.merl.com/publications/TR2025-091)，IROS2025 DOI 10.1109/IROS60139.2025.11245856 |','| P12 | [PMLR官方](https://proceedings.mlr.press/v270/mishra25a.html) |','| P13 / P14 | [Long-VLA作者页](https://long-vla.github.io/) / [AtomSkill作者页](https://atom-skill.github.io/) |','| P16 | [官方仓库README](https://github.com/NVlabs/dexmimicgen/blob/main/README.md) |','| P20 | [作者页](https://rocoda.github.io/) / [IEEE记录](https://ieeexplore.ieee.org/document/11128694/) |','', 'P03的IROS2026接收状态来自arXiv作者comments，不冒充已独立取得正式会议终版。P04/P06/P15/P18/P19按预印本处理；P05只标SemRob workshop，不标RSS主会。','', '## 4. 二轮反例及更早背景（不计候选）','', '| ID | 题名/官方链接 | 首发；所查版本 |','|---|---|---|']
for r in extra:
    out.append(f"| {r['id']} | [{r['title']}](https://arxiv.org/abs/{r['arxiv']}) | {r['first']}；{r['version']} {r['latest']} |")
out+=['', '阅读深度和反例位置见两份gap复检文件。AGRA/CAGE-SGG及经典因果链接等其余外围来源的准确入口保留在复检日志中；不将它们全部声称为全文精读。','', '## 5. 本地证据与重建','', '- [manifest.json](sources/manifest.json)：20候选的下载状态、PDF页数与SHA256；[metadata.json](sources/metadata.json)：19篇arXiv的作者/日期/版本原始字段；SCaR另用正式库。','- [candidates.json](sources/candidates.json)：筛选决定的机器可读记录；[source-checksums.json](sources/source-checksums.json)：全部归档PDF/HTML/文本的哈希。','- [BibTeX](references.bib)：20候选＋BOSS＋已归档补充/背景条目；arXiv条目用首次年、note记录读本版本和发表状态，避免同一工作重复计算。','- `tools/fetch_sources.py`下载公共资料并分页提取；`index_metadata.py`整理元数据；`build_registry.py`生成候选和主书目；`finalize_sources.py`补来源索引；`validate_package.py`作文件/数量/哈希/链接检查。抓取脚本默认缓存本次快照；未来要更新版本，应显式另存归档，不能混用新旧数字。','- 关键表图另存PNG；它们用于核对文本提取列序、计分定义和图上数字，不表示复现实验。','', '本包没有完整搜索服务原始命中导出，也没有所有来源的完整引用网络。记录足以回查所引证据，但不宣称穷尽文献。']
(ROOT/'07-source-index.md').write_text('\n'.join(out)+'\n',encoding='utf-8')
code_paths=['README.md','libero/libero/envs/env_wrapper.py','libero/lifelong/eval_skill_chain.py','libero/lifelong/eval_skills_affected_by_oss.py','libero/lifelong/train_skills.py','libero/configs/data/default.yaml','libero/configs/eval/default.yaml','openvla/experiments/robot/libero/eval_openvla_ch3.py','RAMG/DA_demos_generation.py','scripts/DemoProcessor.py','scripts/form_boss_44_dataset.py','libero/libero/benchmark/__init__.py','libero/mappings/ch1.json','libero/mappings/ch2_2_modifications.json','libero/mappings/ch2_3_modifications.json']
workspace=ROOT.parents[2]
snapshot=[]
for rel in code_paths:
    p=workspace/rel
    snapshot.append({'file':rel,'exists':p.exists(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None})
(ROOT/'sources/code-snapshot.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
checks=[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((ROOT/'sources').iterdir()) if p.suffix in ['.pdf','.html','.txt','.png']]
(ROOT/'sources/source-checksums.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print('Source index complete;',len(extra),'supplementary bibliography entries;',len(checks),'archived sources.')
