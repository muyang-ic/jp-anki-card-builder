# JP Anki Card Builder

一个用于 Codex 的日语 Anki 词卡生成 Skill。输入日语词汇列表后，它会生成经过校验的 27 字段 TSV、词汇音频和两条例句音频，可直接导入 Anki。

## 主要功能

- 每个词条严格输出 27 个 Anki 字段
- 自动生成简体、繁体中文释义
- 每个词条生成两条简短自然的日语例句
- 为句中所有汉字添加假名，并加粗目标词
- 在例句中自然复用同批词汇，帮助交叉复习
- 使用假名文本生成语音，减少多音汉字误读
- 每张卡生成 3 个 MP3：词汇 1 个、例句 2 个
- 音频全部成功后才生成最终 `anki_import.tsv`
- 支持手动导入，也可在明确授权后通过 AnkiConnect 导入

## 目录结构

```text
jp-anki-card-builder/
├─ SKILL.md
├─ agents/
│  └─ openai.yaml
├─ references/
│  ├─ anki-integration.md
│  ├─ card-schema.md
│  └─ japanese-quality.md
└─ scripts/
   ├─ anki_common.py
   ├─ anki_connect.py
   ├─ build_package.py
   ├─ generate_audio.py
   ├─ requirements.txt
   ├─ scan_next_id.py
   ├─ self_test.py
   ├─ setup_runtime.py
   └─ validate_package.py
```

## 环境要求

- Windows、macOS 或 Linux
- Codex
- Python 3.10 或更高版本
- 生成音频时需要联网
- 手动导入需要 Anki；自动导入还需要 AnkiConnect

本 Skill 使用 `edge-tts==7.2.8`。`edge-tts` 是微软在线语音服务的 Python 客户端，并不是可离线下载的语音模型。依赖包可以离线安装，但实际合成 MP3 时仍然需要网络连接。

## 安装 Skill

### 方法一：让 Codex 从 GitHub 安装（推荐）

在新电脑的 Codex 中发送：

```text
请使用 skill-installer 从下面的 GitHub 地址安装 Skill：
https://github.com/muyang-ic/jp-anki-card-builder/tree/main/jp-anki-card-builder
```

安装完成后，在下一个对话回合或新任务中即可使用。

也可以在 PowerShell 中直接运行内置安装脚本：

```powershell
$Installer = "$env:USERPROFILE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py"

py $Installer `
  --repo "muyang-ic/jp-anki-card-builder" `
  --path "jp-anki-card-builder"
```

默认安装位置：

```text
C:\Users\你的用户名\.codex\skills\jp-anki-card-builder
```

如果目标目录已经存在，安装器会停止，不会覆盖原有 Skill。需要更新时，请先备份原目录，再明确决定是否替换。

### 方法二：手动复制

克隆仓库：

```powershell
git clone https://github.com/muyang-ic/jp-anki-card-builder.git
```

复制 Skill 子目录：

```powershell
$Source = ".\jp-anki-card-builder\jp-anki-card-builder"
$Destination = "$env:USERPROFILE\.codex\skills\jp-anki-card-builder"

Copy-Item -LiteralPath $Source -Destination $Destination -Recurse
```

确认入口文件存在：

```powershell
Test-Path "$env:USERPROFILE\.codex\skills\jp-anki-card-builder\SKILL.md"
```

返回 `True` 后，重启 Codex 或开启一个新任务。

macOS/Linux 的默认安装目录为：

```text
~/.codex/skills/jp-anki-card-builder
```

## 安装音频运行环境

Skill 文件和音频运行环境是分开的。不要从另一台电脑复制 Python 虚拟环境，因为虚拟环境通常包含旧电脑的绝对路径。

### 自动安装

Windows PowerShell：

```powershell
$SkillRoot = "$env:USERPROFILE\.codex\skills\jp-anki-card-builder"
$Runtime = "$env:USERPROFILE\.codex\runtimes\jp-anki-audio"

py "$SkillRoot\scripts\setup_runtime.py" $Runtime
```

安装脚本会：

1. 创建独立 Python 虚拟环境；
2. 安装固定版本 `edge-tts==7.2.8`；
3. 验证运行环境是否可用。

验证安装：

```powershell
py "$SkillRoot\scripts\setup_runtime.py" $Runtime --check-only
```

正常结果类似：

```json
{
  "status": "ok",
  "python": "C:\\Users\\你的用户名\\.codex\\runtimes\\jp-anki-audio\\Scripts\\python.exe",
  "edge_tts": "7.2.8"
}
```

macOS/Linux：

```bash
SKILL_ROOT="$HOME/.codex/skills/jp-anki-card-builder"
RUNTIME="$HOME/.codex/runtimes/jp-anki-audio"

python3 "$SKILL_ROOT/scripts/setup_runtime.py" "$RUNTIME"
python3 "$SKILL_ROOT/scripts/setup_runtime.py" "$RUNTIME" --check-only
```

### Windows TLS 下载失败时离线安装

如果出现 `SEC_E_NO_CREDENTIALS`、证书或 TLS 错误，可在另一台网络正常、Python 版本和系统架构相同的 Windows 电脑上制作完整离线依赖包：

```powershell
$Bundle = "$env:USERPROFILE\Desktop\edge_tts_offline"
New-Item -ItemType Directory -Force -Path $Bundle

py -m pip download `
  --only-binary=:all: `
  --dest $Bundle `
  "edge-tts==7.2.8"
