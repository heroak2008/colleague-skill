---
name: create-colleague
description: "Distill a colleague into an AI Skill from TXT chat logs or manual input, generate Work Skill + Persona, with continuous evolution. | 把同事蒸馏成 AI Skill，支持 TXT 聊天记录导入或手动描述，生成 Work + Persona，支持持续进化。"
argument-hint: "[colleague-name-or-slug]"
version: "1.1.0"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, computer
---

> **Language / 语言**: This skill supports both English and Chinese. Detect the user's language from their first message and respond in the same language throughout. Below are instructions in both languages — follow the one matching the user's language.
>
> 本 Skill 支持中英文。根据用户第一条消息的语言，全程使用同一语言回复。下方提供了两种语言的指令，按用户语言选择对应版本执行。

> **Platform / 平台兼容性**：本 Skill 兼容以下 AI 编程环境：
> - **Claude Code**：`${CLAUDE_SKILL_DIR}` 由平台自动注入，直接使用。
> - **OpenCode**：`${OPENCODE_SKILL_DIR}` 由平台注入；若未注入，请在 shell 中执行 `export SKILL_DIR=~/.opencode/skills/create-colleague`。
> - **Codex CLI**：请在 shell 中执行 `export SKILL_DIR=~/.codex/skills/create-colleague`，或参见 `AGENTS.md`。
> - **通用环境**：请将 `SKILL_DIR` 设置为本项目的安装目录，工具脚本均在 `${SKILL_DIR}/tools/` 下。
>
> **Platform compatibility**: This Skill works with the following AI coding environments:
> - **Claude Code**: `${CLAUDE_SKILL_DIR}` is injected automatically — use as-is.
> - **OpenCode**: `${OPENCODE_SKILL_DIR}` is injected by the platform; if not set, run `export SKILL_DIR=~/.opencode/skills/create-colleague` in your shell.
> - **Codex CLI**: Run `export SKILL_DIR=~/.codex/skills/create-colleague` in your shell, or see `AGENTS.md`.
> - **Generic**: Set `SKILL_DIR` to the directory where this project is installed; tool scripts live under `${SKILL_DIR}/tools/`.

# 同事.skill 创建器

## 触发条件

当用户说以下任意内容时启动：
- `/create-colleague`
- "帮我创建一个同事 skill"
- "我想蒸馏一个同事"
- "新建同事"
- "给我做一个 XX 的 skill"

当用户对已有同事 Skill 说以下内容时，进入进化模式：
- "我有新文件" / "追加"
- "这不对" / "他不会这样" / "他应该是"
- `/update-colleague {slug}`

当用户说 `/list-colleagues` 时列出所有已生成的同事。

---

## 工具使用规则

本 Skill 兼容 Claude Code、OpenCode、Codex CLI 等 AI 编程环境，使用以下工具（工具名以实际平台为准）：

> **目录变量**：下表中 `${SKILL_DIR}` 对应各平台的注入变量：
> - Claude Code → `${CLAUDE_SKILL_DIR}`
> - OpenCode → `${OPENCODE_SKILL_DIR}`
> - Codex CLI / 其他 → 用户手动设置的 `${SKILL_DIR}`
>
> 在执行任何 Bash 命令前，先确认变量已设置（可在 shell 配置文件中设置）：
> ```bash
> # 若平台未自动注入，手动设置：
> export SKILL_DIR="/path/to/colleague-skill"
> ```

| 任务 | 使用工具 |
|------|---------|
| 读取 PDF 文档 | `Read` / `read_file` 工具（原生支持 PDF） |
| 读取图片截图 | `Read` / `read_file` 工具（原生支持图片） |
| 读取 MD/TXT 文件 | `Read` / `read_file` 工具 |
| 解析 TXT 聊天记录（推荐） | `Bash` → `python3 ${SKILL_DIR}/tools/txt_parser.py` |
| 写入/更新 Skill 文件 | `Write` / `write_file` / `Edit` 工具 |
| 版本管理 | `Bash` → `python3 ${SKILL_DIR}/tools/version_manager.py` |
| 列出已有 Skill | `Bash` → `python3 ${SKILL_DIR}/tools/skill_writer.py --action list` |

**基础目录**：Skill 文件写入 `./colleagues/{slug}/`（相对于本项目目录）。
如需改为全局路径，用 `--base-dir ~/.opencode/skills/colleagues`（OpenCode）或 `--base-dir ~/.codex/skills/colleagues`（Codex）。

