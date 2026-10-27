# 首页 V1 图片素材记录

使用内置 imagegen（非CLI、未读取OpenAI API Key），输入仅为用户提供的首页设计参考图 `codex-clipboard-b8898c7a-7648-447a-aec9-cd1db6a216fb.png`。素材为参考场景重建，不声称逐像素原图裁切或额外版权授权。原始设计稿未放入公开目录。

| 文件 | 用途 | 尺寸与体积 |
|---|---|---|
| `web/public/images/love-at-the-window.webp` | 精选问题的爱情主题场景 | 1600×780，204670字节 |
| `web/public/images/quiet-landscape.webp` | 思辨引导区域的装饰水墨背景 | 1800×600，31796字节 |

生成后只做等比例缩小与WebP编码，使用现有Next依赖中的Sharp，不新增运行依赖。图内没有UI文字或按钮。SVG线条图标是前端代码，未生成位图图标。

## 爱情场景最终提示词

```text
Image editing/extraction task. From this supplied website design reference, produce ONLY the clean photograph visible in its upper-right rectangular image panel (approximately x=810 to1586, y=98 to477 in the 1672x941 reference). The image is two adult people's hands gently reaching toward each other at a rain-spattered window, warm sunset sun glowing between fingertips, softly out-of-focus city buildings, dark pine-green knit sleeves and amber light. Preserve this reference photograph composition, subjects, clothing, rain, mood and photographic appearance as faithfully as possible. Tight crop to that photograph, landscape approximately 2.05:1 aspect ratio. Absolutely no website UI, no Chinese text, no logos, no buttons, no frames, no captions. This is a photograph asset for a website, not a website mockup. Do not reproduce any part of the rest of the screenshot.
```

## 水墨背景最终提示词

```text
Create only a clean decorative website landscape asset derived from the pale ink-wash landscape in the lower horizontal banner of the supplied reference image. Absolutely no text, no UI, no buttons, no labels, no website frame. Panoramic horizontal Chinese shan shui ink watercolor on warm ivory xuan paper (#f8f6ef): extremely pale misty layered mountains and a few soft gray-green trees, a subtle river, fine distant contemporary city silhouette and a small softly pale ochre sun. Delicate, restrained, desaturated bamboo green / gray washes. The left 35 percent mostly empty warm ivory paper, mountains and river concentrated center and right. This is a subtle background behind real HTML text and a button, not a mockup. Wide landscape approximately 10:1 aspect ratio, single seamless composition, very low contrast across the whole image, light ink painting, no typography.
```

本轮用户后续提供的两张每日一问全屏参考仅作为下一阶段方向，未把它们嵌入首页或实现纵向滑动。
