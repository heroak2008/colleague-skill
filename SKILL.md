---
name: create-shadow
description: "通过对话记录和文章蒸馏自己的使用习惯与个人风格，生成影分身 Skill，帮助本体回答问题和写文章。| Distill your own habits and style from chat logs and writings into a shadow-clone Skill that answers questions and writes articles on your behalf."
argument-hint: "[shadow-codename-or-slug]"
version: "2.0.0"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, computer
---

> **Language / 语言**: This skill supports both English and Chinese. Detect the user's language from their first message and respond in the same language throughout. Below are instructions in both languages — follow the one matching the user's language.
>
> 本 Skill 支持中英文。根据用户第一条消息的语言，全程使用同一语言回复。下方提供了两种语言的指令，按用户语言选择对应版本执行。

> **Platform / 平台兼容性**：本 Skill 兼容以下 AI 编程环境：
> - **Claude Code**：`${CLAUDE_SKILL_DIR}` 由平台自动注入，直接使用。
> - **OpenCode**：`${OPENCODE_SKILL_DIR}` 由平台注入；若未注入，请在 shell 中执行 `export SKILL_DIR=~/.opencode/skills/create-shadow`。
> - **Codex CLI**：请在 shell 中执行 `export SKILL_DIR=~/.codex/skills/create-shadow`，或参见 `AGENTS.md`。
> - **通用环境**：请将 `SKILL_DIR` 设置为本项目的安装目录，工具脚本均在 `${SKILL_DIR}/tools/` 下。
>
> **Platform compatibility**: This Skill works with the following AI coding environments:
> - **Claude Code**: `${CLAUDE_SKILL_DIR}` is injected automatically — use as-is.
> - **OpenCode**: `${OPENCODE_SKILL_DIR}` is injected by the platform; if not set, run `export SKILL_DIR=~/.opencode/skills/create-shadow` in your shell.
> - **Codex CLI**: Run `export SKILL_DIR=~/.codex/skills/create-shadow` in your shell, or see `AGENTS.md`.
> - **Generic**: Set `SKILL_DIR` to the directory where this project is installed; tool scripts live under `${SKILL_DIR}/tools/`.

# 影分身.skill 创建器

## 触发条件

当用户说以下任意内容时启动：
- `/create-shadow`
- "帮我创建一个影分身"
- "我想蒸馏自己"
- "新建影分身"
- "给我做一个自己的 skill"

当用户对已有影分身 Skill 说以下内容时，进入进化模式：
- "我有新文件" / "追加"
- "这不对" / "我不会这样" / "我应该是"
- `/update-shadow {slug}`

当用户说 `/list-shadows` 时列出所有已生成的影分身。

当用户说 `/use {slug}` 时，激活对应的影分身 Skill，进入对话模式：
- AI 加载该影分身的知识层 + 风格层
- 用户发送带有发送人信息的消息，AI 自动判断场景类型并切换对应说话风格

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
| 解析本地 Markdown 文档 | `Bash` → `python3 ${SKILL_DIR}/tools/markdown_parser.py` |
| 写入/更新 Skill 文件 | `Write` / `write_file` / `Edit` 工具 |
| 版本管理 | `Bash` → `python3 ${SKILL_DIR}/tools/version_manager.py` |
| 列出已有 Skill | `Bash` → `python3 ${SKILL_DIR}/tools/skill_writer.py --action list` |
| 加载对话上下文（运行时） | `Bash` → `python3 ${SKILL_DIR}/tools/input_loader.py` |
| 习惯活跃度检查 | `Bash` → `python3 ${SKILL_DIR}/tools/habit_manager.py` |

**基础目录**：Skill 文件写入 `./shadows/{slug}/`（相对于本项目目录）。
如需改为全局路径，用 `--base-dir ~/.opencode/skills/shadows`（OpenCode）或 `--base-dir ~/.codex/skills/shadows`（Codex）。

---

## 主流程：创建新影分身 Skill

### Step 1：基础信息录入（3 个问题）

参考 `${SKILL_DIR}/prompts/intake.md` 的问题序列，只问 3 个问题：

1. **影分身代号**（必填）
2. **背景信息**（一句话：职业、领域、写作方向，想到什么写什么）
   - 示例：`后端工程师 技术博主 专注分布式系统`
3. **风格画像**（一句话：MBTI、个性标签、领域文化、自我印象）
   - 示例：`INTJ 直接犀利 字节味 写文章喜欢结论先行然后怼反方`

除代号外均可跳过。收集完后汇总确认再进入下一步。