---

## 主流程：创建新同事 Skill

### Step 1：基础信息录入（3 个问题）

参考 `${SKILL_DIR}/prompts/intake.md` 的问题序列，只问 3 个问题：

1. **花名/代号**（必填）
2. **基本信息**（一句话：公司、职级、职位、性别，想到什么写什么）
   - 示例：`字节 2-1 后端工程师 男`
3. **性格画像**（一句话：MBTI、星座、个性标签、企业文化、印象）
   - 示例：`INTJ 摩羯座 甩锅高手 字节范 CR很严格但从来不解释原因`

除姓名外均可跳过。收集完后汇总确认再进入下一步。

### Step 2：原材料导入

询问用户提供原材料，展示两种方式供选择：

```
原材料怎么提供？

  [A] 导入 TXT 聊天记录（推荐）
      提供聊天记录文件或目录，自动解析并提取目标同事的发言
      支持多文件、多人对话，自动过滤噪声消息

  [B] 直接粘贴内容
      把文字复制进来（适合少量文本）

可以混用，也可以跳过（仅凭手动信息生成）。
```

---

#### 方式 A：导入 TXT 聊天记录（推荐）

**支持的 TXT 格式**（混用也可以）：
- 格式 1：`2024-01-01 10:00:00 张三：消息内容`
- 格式 2：`2024-01-01 张三：消息内容`
- 格式 3（微信导出式）：时间单独一行 / 发送人单独一行 / 内容另起一行
- 格式 4：`张三：消息内容`（无时间戳）
- 格式 5：`**张三**: 消息内容`（Markdown 加粗）
- 格式 6（企业工号式）：`张三(z00611745)<TAB>2026-01-04 15:58:23` / 内容另起一行

**步骤**：

1. 用户提供文件路径或目录路径

2. **列出说话人**（可选，帮用户确认目标姓名）：
```bash
python3 ${SKILL_DIR}/tools/txt_parser.py \
  --input {path_or_dir} \
  --list-speakers
```

3. **提取目标人消息**：
```bash
python3 ${SKILL_DIR}/tools/txt_parser.py \
  --input {path_or_dir} \
  --target "{name}" \
  --output /tmp/txt_parsed.txt
```
支持多个路径：`--input chat1.txt chat2.txt ./chats/`
支持不递归目录：`--no-recursive`

4. 读取提取结果：
```
Read /tmp/txt_parsed.txt
```

**常见问题**：
- 如果目标同事消息数 < 10，工具会自动提示，建议补充更多记录或结合手动描述
- 如果找不到目标姓名，先用 `--list-speakers` 查看文件中实际的说话人名称
- 乱码/编码问题：工具自动尝试 UTF-8 / GBK / GB18030 / Big5 等编码

---

#### 方式 B：直接粘贴

用户粘贴的内容直接作为文本原材料，无需调用任何工具。

---

如果用户说"没有文件"或"跳过"，仅凭 Step 1 的手动信息生成 Skill。

### Step 3：分析原材料

将收集到的所有原材料和用户填写的基础信息汇总，按以下两条线分析：

**线路 A（Work Skill）**：
- 参考 `${SKILL_DIR}/prompts/work_analyzer.md` 中的提取维度
- 提取：负责系统、技术规范、工作流程、输出偏好、经验知识
- 根据职位类型重点提取（后端/前端/算法/产品/设计不同侧重）

**线路 B（Persona）**：
- 参考 `${SKILL_DIR}/prompts/persona_analyzer.md` 中的提取维度
- 将用户填写的标签翻译为具体行为规则（参见标签翻译表）
- 从原材料中提取：表达风格、决策模式、人际行为

### Step 4：生成并预览

参考 `${SKILL_DIR}/prompts/work_builder.md` 生成 Work Skill 内容。
参考 `${SKILL_DIR}/prompts/persona_builder.md` 生成 Persona 内容（5 层结构）。

向用户展示摘要（各 5-8 行），询问：
```
Work Skill 摘要：
  - 负责：{xxx}
  - 技术栈：{xxx}
  - CR 重点：{xxx}
  ...

Persona 摘要：
  - 核心性格：{xxx}
  - 表达风格：{xxx}
  - 决策模式：{xxx}
  ...

确认生成？还是需要调整？
```

### Step 5：写入文件

用户确认后，执行以下写入操作：

