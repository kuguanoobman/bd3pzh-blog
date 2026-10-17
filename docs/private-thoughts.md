# 个人想法

分类入口：`https://bd3pzh.top/categories/personal-thoughts/`。

访客输入农历腊月生日的日数（1～30）解锁，不含年月。`9` 和 `09` 视为同一天。生日由作者在终端交互设置，服务器只保存加盐 PBKDF2 摘要。Cookie 使用 HTTPS、HttpOnly、SameSite，12 小时后失效，页面可主动重新上锁。同一 IP 在 15 分钟内最多尝试 5 次，全站还有限制。

当前分类没有文章，解锁后显示空状态。

## 写私密文章

原稿只保存在本机 `.private-content/`（已忽略 Git），例如 `.private-content/随想.md`：

```markdown
---
title: "一篇随想"
date: 2026-10-18T12:00:00+08:00
---

这里开始写正文。
```

在项目目录执行：

```sh
node scripts/encrypt-private-post.mjs .private-content/随想.md my-thought

git add private-posts
git commit -m "更新个人想法"
git push origin main
ssh blog-deploy
```

第二个参数是唯一的英文标识（小写字母、数字和连字符），相同标识再次加密会更新该篇文章。

密文放在 `private-posts/`。RSA-OAEP 公钥可以公开；解密私钥仅在服务器 `/etc/jingkang-blog/private-posts.pem`，不要提交到仓库。正文使用随机 AES-256-GCM 密钥加密。服务器构建到公开网站目录之外，访问 `/thoughts/` 及文章链接均须验证，不进入公开搜索、RSS 或站点地图。

请勿把私密原稿放进 `content/post/` 再提交。这个电脑已启用提交前检查，避免把标为“个人想法”的明文文章提交到公开 GitHub。其他电脑需执行 `git config core.hooksPath .githooks` 启用同样的检查。

现阶段私密文章支持 Markdown 正文。插图请使用公开可见图片；私密附件上传尚未提供，不要把私密照片放入 `static/`。

## 维护

`ssh blog-deploy` 继续使用原有的专用部署密钥。服务器上的部署脚本已添加公开内容检查和私密文章构建步骤。

首次安装需要管理员连接后运行 `python3 /srv/bd3pzh-blog/ops/install-private.py`。安装器会备份原有 Nginx 配置和部署脚本，Nginx 检查通过后才生效。服务为 `jingkang-private.service`，仅监听 `127.0.0.1:8766`。

修改解锁日数时，先在本机建立临时管理员 SSH 连接，再运行 `python3 scripts/set-private-birthday.py`；不要将生日写进源码或聊天。

服务器解密私钥应由作者通过自己的加密备份工具备份。丢失私钥后，仓库中的密文无法恢复。