### Step 2：原材料导入

询问用户提供原材料，展示三种方式供选择：

```
原材料怎么提供？

  [A] 导入 TXT 聊天记录（推荐）
      提供你自己的聊天记录文件或目录，自动解析并提取你的发言
      支持多文件、多人对话，自动过滤噪声消息

  [B] 直接粘贴内容
      把文字复制进来（适合文章、笔记、少量文本）

  [C] 导入本地 Markdown 文档（文章/笔记/技术文档）
      提供你写过的 .md 文件或目录，自动分析你的文档写作习惯和风格
      分析结果将用于影分身生成文章时仿照你的风格

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

2. **列出说话人**（可选，帮用户确认自己的名字写法）：
```bash
python3 ${SKILL_DIR}/tools/txt_parser.py \
  --input {path_or_dir} \
  --list-speakers
```

3. **提取用户自己的消息**：

   首先询问用户这份记录是和谁的对话：
   ```
   这份记录是和谁的对话？
     [1] 领导 / 上级（对方地位高于你）
     [2] 同级 / 平级（对方和你地位相当）
     [3] 后辈 / 下属（对方是你带的人）
     [4] 混合（文件里有多种关系，跳过分类）
   ```

   根据用户选择，将对应关系类型传入 `--relation` 参数（选 [4] 则不传）：
   ```bash
   # 示例：跟领导的对话（提取你的发言）
   python3 ${SKILL_DIR}/tools/txt_parser.py \
     --input {path_or_dir} \
     --target "{your_name}" \
     --relation superior \
     --output /tmp/txt_parsed_superior.txt

   # 示例：跟平级的对话
   python3 ${SKILL_DIR}/tools/txt_parser.py \
     --input {path_or_dir} \
     --target "{your_name}" \
     --relation peer \
     --output /tmp/txt_parsed_peer.txt

   # 示例：跟后辈的对话
   python3 ${SKILL_DIR}/tools/txt_parser.py \
     --input {path_or_dir} \
     --target "{your_name}" \
     --relation junior \
     --output /tmp/txt_parsed_junior.txt

   # 示例：混合文件（不传 --relation）
   python3 ${SKILL_DIR}/tools/txt_parser.py \
     --input {path_or_dir} \
     --target "{your_name}" \
     --output /tmp/txt_parsed.txt
   ```
   支持多个路径：`--input chat1.txt chat2.txt ./chats/`
   支持不递归目录：`--no-recursive`

4. 读取提取结果：
```
Read /tmp/txt_parsed.txt
```

**常见问题**：
- 如果你的消息数 < 10，工具会自动提示，建议补充更多记录或结合手动描述
- 如果找不到你的名字，先用 `--list-speakers` 查看文件中实际的说话人名称
- 乱码/编码问题：工具自动尝试 UTF-8 / GBK / GB18030 / Big5 等编码

---

#### 方式 B：直接粘贴

用户粘贴的内容（文章、笔记、聊天片段）直接作为文本原材料，无需调用任何工具。

---

#### 方式 C：导入本地 Markdown 文档

**支持的格式**：`.md` / `.markdown` 文件（单个文件或目录，目录默认递归扫描）

**步骤**：

1. 用户提供 Markdown 文件路径或目录路径

2. **解析文档结构**：
```bash
python3 ${SKILL_DIR}/tools/markdown_parser.py \
  --input {path_or_dir} \
  --summary
```
> 输出：文档写作风格摘要（供后续 LLM 分析使用）

3. 读取摘要输出，进入 Step 3 的**线路 C（文档写作风格）**分析。

4. 若需同时输出 JSON 详情（可选）：
```bash
python3 ${SKILL_DIR}/tools/markdown_parser.py \
  --input {path_or_dir} \
  --output /tmp/md_analysis.json