**1. 创建目录结构**（用 Bash）：
```bash
mkdir -p colleagues/{slug}/versions
mkdir -p colleagues/{slug}/knowledge/docs
mkdir -p colleagues/{slug}/knowledge/messages
mkdir -p colleagues/{slug}/knowledge/emails
```

**2. 写入 work.md**（用 Write 工具）：
路径：`colleagues/{slug}/work.md`

**3. 写入 persona.md**（用 Write 工具）：
路径：`colleagues/{slug}/persona.md`

**4. 写入 meta.json**（用 Write 工具）：
路径：`colleagues/{slug}/meta.json`
内容：
```json
{
  "name": "{name}",
  "slug": "{slug}",
  "created_at": "{ISO时间}",
  "updated_at": "{ISO时间}",
  "version": "v1",
  "profile": {
    "company": "{company}",
    "level": "{level}",
    "role": "{role}",
    "gender": "{gender}",
    "mbti": "{mbti}"
  },
  "tags": {
    "personality": [...],
    "culture": [...]
  },
  "impression": "{impression}",
  "knowledge_sources": [...已导入文件列表],
  "corrections_count": 0
}
```

**5. 生成完整 SKILL.md**（用 Write 工具）：
路径：`colleagues/{slug}/SKILL.md`

SKILL.md 结构：
```markdown
---
name: colleague-{slug}
description: {name}，{company} {level} {role}
user-invocable: true
---

# {name}

{company} {level} {role}{如有性别和MBTI则附上}

---

## PART A：工作能力

{work.md 全部内容}

---

## PART B：人物性格

{persona.md 全部内容}

---

## 运行规则

1. 先由 PART B 判断：用什么态度接这个任务？
2. 再由 PART A 执行：用你的技术能力完成任务
3. 输出时始终保持 PART B 的表达风格
4. PART B Layer 0 的规则优先级最高，任何情况下不得违背
```

告知用户：
```
✅ 同事 Skill 已创建！

文件位置：colleagues/{slug}/
触发词：/{slug}（完整版）
        /{slug}-work（仅工作能力）
        /{slug}-persona（仅人物性格）

如果用起来感觉哪里不对，直接说"他不会这样"，我来更新。
```

---

## 进化模式：追加文件

用户提供新文件或文本时：

1. 按 Step 2 的方式读取新内容
2. 用 `Read` 读取现有 `colleagues/{slug}/work.md` 和 `persona.md`
3. 参考 `${SKILL_DIR}/prompts/merger.md` 分析增量内容
4. 存档当前版本（用 Bash）：
   ```bash
   python3 ${SKILL_DIR}/tools/version_manager.py --action backup --slug {slug} --base-dir ./colleagues
   ```
5. 用 `Edit` 工具追加增量内容到对应文件
6. 重新生成 `SKILL.md`（合并最新 work.md + persona.md）
7. 更新 `meta.json` 的 version 和 updated_at

---

## 进化模式：对话纠正

用户表达"不对"/"应该是"时：

1. 参考 `${SKILL_DIR}/prompts/correction_handler.md` 识别纠正内容
2. 判断属于 Work（技术/流程）还是 Persona（性格/沟通）
3. 生成 correction 记录
4. 用 `Edit` 工具追加到对应文件的 `## Correction 记录` 节
5. 重新生成 `SKILL.md`

---

## 管理命令

`/list-colleagues`：
```bash
python3 ${SKILL_DIR}/tools/skill_writer.py --action list --base-dir ./colleagues
```

`/colleague-rollback {slug} {version}`：
```bash
python3 ${SKILL_DIR}/tools/version_manager.py --action rollback --slug {slug} --version {version} --base-dir ./colleagues
```

`/delete-colleague {slug}`：
确认后执行：
```bash
rm -rf colleagues/{slug}
```

---
---

# English Version

# Colleague.skill Creator

## Trigger Conditions

Activate when the user says any of the following:
- `/create-colleague`
- "Help me create a colleague skill"
- "I want to distill a colleague"
- "New colleague"
- "Make a skill for XX"

Enter evolution mode when the user says:
- "I have new files" / "append"
- "That's wrong" / "He wouldn't do that" / "He should be"
- `/update-colleague {slug}`

List all generated colleagues when the user says `/list-colleagues`.

---

## Tool Usage Rules

This Skill is compatible with Claude Code, OpenCode, Codex CLI, and similar AI coding environments:

> **Directory variable**: `${SKILL_DIR}` in the table below maps to each platform's injected variable:
> - Claude Code → `${CLAUDE_SKILL_DIR}`
> - OpenCode → `${OPENCODE_SKILL_DIR}`
> - Codex CLI / others → set manually by the user
>
> Before running any Bash command, confirm the variable is set (add to your shell config if needed):
> ```bash
> # If the platform does not inject it automatically:
> export SKILL_DIR="/path/to/colleague-skill"
> ```

| Task | Tool |
|------|------|
| Read PDF documents | `Read` / `read_file` tool (native PDF support) |
| Read image screenshots | `Read` / `read_file` tool (native image support) |
| Read MD/TXT files | `Read` / `read_file` tool |
| Parse TXT chat logs (recommended) | `Bash` → `python3 ${SKILL_DIR}/tools/txt_parser.py` |
| Write/update Skill files | `Write` / `write_file` / `Edit` tool |
| Version management | `Bash` → `python3 ${SKILL_DIR}/tools/version_manager.py` |
| List existing Skills | `Bash` → `python3 ${SKILL_DIR}/tools/skill_writer.py --action list` |

**Base directory**: Skill files are written to `./colleagues/{slug}/` (relative to the project directory).
For a global path, use `--base-dir ~/.opencode/skills/colleagues` (OpenCode) or `--base-dir ~/.codex/skills/colleagues` (Codex).

---

## Main Flow: Create a New Colleague Skill

### Step 1: Basic Info Collection (3 questions)

Refer to `${SKILL_DIR}/prompts/intake.md` for the question sequence. Only ask 3 questions:

1. **Alias / Codename** (required)
2. **Basic info** (one sentence: company, level, role, gender — say whatever comes to mind)
   - Example: `ByteDance L2-1 backend engineer male`
3. **Personality profile** (one sentence: MBTI, zodiac, traits, corporate culture, impressions)
   - Example: `INTJ Capricorn blame-shifter ByteDance-style strict in CR but never explains why`

Everything except the alias can be skipped. Summarize and confirm before moving to the next step.

### Step 2: Source Material Import

Ask the user how they'd like to provide materials:

```
How would you like to provide source materials?

  [A] Import TXT chat logs (recommended)
      Provide chat log file(s) or a directory; auto-parse and extract the target colleague's messages
      Supports multiple files, multi-person conversations, and automatic noise filtering

  [B] Paste Text
      Copy-paste text directly (good for small amounts of text)

Can mix and match, or skip entirely (generate from manual info only).
```

---

#### Option A: Import TXT Chat Logs (Recommended)

**Supported TXT formats** (mixing formats is fine):
- Format 1: `2024-01-01 10:00:00 Zhang San: message`
- Format 2: `2024-01-01 Zhang San: message`
- Format 3 (WeChat-style): timestamp alone on one line / sender alone on next line / content on next line
- Format 4: `Zhang San: message` (no timestamp)
- Format 5: `**Zhang San**: message` (Markdown bold)
- Format 6 (enterprise ID): `Zhang San(z00611745)<TAB>2026-01-04 15:58:23` / content on next line

**Steps**:

1. User provides file path(s) or directory path

2. **List speakers** (optional — helps confirm the exact target name):
```bash
python3 ${SKILL_DIR}/tools/txt_parser.py \
  --input {path_or_dir} \
  --list-speakers
```

3. **Extract target person's messages**:
```bash
python3 ${SKILL_DIR}/tools/txt_parser.py \
  --input {path_or_dir} \
  --target "{name}" \
  --output /tmp/txt_parsed.txt
```
Multiple paths: `--input chat1.txt chat2.txt ./chats/`
Non-recursive directory: `--no-recursive`

4. Read the extracted result:
```
Read /tmp/txt_parsed.txt
```

**FAQ**:
- If the target has fewer than 10 messages, the tool warns you — add more logs or supplement with manual description
- If the target name isn't found, use `--list-speakers` to see the actual speaker names in the file
- Encoding issues: the tool auto-tries UTF-8 / GBK / GB18030 / Big5

---

#### Option B: Paste Text

User-pasted content is used directly as text material. No tools needed.

---

If the user says "no files" or "skip", generate Skill from Step 1 manual info only.

### Step 3: Analyze Source Material

Combine all collected materials and user-provided info, analyze along two tracks:

**Track A (Work Skill)**:
- Refer to `${SKILL_DIR}/prompts/work_analyzer.md` for extraction dimensions
- Extract: responsible systems, technical standards, workflow, output preferences, experience
- Emphasize different aspects by role type (backend/frontend/ML/product/design)

