# 配套 Anki 笔记类型模板

此目录包含 Card1（日→中）的正面、背面、样式和完整字段清单。

## 文件

- `front.html`：正面模板
- `back.html`：背面模板
- `styling.css`：卡片样式
- `fields.txt`：36 个字段，必须按顺序建立
- `THIRD_PARTY_NOTICE.md`：模板来源、许可与网络行为说明

## 与生成器的兼容关系

笔记类型共有 36 个字段，但生成器继续输出前 27 个字段。导入时把 TSV 第 1～27 列映射到同名字段；第 28～36 个扩展字段保持为空即可。Anki 会把未提供的后续字段视为空值。

扩展字段是：

```text
SentType4
SentKanji4
SentFurigana4
SentDef4
SentDefTC4
SentAudio4
Frequency
Alt1
Alt2
```

`Alt1` 必须存在。Card1 使用 `{{^Alt1}}` 条件，因此 `Alt1` 为空时显示本卡；填入内容时会隐藏本卡。

## 安装

1. 在 Anki 桌面版打开“工具 → 管理笔记类型”。
2. 新建一个笔记类型，例如 `JP Anki Card Builder 36`。
3. 打开“字段”，按照 `fields.txt` 的顺序建立全部 36 个字段。
4. 打开“卡片”，把 `front.html`、`back.html`、`styling.css` 分别粘贴到正面、背面和样式区域。
5. 保存后导入 `anki_import.tsv`，选择这个笔记类型，确认第 1～27 列映射到同名字段，并启用 HTML。
6. 把生成的 MP3 直接复制到当前 Anki 用户的 `collection.media` 根目录。

## 字体

样式会尝试加载以下媒体字体，但本仓库不附带字体文件：

```text
_SourceHanSerifCN-Medium.otf
_SourceHanSerifTW-Medium.otf
_SourceHanSerifJP-Medium.otf
```

没有这些文件时会使用系统备用字体，不影响卡片字段和音频。

## 在线功能

模板包含外部词典跳转、GitHub 版本检查和在线 TTS 回退。若只使用 Skill 生成的本地 MP3，可在 `front.html` 的 `CONFIG()` 中把 `tts.enable` 改为 `never`。其他网络行为与来源见 `THIRD_PARTY_NOTICE.md`。