```

**常见问题**：
- 文档数 < 3 篇时，工具会在摘要中自动提示，建议补充更多文档
- 支持多路径输入：`--input a.md b.md ./docs/`
- 目录不递归时加 `--no-recursive`
- 自动处理 UTF-8 / UTF-8-BOM / GBK / GB18030 / Big5 编码

---

如果用户说"没有文件"或"跳过"，仅凭 Step 1 的手动信息生成 Skill。

### Step 3：分析原材料

将收集到的所有原材料和用户填写的基础信息汇总，按以下三条线分析：

**线路 A（知识与能力）**：
- 参考 `${SKILL_DIR}/prompts/work_analyzer.md` 中的提取维度
- 提取：专业领域、知识体系、思维框架、写作习惯、输出风格偏好
- 根据职业类型重点提取（技术/产品/研究/写作不同侧重）

**线路 B（说话风格）**：
- 参考 `${SKILL_DIR}/prompts/persona_analyzer.md` 中的提取维度
- 将用户填写的标签翻译为具体行为规则（参见标签翻译表）
- 从原材料中提取：表达习惯、决策模式、人际行为

**线路 C（文档写作风格）**：
- 仅在用户通过方式 C 导入了 Markdown 文档时触发
- 参考 `${SKILL_DIR}/prompts/doc_style_analyzer.md` 中的分析维度
- 输入：`markdown_parser.py --summary` 的输出 + 原始 Markdown 文档内容
- 提取：文章结构偏好、格式习惯、信息密度、语气风格、典型句式
- 分析结果将写入 `work.md` 的"文档写作风格"区块（参见 `doc_style_builder.md`）

### Step 4：生成并预览

参考 `${SKILL_DIR}/prompts/work_builder.md` 生成知识与能力内容。
参考 `${SKILL_DIR}/prompts/persona_builder.md` 生成说话风格内容（5 层结构）。
若有 Markdown 文档语料，参考 `${SKILL_DIR}/prompts/doc_style_builder.md` 生成文档写作风格区块。

向用户展示摘要（各 5-8 行），询问：
```
知识与能力摘要：
  - 专业领域：{xxx}
  - 核心知识：{xxx}
  - 写作风格：{xxx}
  ...

说话风格摘要：
  - 核心特点：{xxx}
  - 表达习惯：{xxx}
  - 决策模式：{xxx}
  ...

{若有 Markdown 文档语料：}
文档写作风格摘要：
  - 文章结构：{xxx}
  - 格式偏好：{xxx}
  - 典型开篇：{xxx}
  ...

确认生成？还是需要调整？
```

### Step 5：写入文件

用户确认后，执行以下写入操作：

**1. 创建目录结构**（用 Bash）：
```bash
mkdir -p shadows/{slug}/versions
mkdir -p shadows/{slug}/knowledge/docs
mkdir -p shadows/{slug}/knowledge/messages
mkdir -p shadows/{slug}/knowledge/articles
mkdir -p shadows/{slug}/input/{正式/日常/专业}
```

**2. 写入 work.md**（用 Write 工具）：
路径：`shadows/{slug}/work.md`

**3. 写入 persona.md**（用 Write 工具）：
路径：`shadows/{slug}/persona.md`

**4. 写入 meta.json**（用 Write 工具）：
路径：`shadows/{slug}/meta.json`
内容：
```json
{
  "name": "{name}",
  "slug": "{slug}",
  "created_at": "{ISO时间}",
  "updated_at": "{ISO时间}",
  "version": "v1",
  "profile": {
    "profession": "{职业}",
    "domains": ["{领域1}", "{领域2}"],
    "writing_direction": "{写作方向}",
    "mbti": "{mbti}"
  },
  "tags": {
    "personality": [...],
    "culture": []
  },
  "impression": "{自我印象}",
  "knowledge_sources": [...已导入文件列表],
  "markdown_sources": [...已导入 Markdown 文档列表，无则为空数组],
  "relation_sources": {
    "superior": [...跟领导的聊天文件],
    "peer": [...跟平级的聊天文件],
    "junior": [...跟后辈的聊天文件]
  },
  "corrections_count": 0
}
```

**5. 生成完整 SKILL.md**（用 Write 工具）：
路径：`shadows/{slug}/SKILL.md`

SKILL.md 结构：
```markdown
---
name: shadow-{slug}
description: {name} 的影分身，{职业} / {领域}
user-invocable: true
---

# {name}（影分身）

{职业} · {领域} · {写作方向（若有）}

---

## PART A：知识与能力

{work.md 全部内容}

---

## PART B：说话风格

{persona.md 全部内容}

---

## 运行规则

1. 先由 PART B 判断：用什么态度接这个任务？
2. 再由 PART A 执行：用你的知识体系完成任务
3. 输出时始终保持 PART B 的表达风格
4. PART B Layer 0 的规则优先级最高，任何情况下不得违背

### 回答问题

收到问题时：
- 知识范围内：用 PART A「如何回答问题」中定义的方式给出结论
- 知识范围外：用 PART B 中描述的方式应对（说明不了解、给出方向性判断、或推荐其他资源）
- 无论哪种情况，回答风格始终保持 PART B Layer 2 的表达习惯

