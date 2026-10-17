# 靖康的博客

基于 Hugo 和 Stack 主题，使用「夏日放映室」赛璐璐动画视觉。

## 本地预览

```sh
hugo server --cacheDir /tmp/jingkang-hugo-cache
```

打开 http://localhost:1313/ 。

## 写文章

```sh
hugo new content/post/文章标题.md
```

完成后将文章头部的 `draft` 改为 `false`。

## 构建与部署

```sh
hugo --minify --cacheDir /tmp/jingkang-hugo-cache
```

生成文件位于 `public/`。沿用现有 `deploy-blog` 部署流程。

## 视觉维护

- 首页：`layouts/home.html`
- 全站导航和结构：`layouts/baseof.html`
- 全站视觉与手机适配：`assets/css/cel.css`
- 页脚：`layouts/_partials/footer/footer.html`
- 首页插画：`static/images/summer-train.webp`
- 插画生成说明：`docs/visual-design.md`

自定义文件均位于项目目录，未修改 Stack 主题子模块。首页文章、分类和数量由 Hugo 自动生成，草稿不公开。
