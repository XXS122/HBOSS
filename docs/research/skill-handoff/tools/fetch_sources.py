"""Archive public research sources and extract page-indexed text; no robot execution."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import urllib.request
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'sources'
PAPERS = {
    'P01': '2509.16053', 'P02': '2411.01284', 'P03': '2607.16506',
    'P04': '2608.16889', 'P05': '2607.06256', 'P06': '2602.09430',
    'P08': '2505.00527', 'P09': '2410.18907', 'P10': '2502.18015',
    'P11': '2410.13979', 'P12': '2409.16275', 'P13': '2508.19958',
    'P14': '2512.18368', 'P15': '2608.14822', 'P16': '2410.24185',
    'P17': '2402.07412', 'P18': '2603.08383', 'P19': '2603.08057',
    'P20': '2411.16959',
}

def read_url(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'BOSS-literature-review/1.0'})
    with urllib.request.urlopen(req, timeout=55) as response:
        return response.read()

def fetch_one(item):
    key, identifier = item
    url = 'https://arxiv.org/abs/' + identifier
    record = {'id': key, 'arxiv_id': identifier, 'metadata_url': url, 'retrieved': '2026-09-11'}
    try:
        meta_path = SOURCES / (key + '-metadata.html')
        if not meta_path.exists():
            meta_path.write_bytes(read_url(url))
        if int(key[1:]) <= 10 or key in {'P11', 'P12', 'P13', 'P15', 'P17', 'P20'}:
            pdf_url = 'https://arxiv.org/pdf/' + identifier
            path = SOURCES / (key + '.pdf')
            data = path.read_bytes() if path.exists() else read_url(pdf_url)
            if not data.startswith(b'%PDF'):
                raise ValueError('Response was not a PDF')
            path.write_bytes(data)
            reader = PdfReader(path)
            text = '\n\n'.join(f'=== PDF PAGE {i + 1} ===\n{p.extract_text()}' for i, p in enumerate(reader.pages))
            (SOURCES / (key + '.txt')).write_text(text, encoding='utf-8')
            record.update(pdf_url=pdf_url, pages=len(reader.pages), sha256=hashlib.sha256(data).hexdigest())
        record['status'] = 'ok'
    except Exception as exc:
        record.update(status='error', error=str(exc))
    return record

def main():
    SOURCES.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch_one, PAPERS.items()))
    url = 'https://proceedings.neurips.cc/paper_files/paper/2024/file/ca92ff06d973ece92cecc561757d500e-Paper-Conference.pdf'
    try:
        path = SOURCES / 'P07.pdf'
        data = path.read_bytes() if path.exists() else read_url(url)
        path.write_bytes(data)
        reader = PdfReader(path)
        (SOURCES / 'P07.txt').write_text('\n\n'.join(f'=== PDF PAGE {i + 1} ===\n{p.extract_text()}' for i, p in enumerate(reader.pages)), encoding='utf-8')
        records.append({'id': 'P07', 'pdf_url': url, 'pages': len(reader.pages), 'sha256': hashlib.sha256(data).hexdigest(), 'status': 'ok', 'retrieved': '2026-09-11'})
    except Exception as exc:
        records.append({'id': 'P07', 'status': 'error', 'error': str(exc)})
    for key, url in {
        'BOSS-project': 'https://boss-benchmark.github.io/',
        'BOSS-metadata': 'https://arxiv.org/abs/2502.15679',
        'X01-ees-metadata': 'https://arxiv.org/abs/2402.15025',
        'X02-asc-metadata': 'https://arxiv.org/abs/2304.00410',
        'X04-caiac-metadata': 'https://arxiv.org/abs/2405.18917',
        'X05-afp-metadata': 'https://arxiv.org/abs/2607.10655',
        'X06-interpretability-metadata': 'https://arxiv.org/abs/2605.00321',
        'X07-inverse-metadata': 'https://arxiv.org/abs/2606.05248',
        'X08-jit-metadata': 'https://arxiv.org/abs/2607.16247',
        'X09-tstar-metadata': 'https://arxiv.org/abs/2111.07999',
        'X10-sequential-dexterity-metadata': 'https://arxiv.org/abs/2309.00987',
    }.items():
        path = SOURCES / (key + '.html')
        if not path.exists():
            try:
                path.write_bytes(read_url(url))
            except Exception as exc:
                print(json.dumps({'id': key, 'error': str(exc)}))
    (SOURCES / 'manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    for record in records:
        print(json.dumps(record, ensure_ascii=False))

if __name__ == '__main__':
    main()