### 写文章

收到写作任务时：
- 参考 `${SKILL_DIR}/prompts/doc_generator.md` 中的风格约束执行
- 若 work.md 有"文档写作风格"区块：严格按照其中的结构、格式、句式约束生成
- 若无该区块：按照 PART A 的「写作习惯」和「输出格式偏好」生成
- 全程用 PART B Layer 2 的表达风格和口吻
- 结构、例子、观点风格都要像你

**触发写作模式的用户输入**（包括但不限于）：
- 帮我写一篇关于 `{主题}` 的文章
- 写个 `{主题}` 的技术文档 / 教程
- 用你的风格写篇 `{主题}` 的文章
- 仿照你的写法写一篇关于 `{主题}` 的
- 以你的口吻写一篇
```

**6. 初始化习惯追踪档案**（用 Bash）：
```bash
python3 ${SKILL_DIR}/tools/habit_manager.py init \
  --slug {slug} --base-dir ./shadows
```
> 此步骤从 persona.md Layer 2 提取口头禅 / 高频词，写入 `habits.json`，用于追踪说话习惯的活跃状态。
> Layer 0（核心性格）不受此规则影响。

告知用户：
```
✅ 影分身 Skill 已创建！

文件位置：shadows/{slug}/
触发词：/{slug}（完整版）
        /{slug}-work（仅知识与能力）
        /{slug}-persona（仅说话风格）

如果用起来感觉哪里不像你，直接说"我不会这样"，我来更新。
```

---

## 进化模式：追加文件

用户提供新文件或文本时：

1. 按 Step 2 的方式读取新内容
   - 若是 TXT 聊天记录：**同样询问场景类型**（正式/日常/专业）
   - 若是 Markdown 文档：调用 `markdown_parser.py --summary` 生成摘要，进入线路 C 增量分析
2. 用 `Read` 读取现有 `shadows/{slug}/work.md` 和 `persona.md`
3. 读取 `shadows/{slug}/meta.json`，查看 `relation_sources`，判断哪种场景类型目前**尚无**原材料——如有缺失，在更新 persona 时重点补充该场景下的风格描述
4. 参考 `${SKILL_DIR}/prompts/merger.md` 分析增量内容
   - 若新内容为 Markdown 文档，同时执行 Step 3b（文档写作风格区块增量更新）
5. 存档当前版本（用 Bash）：
   ```bash
   python3 ${SKILL_DIR}/tools/version_manager.py --action backup --slug {slug} --base-dir ./shadows
   ```
6. 用 `Edit` 工具追加增量内容到对应文件
7. 重新生成 `SKILL.md`（合并最新 work.md + persona.md）
8. 更新 `meta.json` 的 version、updated_at、`relation_sources`，以及 `markdown_sources`（若有新增 Markdown 文档）
9. 扫描聊天记录，更新习惯活跃状态（用 Bash）：
   ```bash
   python3 ${SKILL_DIR}/tools/habit_manager.py scan \
     --slug {slug} --base-dir ./shadows
   ```
   > 此步骤会检查 Layer 2 的口头禅 / 高频词在最近 input/ 聊天记录中是否仍然出现，超过 90 天未出现的习惯将在下次使用时被提示降低权重。

---

## 进化模式：对话纠正

用户表达"不对"/"我应该是"时：

1. 参考 `${SKILL_DIR}/prompts/correction_handler.md` 识别纠正内容
2. 判断属于知识层（领域知识/写作方法）还是风格层（说话方式/人际行为）
3. 生成 correction 记录
4. 用 `Edit` 工具追加到对应文件的 `## Correction 记录` 节
5. 重新生成 `SKILL.md`

---

## 管理命令

`/list-shadows`：
```bash
python3 ${SKILL_DIR}/tools/skill_writer.py --action list --base-dir ./shadows
```

`/shadow-rollback {slug} {version}`：
```bash
python3 ${SKILL_DIR}/tools/version_manager.py --action rollback --slug {slug} --version {version} --base-dir ./shadows
```

`/delete-shadow {slug}`：
确认后执行：
```bash
rm -rf shadows/{slug}
```

---

## 对话上下文：文件放置 + 自动加载

### 目录结构

每个影分身 Skill 下有一个 `input/` 目录，包含 3 个子目录：

```
shadows/{slug}/input/
├── 正式/    # 正式场合的对话记录（每人或每个场景一个 .txt）
├── 日常/    # 日常对话记录（朋友、熟人）
└── 专业/    # 专业/技术场景对话记录
```