```

把整个 `edge_tts_offline` 文件夹复制到目标电脑，例如：

```text
C:\Users\你的用户名\Downloads\edge_tts_offline
```

如果虚拟环境尚未创建：

```powershell
$Runtime = "$env:USERPROFILE\.codex\runtimes\jp-anki-audio"
py -m venv $Runtime
```

从本地依赖目录安装，不访问 PyPI：

```powershell
$RuntimePython = "$env:USERPROFILE\.codex\runtimes\jp-anki-audio\Scripts\python.exe"
$Bundle = "$env:USERPROFILE\Downloads\edge_tts_offline"

& $RuntimePython -m pip install `
  --no-index `
  --find-links $Bundle `
  "edge-tts==7.2.8"
```

验证：

```powershell
& $RuntimePython -c "import importlib.metadata as m; print(m.version('edge-tts'))"
& $RuntimePython -m pip check
```

正确结果应包含：

```text
7.2.8
No broken requirements found.
```

测试日语语音：

```powershell
& $RuntimePython -m edge_tts `
  --voice "ja-JP-NanamiNeural" `
  --text "個室を予約しました。" `
  --write-media "$env:TEMP\jp_anki_test.mp3"
```

## 使用方法

安装完成后，在 Codex 中发送词汇列表。可以显式调用 Skill：

```text
$jp-anki-card-builder

NoteID 从 1 开始：
個室
梅雨
筋トレ
すする（麺をすする）
```

也可以直接描述任务：

```text
请把下面的词汇生成日语 Anki 词卡，NoteID 从 1000 开始：
個室
気遣い
蒸し暑い
```

括号中的文字会被视为用法提示，不会成为词头的一部分。Skill 会让至少一条例句体现该提示语境。

## 输出文件

成功后会得到：

```text
输出目录/
├─ anki_import.tsv
└─ media/
   ├─ jpa_v_...mp3
   ├─ jpa_s1_...mp3
   └─ jpa_s2_...mp3
```

中间阶段还可能包含：

```text
anki_import.pending.tsv
manifest.json
audio_report.json
validation.json
```

只有全部音频成功后，`anki_import.pending.tsv` 才会提升为最终的 `anki_import.tsv`。因此不要把 pending 文件当作完整批次导入。

## 手动导入 Anki

1. 打开 Anki 的用户数据目录；
2. 把生成的 `media` 文件夹中的所有 MP3 复制到 `collection.media` 根目录；
3. 不要把 `media` 作为嵌套文件夹整体放进去；
4. 在 Anki 中导入 `anki_import.tsv`；
5. 确认分隔符为 Tab，并启用 HTML；
6. 导入后运行 Anki 的“检查媒体”。

TSV 第一列为 `NoteID`，可用于 Anki 文本导入时的重复检查，但它不是 Anki 内部 GUID。

## 可选：通过 AnkiConnect 导入

自动导入属于外部写入操作，默认关闭。只有在明确授权并配置 profile 后才应使用。

Profile 示例：

```json
{
  "deck": "Japanese",
  "notetype": "Japanese 27",
  "tags": ["jp-anki"],
  "audio": {
    "backend": "edge",
    "voice": "ja-JP-NanamiNeural",
    "rate": "+0%",
    "volume": "+0%",
    "pitch": "+0Hz",
    "concurrency": 4,
    "retries": 3
  },
  "anki_connect": {
    "url": "http://127.0.0.1:8765",
    "api_key": "",
    "auto_import": false
  }
}
```

预检不会写入 Anki：

```powershell
py "$SkillRoot\scripts\anki_connect.py" preflight `
  "C:\路径\到\完整输出目录" `
  --profile "C:\路径\到\jp_anki_profile.json"
```

确认预检无误，并明确同意写入后：

```powershell
py "$SkillRoot\scripts\anki_connect.py" import `
  "C:\路径\到\完整输出目录" `
  --profile "C:\路径\到\jp_anki_profile.json" `
  --commit
```

脚本不会直接修改 `collection.anki2`，也不会默认覆盖已有笔记。

## 自检

Skill 自带不需要网络或 Anki 的回归测试：

```powershell
py "$SkillRoot\scripts\self_test.py"
```

成功结果：

```json
{"status": "ok", "tests": 13}
```

还可以检查 Skill 的结构：

```powershell
$Validator = "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py"
py $Validator $SkillRoot
```

## 常见问题

### 已安装 Skill，但 Codex 没有识别

- 确认 `SKILL.md` 位于 `~/.codex/skills/jp-anki-card-builder/SKILL.md`；
- 不要多嵌套一层同名目录；
- 重启 Codex 或开启新任务；
- 显式使用 `$jp-anki-card-builder` 测试调用。

### `setup_runtime.py` 提示目录已存在但无效

该脚本不会自动删除或覆盖已有运行环境。你可以把缺失依赖手动安装进现有虚拟环境，或者选择一个新的空目录创建运行环境。

### `edge-tts` 已安装，但无法生成 MP3

安装成功只代表 Python 客户端可用。实际生成语音仍需访问微软在线语音服务。请检查代理、防火墙、校园或公司网络限制。

### 部分音频生成失败

脚本会保留已经成功的 MP3。网络恢复后重新运行同一个音频生成步骤即可复用缓存，不必重新生成整批卡片。

### 没有生成 `anki_import.tsv`

检查是否仍存在 `anki_import.pending.tsv`。这通常表示至少一个音频尚未成功生成。查看 `audio_report.json` 中的失败文件和错误信息。

## 数据与安全边界

- 不会修改原始词汇列表或旧批次文件；
- 不会直接修改 Anki 数据库；
- 默认只导出文件，不自动导入 Anki；
- 不会在音频未完成时交付最终 TSV；
- API key 不应写入 Skill 目录或提交到 GitHub。
