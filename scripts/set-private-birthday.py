#!/usr/bin/env python3
"""Set the private category password through an existing authenticated SSH master."""
import getpass
import hashlib
import json
import secrets
import subprocess
from pathlib import Path

if not Path("/tmp/jingkang-blog-vps.sock").exists():
    raise SystemExit("管理员 SSH 连接尚未建立，请先登录并保持终端窗口打开。")

birthday = getpass.getpass('请输入农历腊月生日的日数（1～30，不含年月，输入不显示）：')
if not birthday.isascii() or not birthday.isdigit() or not 1 <= int(birthday) <= 30:
    raise SystemExit('请输入 1～30 的日数。')
birthday = str(int(birthday))
confirmation = getpass.getpass('请再次输入日数：')
if not confirmation.isascii() or not confirmation.isdigit() or str(int(confirmation)) != birthday:
    raise SystemExit('两次输入不一致，未修改。')
salt = secrets.token_hex(32)
config = {'salt': salt, 'iterations': 600000,
          'digest': hashlib.pbkdf2_hmac('sha256', birthday.encode(), bytes.fromhex(salt), 600000).hex()}
remote = "umask 077; mkdir -p /etc/jingkang-blog/auth; chown root:www-data /etc/jingkang-blog/auth; chmod 750 /etc/jingkang-blog/auth; cat > /etc/jingkang-blog/auth/birthday.json.new; chown root:www-data /etc/jingkang-blog/auth/birthday.json.new; chmod 640 /etc/jingkang-blog/auth/birthday.json.new; mv /etc/jingkang-blog/auth/birthday.json.new /etc/jingkang-blog/auth/birthday.json; openssl rand -out /etc/jingkang-blog/auth/session.key.new 32; chown root:www-data /etc/jingkang-blog/auth/session.key.new; chmod 640 /etc/jingkang-blog/auth/session.key.new; mv /etc/jingkang-blog/auth/session.key.new /etc/jingkang-blog/auth/session.key; systemctl try-restart jingkang-private.service 2>/dev/null || true"
subprocess.run(['ssh', '-S', '/tmp/jingkang-blog-vps.sock', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                'root@107.174.127.153', remote], input=json.dumps(config), text=True, check=True, timeout=30)
print('生日验证已设置。终端没有保存生日明文。')
