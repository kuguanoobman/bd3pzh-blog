#!/usr/bin/env node
// Keep original Markdown in the ignored .private-content directory.
import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {resolve, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {randomBytes, publicEncrypt, constants, createCipheriv} from 'node:crypto';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const [source, id] = process.argv.slice(2);
if (!source || !/^[a-z0-9][a-z0-9-]{0,79}$/.test(id || '')) {
  console.error('用法：node scripts/encrypt-private-post.mjs .private-content/文章.md 英文文章标识');
  process.exit(1);
}
const input = readFileSync(resolve(source), 'utf8');
const match = input.match(/^(---|\+\+\+)\r?\n([\s\S]*?)\r?\n\1\r?\n([\s\S]*)$/);
if (!match) throw new Error('文章需要 YAML 或 TOML 头部，包含单行 title。');
const titleLine = match[2].match(/^title\s*[:=]\s*(.+)\s*$/m)?.[1]?.trim();
if (!titleLine) throw new Error('缺少 title。');
let title = titleLine;
if (title.startsWith('"')) title = JSON.parse(title);
else if (title.startsWith("'") && title.endsWith("'")) title = title.slice(1,-1);
const date = match[2].match(/^date\s*[:=]\s*(.+)\s*$/m)?.[1]?.replace(/^['"]|['"]$/g,'') || new Date().toISOString();
if (!Number.isFinite(Date.parse(date))) throw new Error('文章日期无效。');
const payload = JSON.stringify({id,title,date,body:match[3]});
const key = randomBytes(32), iv = randomBytes(12);
const cipher = createCipheriv('aes-256-gcm',key,iv);
const ciphertext = Buffer.concat([cipher.update(payload,'utf8'),cipher.final()]);
const wrappedKey = publicEncrypt({key:readFileSync(resolve(root,'config/private-posts-public.pem')),oaepHash:'sha256',padding:constants.RSA_PKCS1_OAEP_PADDING},key);
mkdirSync(resolve(root,'private-posts'),{recursive:true});
writeFileSync(resolve(root,`private-posts/${id}.json`),JSON.stringify({version:1,key:wrappedKey.toString('base64'),iv:iv.toString('base64'),data:Buffer.concat([ciphertext,cipher.getAuthTag()]).toString('base64')})+'\n');
console.log(`已加密：private-posts/${id}.json。仅提交密文文件，原稿保留在 .private-content/。`);
