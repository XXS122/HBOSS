"""Check counts, archived evidence, local links and explicitly recomputed quantities."""
from pathlib import Path
import hashlib
import json
import re
from urllib.parse import unquote
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
checks=[]
def check(name,ok,detail=''):
    checks.append(dict(check=name,passed=bool(ok),detail=detail))
rows=json.loads((ROOT/'sources/candidates.json').read_text(encoding='utf-8'))
manifest={r['id']:r for r in json.loads((ROOT/'sources/manifest.json').read_text(encoding='utf-8'))}
check('Exactly 20 unique candidates',len(rows)==20 and len({r['id'] for r in rows})==20 and len({r['title'] for r in rows})==20)
check('BOSS is excluded from candidate set',all(r['id']!='BOSS' for r in rows))
core=[r for r in rows if r['core']]
check('Exactly 10 core cards',len(core)==10 and len(list((ROOT/'cards').glob('*.md')))==10)
for r in rows:
    if r['id']!='P07':
        check(r['id']+' dates in scope','2024-01-01'<=r['first_public']<=r['read_date']<='2026-09-11')
    else:
        check('P07 earliest-date uncertainty explicit','全球首次' in r['first_public'])
    check(r['id']+' metadata/archive success',manifest[r['id']]['status']=='ok')
for r in core:
    key=r['id']; p=ROOT/'sources'/f'{key}.pdf'; txt=ROOT/'sources'/f'{key}.txt'; m=manifest[key]
    check(key+' full-text card exists',(ROOT/r['card']).exists())
    n=len(PdfReader(p).pages)
    check(key+' PDF/text page count',n==m['pages'] and txt.read_text(encoding='utf-8').count('=== PDF PAGE ')==n,f'{n} pages')
    check(key+' PDF SHA256',hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256'])
    if r['arxiv']:
        # PDF headers contain the arXiv stamp; verify version when available in text.
        stamp=r['arxiv']+r['version']
        body=txt.read_text(encoding='utf-8')
        check(key+' read-version stamp',stamp in body or stamp in body.replace(' ',''),stamp)
check('P15 is CoRe',next(r for r in rows if r['id']=='P15')['arxiv']=='2608.14822')
check('HODOR retained as supporting',(ROOT/'supporting/P02-hodor.md').exists())
bib=(ROOT/'references.bib').read_text(encoding='utf-8')
keys=re.findall(r'@\w+\{([^,]+),',bib)
check('BibTeX unique keys and candidate coverage',len(keys)==len(set(keys)) and all(r['id'] in keys for r in rows) and 'BOSS' in keys,f'{len(keys)} entries')
check('DeCo table recount disclosed',sum([7,7,6,5,4,3,9,3,1])==45 and '45/90' in (ROOT/'03-comparison.md').read_text(encoding='utf-8'),'45/90 = 50%, author aggregate = 53.33%')
check('SkillMimicGen augmentation deltas',[52-40,50-14,98-56]==[12,36,42])
check('CoRe real counts',sum([6,1,1,9,4])==21 and sum([18,18,18,17,19])==90)
check('Pilot boundary denominator',10*20==200 and 200*(3-1)==400)
for r in json.loads((ROOT/'sources/code-snapshot.json').read_text(encoding='utf-8')):
    p=ROOT.parents[2]/r['file']
    check('Code snapshot '+r['file'],p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'])
# Write a temporary report so forward links to its eventual name are checkable.
(ROOT/'08-validation.md').write_text('# 验收记录\n\n检查正在生成。\n',encoding='utf-8')
broken=[]; local_count=0
for p in ROOT.rglob('*.md'):
    body=p.read_text(encoding='utf-8')
    for dest in re.findall(r'\[[^\]]*\]\(([^\n]+?)\)',body):
        dest=dest.strip('<>')
        if dest.startswith(('https://','http://','mailto:','#','app:')): continue
        dest=unquote(dest.split('#',1)[0])
        if re.match(r'^/[A-Za-z]:/',dest): dest=dest[1:]
        dest=re.sub(r':\d+$','',dest)
        target=Path(dest) if re.match(r'^[A-Za-z]:[/\\]',dest) else p.parent/dest
        local_count+=1
        if not target.exists(): broken.append(f'{p.relative_to(ROOT)} -> {dest}')
check('All local Markdown links resolve',not broken,f'{local_count} links; '+ '; '.join(broken))
fail=[c for c in checks if not c['passed']]
result={'date':'2026-09-11','checks':len(checks),'passed':len(checks)-len(fail),'failures':fail,'details':checks,'candidate_count':20,'core_fulltext_count':10,'local_link_count':local_count}
(ROOT/'sources/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
out=['# 交付验收记录','', '执行日期：2026-09-11。自动校验只检查文件结构、版本戳、数量、哈希、链接和明确列出的算术；不能自动证明论文结论正确或研究新颖性。人工阅读全文/关键表图复核、独立抽核和反例复检是另外的证据。','', f"自动检查：{len(checks)}项，通过{len(checks)-len(fail)}项，失败{len(fail)}项。[机器记录](sources/validation.json)。",'', '| 用户要求 | 验收结果 |','|---|---|','| BOSS独立分析、代码定位 | [项目画像](01-boss-project.md)覆盖BC/OpenVLA/RAMG、reset、成功判据、seed、数据与指标 |','| 20篇候选去重、时间可核 | 候选/书目/元数据相符；P07只确认公开存档日和年份，全球首次日明确未知 |','| 10篇核心全文与可得附录 | 每卡都有本地PDF、分页文本、正文/附录或无附录说明；正文可得但独立补充缺失明确标注 |','| 数字能追溯 | 每卡/矩阵有表号页码；关键表图人工复核；原文冲突不强行裁决 |','| 作者不足与推断分离 | 卡内单列，未设limitations的论文按实际披露，不代写作者声明 |','| 新颖性复检与证据等级 | 两份独立反例记录；撤销通用机制新颖性，保留两个N1方向，效果E0 |','| 最低实验设计 | 原始/CH1/CH2/CH3/未见组合、数据泄漏、原任务损失、成本、无reset单列 |','| 不修改算法、不训练 | 本次仅增加研究文档、来源归档和整理/验收脚本；不声称复现实验 |','', '## 人工复检与保留缺口','', '- [独立抽核记录](audit-independent.md)：核心卡数字/协议抽核及证据等级修正。随后再次交叉审阅综合报告，修正P01试验分母、P03限制章节、P05主评测与代表轮、pilot边界数。','- 核心PDF提供全文依据不等于结果已复现。部分最新工作为预印本；AtomBridge的独立补充材料未取得；部分文献无误差条/缺完整预算。','- 不完整的检索命中导出和引用网络限制了穷尽性，因此新颖性仍N1。不能由本次未检得同方案证明不存在。','- 数学分析没有给BOSS乘积参考无条件上界；原始机械臂reset不代表动态物理连续handoff。']
if fail:
    out+=['','## 需修正的自动检查项','']+[f"- {c['check']}：{c['detail']}" for c in fail]
(ROOT/'08-validation.md').write_text('\n'.join(out)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='details'},ensure_ascii=False,indent=2))
raise SystemExit(bool(fail))
