import {mkdtempSync,mkdirSync,readFileSync,writeFileSync,copyFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {generateKeyPairSync,privateDecrypt,createDecipheriv,constants} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
const root=mkdtempSync(join(tmpdir(),'private-post-test-'));
try {
 for(const d of ['scripts','config','.private-content'])mkdirSync(join(root,d));
 const keys=generateKeyPairSync('rsa',{modulusLength:2048,publicKeyEncoding:{type:'spki',format:'pem'},privateKeyEncoding:{type:'pkcs8',format:'pem'}});
 writeFileSync(join(root,'config/private-posts-public.pem'),keys.publicKey);
 copyFileSync(resolve('scripts/encrypt-private-post.mjs'),join(root,'scripts/encrypt-private-post.mjs'));
 writeFileSync(join(root,'.private-content/example.md'),'---\ntitle: "PRIVATE_FIXTURE_TITLE"\ndate: 2020-01-01\n---\n\nPRIVATE_FIXTURE_BODY');
 execFileSync(process.execPath,[join(root,'scripts/encrypt-private-post.mjs'),join(root,'.private-content/example.md'),'fixture'],{stdio:'pipe'});
 const raw=readFileSync(join(root,'private-posts/fixture.json'),'utf8');
 assert(!raw.includes('PRIVATE_FIXTURE'));
 const envelope=JSON.parse(raw);
 const key=privateDecrypt({key:keys.privateKey,oaepHash:'sha256',padding:constants.RSA_PKCS1_OAEP_PADDING},Buffer.from(envelope.key,'base64'));
 const data=Buffer.from(envelope.data,'base64');
 const decode=(ciphertext)=>{const decipher=createDecipheriv('aes-256-gcm',key,Buffer.from(envelope.iv,'base64'));decipher.setAuthTag(ciphertext.subarray(-16));return Buffer.concat([decipher.update(ciphertext.subarray(0,-16)),decipher.final()]).toString();};
 const payload=JSON.parse(decode(data));assert.equal(payload.title,'PRIVATE_FIXTURE_TITLE');assert(payload.body.includes('PRIVATE_FIXTURE_BODY'));
 data[0]^=1;assert.throws(()=>decode(data));
 console.log('Encryption round trip, metadata privacy and tamper rejection passed.');
} finally {rmSync(root,{recursive:true,force:true});}
