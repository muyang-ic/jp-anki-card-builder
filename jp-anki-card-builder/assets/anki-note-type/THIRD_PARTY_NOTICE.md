# 第三方模板说明

正面模板和样式包含来自 [5mdld/anki-jlpt-decks](https://github.com/5mdld/anki-jlpt-decks) 的代码与链接。原项目采用 [Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/) 许可。

本仓库中的整理改动：

- 将用户提供的正面、背面和样式拆分为独立文件；
- 补充与本 Skill 的 27 列 TSV／36 字段笔记类型兼容说明；
- 未移除原模板中的版本检查、反馈、词典和在线 TTS 功能。

使用或再次分发这部分模板时，请保留原作者署名、原项目链接和 CC BY-NC 4.0 许可说明，并仅用于非商业用途。本仓库与原作者没有隶属或官方认可关系。

模板可能访问以下外部服务：

- GitHub API：检查原模板项目的最新版；
- 原项目的 GitHub Issues 或飞书表单：提交反馈；
- 由 `CONFIG()` 选择的外部词典；
- `anki.0w0.live` 和 `ms-ra-forwarder-for-ifreetime-v9q1.vercel.app`：本地音频缺失时的在线 TTS 回退。

如不需要在线 TTS，把 `front.html` 中的 `tts.enable` 设置为 `never`。
