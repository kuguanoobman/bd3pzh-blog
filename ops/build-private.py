#!/usr/bin/env python3
"""Decrypt repository envelopes outside the checkout and build protected Hugo pages."""
import argparse
import base64
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

parser=argparse.ArgumentParser()
parser.add_argument('--repo', default='/srv/bd3pzh-blog')
parser.add_argument('--key', default='/etc/jingkang-blog/private-posts.pem')
parser.add_argument('--destination', default='/var/lib/jingkang-blog/site')
args=parser.parse_args()
repo=Path(args.repo)
key=serialization.load_pem_private_key(Path(args.key).read_bytes(),password=None)
with tempfile.TemporaryDirectory(prefix='jingkang-private-',dir='/var/lib/jingkang-blog') as staging:
    work=Path(staging); content=work/'content'; thoughts=content/'thoughts'; thoughts.mkdir(parents=True)
    (thoughts/'_index.md').write_text('---\ntitle: 个人想法\nlayout: thoughts-index\n---\n')
    for envelope in sorted((repo/'private-posts').glob('*.json')):
        data=json.loads(envelope.read_text())
        if data['version'] != 1: raise ValueError('Unsupported encrypted format')
        aes=key.decrypt(base64.b64decode(data['key']),padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
        post=json.loads(AESGCM(aes).decrypt(base64.b64decode(data['iv']),base64.b64decode(data['data']),None))
        if not re.fullmatch('[a-z0-9][a-z0-9-]{0,79}',post['id']):raise ValueError('Invalid post ID')
        if envelope.stem!=post['id']:raise ValueError('Post ID mismatch')
        metadata={'title':post['title'],'date':post['date'],'layout':'private-entry','url':'/thoughts/'+post['id']+'/'}
        text='---\n'+'\n'.join(k+': '+json.dumps(v,ensure_ascii=False) for k,v in metadata.items())+'\n---\n\n'+post['body']
        (thoughts/(post['id']+'.md')).write_text(text)
    output=work/'output'
    subprocess.run(['/usr/local/bin/hugo','--source',str(repo),'--contentDir',str(content),'--destination',str(output),'--minify','--baseURL','https://bd3pzh.top/','--disableKinds','RSS,sitemap,robotsTXT'],check=True)
    dest=Path(args.destination)
    # Only the authenticated thoughts subtree is retained, never copied to the public webroot.
    replacement=dest.parent/'site-new'
    if replacement.exists():shutil.rmtree(replacement)
    replacement.mkdir(mode=0o755)
    shutil.copytree(output/'thoughts',replacement/'thoughts')
    old=dest.parent/'site-old'
    if old.exists():shutil.rmtree(old)
    if dest.exists():dest.rename(old)
    replacement.rename(dest)
    if old.exists():shutil.rmtree(old)