用户**只需把导出的 TXT 放到对应目录**，无需任何命令。
场景类型由放置的目录决定。

### `/use {slug}` — 激活影分身并进入对话模式

```
/use my-shadow
```

执行步骤：
1. 读取 `shadows/{slug}/SKILL.md`（加载知识层 + 风格层）
2. 扫描 `input/` 目录，了解已有记录：
   ```bash
   python3 ${SKILL_DIR}/tools/input_loader.py scan \
     --slug {slug} --base-dir ./shadows
   ```
3. 告知用户激活成功，并显示已有记录概况：
   ```
   ✅ 已激活影分身：{name}

   已加载对话记录：
     正式：{n} 个文件  日常：{n} 个文件  专业：{n} 个文件

   现在可以直接对话，影分身会用你的风格和知识体系回答。
   ```

---
---

# English Version

# Shadow-Clone.skill Creator

## Trigger Conditions

Activate when the user says any of the following:
- `/create-shadow`
- "Help me create a shadow clone"
- "I want to distill myself"
- "New shadow clone"
- "Make a skill for me"

Enter evolution mode when the user says:
- "I have new files" / "append"
- "That's wrong" / "I wouldn't do that" / "I should actually be"
- `/update-shadow {slug}`

List all generated shadow clones when the user says `/list-shadows`.

When the user says `/use {slug}`, activate the shadow clone Skill and enter conversation mode.

---

## Tool Usage Rules

This Skill is compatible with Claude Code, OpenCode, Codex CLI, and similar AI coding environments:

> **Directory variable**: `${SKILL_DIR}` maps to each platform's injected variable:
> - Claude Code → `${CLAUDE_SKILL_DIR}`
> - OpenCode → `${OPENCODE_SKILL_DIR}`
> - Codex CLI / others → set manually by the user

| Task | Tool |
|------|------|
| Read PDF documents | `Read` / `read_file` tool |
| Read image screenshots | `Read` / `read_file` tool |
| Read MD/TXT files | `Read` / `read_file` tool |
| Parse TXT chat logs (recommended) | `Bash` → `python3 ${SKILL_DIR}/tools/txt_parser.py` |
| Parse local Markdown documents | `Bash` → `python3 ${SKILL_DIR}/tools/markdown_parser.py` |
| Write/update Skill files | `Write` / `write_file` / `Edit` tool |
| Version management | `Bash` → `python3 ${SKILL_DIR}/tools/version_manager.py` |
| List existing Skills | `Bash` → `python3 ${SKILL_DIR}/tools/skill_writer.py --action list` |
| Load conversation context (runtime) | `Bash` → `python3 ${SKILL_DIR}/tools/input_loader.py` |
| Habit activity check | `Bash` → `python3 ${SKILL_DIR}/tools/habit_manager.py` |

**Base directory**: Skill files are written to `./shadows/{slug}/` (relative to the project directory).

---

## Main Flow: Create a New Shadow Clone Skill

### Step 1: Basic Info Collection (3 questions)

Refer to `${SKILL_DIR}/prompts/intake.md`. Only ask 3 questions:

1. **Shadow clone codename** (required)
2. **Background** (one sentence: profession, domains, writing focus — say whatever comes to mind)
   - Example: `backend engineer, tech blogger, distributed systems`
3. **Style profile** (one sentence: MBTI, personality traits, culture, self-description)
   - Example: `INTJ direct and sharp ByteDance-style I like to lead with conclusions then argue against the opposing view`

Everything except the codename can be skipped. Summarize and confirm before moving on.

### Step 2: Source Material Import

Ask the user how they'd like to provide materials:

```
How would you like to provide source materials?

  [A] Import TXT chat logs (recommended)
      Provide your own chat log file(s) or a directory; auto-parse and extract your messages
      Supports multiple files, multi-person conversations, and automatic noise filtering

  [B] Paste Text
      Paste text directly (good for articles, notes, small amounts of text)

  [C] Import local Markdown documents (articles / notes / technical docs)
      Provide .md files or a directory you've written; auto-analyze your document writing style
      Results are used by the shadow clone when generating articles in your style

Can mix and match, or skip entirely (generate from manual info only).
```

---

#### Option A: Import TXT Chat Logs (Recommended)

**Steps**:

1. User provides file path(s) or directory

2. **List speakers** (optional — confirm your own name spelling):
```bash
python3 ${SKILL_DIR}/tools/txt_parser.py \
  --input {path_or_dir} \
  --list-speakers
```

