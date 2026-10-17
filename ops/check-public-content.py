#!/usr/bin/env python3
"""Reject private-category source before committing or publishing public content."""
from pathlib import Path
import re
import subprocess
import sys

if '--staged' in sys.argv:
    names=subprocess.check_output(['git','diff','--cached','--name-only','--diff-filter=ACMR','-z']).decode().split('\0')
    pages=[]
    for name in filter(None,names):
        if name.startswith('.private-content/'):
            raise SystemExit('拒绝提交私密原稿：请先加密。')
        if name.startswith('content/') and name.endswith('.md'):
            pages.append((Path(name),subprocess.check_output(['git','show',':'+name]).decode()))
else:
    pages=[(p,p.read_text()) for p in Path('content').rglob('*.md')]
for page,text in pages:
    if 'categories' in page.parts and page.name == '_index.md':
        continue
    match=re.match(r'^(---|\+\+\+)\s*\n([\s\S]*?)\n\1',text)
    if match and '个人想法' in match[2]:
        raise SystemExit(f'拒绝公开发布 {page}：个人想法文章需放在 .private-content/，使用加密脚本生成密文。')
print('Public content privacy check passed.')
