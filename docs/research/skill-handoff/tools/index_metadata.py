"""Index archived publication metadata; bibliography uses the actually read version."""
from html.parser import HTMLParser
from html import unescape
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]

class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'meta' and d.get('name', '').startswith('citation_'):
            self.values.setdefault(d['name'], []).append(d.get('content', ''))

rows = []
for path in sorted((ROOT / 'sources').glob('P*-metadata.html')):
    p = MetaParser()
    html = path.read_text(encoding='utf-8')
    p.feed(html)
    history = re.search(r'<div class="submission-history">(.*?)</div>', html, re.S)
    row = {'id': path.name.split('-')[0], **p.values,
           'history': unescape(re.sub(r'<[^>]+>', ' ', history.group(1))).strip() if history else ''}
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))
(ROOT / 'sources' / 'metadata.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