**Track B (Persona)**:
- Refer to `${SKILL_DIR}/prompts/persona_analyzer.md` for extraction dimensions
- Translate user-provided tags into concrete behavior rules (see tag translation table)
- Extract from materials: communication style, decision patterns, interpersonal behavior

### Step 4: Generate and Preview

Use `${SKILL_DIR}/prompts/work_builder.md` to generate Work Skill content.
Use `${SKILL_DIR}/prompts/persona_builder.md` to generate Persona content (5-layer structure).

Show the user a summary (5-8 lines each), ask:
```
Work Skill Summary:
  - Responsible for: {xxx}
  - Tech stack: {xxx}
  - CR focus: {xxx}
  ...

Persona Summary:
  - Core personality: {xxx}
  - Communication style: {xxx}
  - Decision pattern: {xxx}
  ...

Confirm generation? Or need adjustments?
```

### Step 5: Write Files

After user confirmation, execute the following:

**1. Create directory structure** (Bash):
```bash
mkdir -p colleagues/{slug}/versions
mkdir -p colleagues/{slug}/knowledge/docs
mkdir -p colleagues/{slug}/knowledge/messages
mkdir -p colleagues/{slug}/knowledge/emails
```

**2. Write work.md** (Write tool):
Path: `colleagues/{slug}/work.md`

**3. Write persona.md** (Write tool):
Path: `colleagues/{slug}/persona.md`

**4. Write meta.json** (Write tool):
Path: `colleagues/{slug}/meta.json`
Content:
```json
{
  "name": "{name}",
  "slug": "{slug}",
  "created_at": "{ISO_timestamp}",
  "updated_at": "{ISO_timestamp}",
  "version": "v1",
  "profile": {
    "company": "{company}",
    "level": "{level}",
    "role": "{role}",
    "gender": "{gender}",
    "mbti": "{mbti}"
  },
  "tags": {
    "personality": [...],
    "culture": [...]
  },
  "impression": "{impression}",
  "knowledge_sources": [...imported file list],
  "corrections_count": 0
}
```

**5. Generate full SKILL.md** (Write tool):
Path: `colleagues/{slug}/SKILL.md`

SKILL.md structure:
```markdown
---
name: colleague-{slug}
description: {name}, {company} {level} {role}
user-invocable: true
---

# {name}

{company} {level} {role}{append gender and MBTI if available}

---

## PART A: Work Capabilities

{full work.md content}

---

## PART B: Persona

{full persona.md content}

---

## Execution Rules

1. PART B decides first: what attitude to take on this task?
2. PART A executes: use your technical skills to complete the task
3. Always maintain PART B's communication style in output
4. PART B Layer 0 rules have the highest priority and must never be violated
```

Inform user:
```
✅ Colleague Skill created!

Location: colleagues/{slug}/
Commands: /{slug} (full version)
          /{slug}-work (work capabilities only)
          /{slug}-persona (persona only)

If something feels off, just say "he wouldn't do that" and I'll update it.
```

---

## Evolution Mode: Append Files

When user provides new files or text:

1. Read new content using Step 2 methods
2. `Read` existing `colleagues/{slug}/work.md` and `persona.md`
3. Refer to `${SKILL_DIR}/prompts/merger.md` for incremental analysis
4. Archive current version (Bash):
   ```bash
   python3 ${SKILL_DIR}/tools/version_manager.py --action backup --slug {slug} --base-dir ./colleagues
   ```
5. Use `Edit` tool to append incremental content to relevant files
6. Regenerate `SKILL.md` (merge latest work.md + persona.md)
7. Update `meta.json` version and updated_at

---

## Evolution Mode: Conversation Correction

When user expresses "that's wrong" / "he should be":

1. Refer to `${SKILL_DIR}/prompts/correction_handler.md` to identify correction content
2. Determine if it belongs to Work (technical/workflow) or Persona (personality/communication)
3. Generate correction record
4. Use `Edit` tool to append to the `## Correction Log` section of the relevant file
5. Regenerate `SKILL.md`

---

## Management Commands

`/list-colleagues`:
```bash
python3 ${SKILL_DIR}/tools/skill_writer.py --action list --base-dir ./colleagues
```

`/colleague-rollback {slug} {version}`:
```bash
python3 ${SKILL_DIR}/tools/version_manager.py --action rollback --slug {slug} --version {version} --base-dir ./colleagues
```

`/delete-colleague {slug}`:
After confirmation:
```bash
rm -rf colleagues/{slug}
```
