#!/usr/bin/env python3
"""One-time installation using the owner's existing admin SSH connection."""
from pathlib import Path
import shutil
import subprocess
repo=Path('/srv/bd3pzh-blog')
nginx=Path('/etc/nginx/sites-available/bd3pzh.top')
deploy=Path('/usr/local/bin/deploy-blog')
for file in (nginx,deploy):
    backup=file.with_name(file.name+'.before-private-thoughts')
    if not backup.exists():shutil.copy2(file,backup)
# Run a full build before changing routing.
subprocess.run(['/usr/bin/python3',str(repo/'ops/build-private.py')],check=True)
s=nginx.read_text()
marker='    include /etc/nginx/snippets/jingkang-private.conf;'
if marker not in s:
    needle='    access_log /var/log/nginx/bd3pzh.top.access.log;'
    if s.count(needle)!=1:raise SystemExit('Unexpected Nginx configuration; stopped without editing it.')
    s=s.replace(needle,marker+'\n\n'+needle)
Path('/etc/nginx/snippets/jingkang-private.conf').write_text((repo/'ops/nginx-private.conf').read_text())
nginx.write_text(s)
r=subprocess.run(['nginx','-t'])
if r.returncode:
    shutil.copy2(nginx.with_name(nginx.name+'.before-private-thoughts'),nginx)
    raise SystemExit('Nginx validation failed; restored original configuration.')
s=deploy.read_text()
if 'ops/build-private.py' not in s:
    needle='log "Build Hugo site"'
    if s.count(needle)!=1:raise SystemExit('Unexpected deployment script; stopped.')
    s=s.replace(needle,'log "Check public content privacy"\npython3 ops/check-public-content.py\n\nlog "Build protected thoughts"\npython3 ops/build-private.py\n\n'+needle)
    s=s.replace('log "Deployment complete"','systemctl try-restart jingkang-private.service\n\nlog "Deployment complete"')
    deploy.write_text(s)
shutil.copy2(repo/'ops/jingkang-private.service','/etc/systemd/system/jingkang-private.service')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','jingkang-private.service'],check=True)
subprocess.run(['systemctl','reload','nginx'],check=True)
print('Private thoughts service installed and Nginx validated.')