3. **Extract your own messages** with relation type:
```bash
python3 ${SKILL_DIR}/tools/txt_parser.py \
  --input {path_or_dir} \
  --target "{your_name}" \
  --relation peer \
  --output /tmp/txt_parsed.txt
```

4. Read the result: `Read /tmp/txt_parsed.txt`

---

#### Option B: Paste Text

User-pasted content (articles, notes, chat excerpts) is used directly. No tools needed.

---

#### Option C: Import Local Markdown Documents

**Supported formats**: `.md` / `.markdown` files (single file or directory; directories are scanned recursively by default)

**Steps**:

1. User provides Markdown file path(s) or directory

2. **Parse document structure**:
```bash
python3 ${SKILL_DIR}/tools/markdown_parser.py \
  --input {path_or_dir} \
  --summary
```
> Output: A human-readable writing style summary for LLM analysis

3. Read the summary output, then proceed to **Track C (Document Writing Style)** in Step 3.

4. Optionally export full JSON details:
```bash
python3 ${SKILL_DIR}/tools/markdown_parser.py \
  --input {path_or_dir} \
  --output /tmp/md_analysis.json
```

**Notes**:
- If fewer than 3 documents are provided, the tool will warn in the summary
- Multiple paths supported: `--input a.md b.md ./docs/`
- Disable recursive scanning: `--no-recursive`
- Encoding auto-detection: UTF-8, GBK, GB18030, Big5

---

### Step 3: Analyze Source Material

Analyze all collected materials along three tracks:

**Track A (Knowledge & Capabilities)**:
- Refer to `${SKILL_DIR}/prompts/work_analyzer.md`
- Extract: domains, knowledge base, mental models, writing habits, output format preferences

**Track B (Speaking Style)**:
- Refer to `${SKILL_DIR}/prompts/persona_analyzer.md`
- Translate tags into concrete behavior rules
- Extract: expression habits, decision patterns, interpersonal behavior

**Track C (Document Writing Style)**:
- Only triggered when the user imports Markdown documents via Option C
- Refer to `${SKILL_DIR}/prompts/doc_style_analyzer.md`
- Input: `markdown_parser.py --summary` output + raw Markdown content
- Extract: structure preferences, format habits, information density, tone, typical sentence patterns
- Results are written to the "Document Writing Style" section in `work.md`

### Step 4: Generate and Preview

Use `${SKILL_DIR}/prompts/work_builder.md` for knowledge content.
Use `${SKILL_DIR}/prompts/persona_builder.md` for style content (5-layer structure).
If Markdown documents were imported, use `${SKILL_DIR}/prompts/doc_style_builder.md` for the document writing style section.

Show user a summary and ask for confirmation.

### Step 5: Write Files

After confirmation, write to `shadows/{slug}/`.

Inform user:
```
✅ Shadow clone Skill created!

Location: shadows/{slug}/
Commands: /{slug} (full version)
          /{slug}-work (knowledge & capabilities only)
          /{slug}-persona (speaking style only)

If something feels off, just say "I wouldn't do that" and I'll update it.
```

---

## Evolution Mode: Append Files

When user provides new files or text:

1. Read new content using Step 2 methods
   - If TXT chat logs: ask for relation type (formal / casual / professional)
   - If Markdown documents: run `markdown_parser.py --summary`, proceed with Track C incremental analysis
2. `Read` existing `shadows/{slug}/work.md` and `persona.md`
3. Refer to `${SKILL_DIR}/prompts/merger.md` for incremental analysis
   - If new content is Markdown documents, also execute Step 3b (document style section incremental update)
4. Archive current version, apply edits, regenerate `SKILL.md`
5. Update `meta.json`: version, updated_at, `relation_sources`, and `markdown_sources` (if new Markdown files added)

---

## Evolution Mode: Conversation Correction

When user says "that's wrong" / "I should actually be":

1. Refer to `${SKILL_DIR}/prompts/correction_handler.md`
2. Determine if it belongs to knowledge (domains/writing) or style (communication/behavior)
3. Generate and append correction record
4. Regenerate `SKILL.md`

---

## Management Commands

`/list-shadows`:
```bash
python3 ${SKILL_DIR}/tools/skill_writer.py --action list --base-dir ./shadows
```

`/shadow-rollback {slug} {version}`:
```bash
python3 ${SKILL_DIR}/tools/version_manager.py --action rollback --slug {slug} --version {version} --base-dir ./shadows
```

`/delete-shadow {slug}`:
After confirmation:
```bash
rm -rf shadows/{slug}
```
