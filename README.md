<div align="center">

# 同事.skill

> *"你们搞大模型的就是码奸，你们已经害死前端兄弟了，还要害死后端兄弟，测试兄弟，运维兄弟，害死网安兄弟，害死ic兄弟，最后害死自己害死全人类"*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)](https://claude.ai/code)
[![OpenCode](https://img.shields.io/badge/OpenCode-Compatible-blue)](https://github.com/sst/opencode)
[![Codex CLI](https://img.shields.io/badge/Codex%20CLI-Compatible-green)](https://github.com/openai/codex)
[![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)](https://agentskills.io)

<br>

你的同事跳槽了，留下大量的文档没人维护？<br>
你的实习生离职了，只留下空荡的工位和烂尾的项目？<br>
你的导师毕业了，带走了所有的经验和上下文？<br>
你的搭档转岗了，熟悉的默契一夜之间归零？<br>
你的前任交接了，三页文档想概括三年的积累？<br>

**将冰冷的离别化为温暖的 Skill，欢迎加入赛博永生！**

<br>

提供同事的 **TXT 聊天记录**（支持多文件、多人对话）或手动描述<br>
生成一个**真正能替他工作的 AI Skill**<br>
用他的技术规范写代码，用他的语气回答问题，知道他什么时候会甩锅

[数据来源](#支持的数据来源) · [安装](#安装) · [使用](#使用) · [效果示例](#效果示例) · [详细安装说明](INSTALL.md) · [**English**](README_EN.md)

</div>

---

### 🌟 同系列项目：[前任.skill](https://github.com/titanwings/ex-skill)

> 根据大家的 issue 反馈，更新了一版 **前任.skill**！现已支持：
>
> - **微信聊天记录全自动导入**（Windows / macOS，桌面端登录即可，无需任何配置）
> - **iMessage 全自动提取**（macOS 用户）
> - **完整星盘解读**（太阳/月亮/上升/金星/火星/水星 × 12 星座）
> - **MBTI 16 型 + 认知功能**、九型人格、依恋风格全支持
> - 支持所有性别认同与关系类型
>
> 同事跑了用 **同事.skill**，前任跑了用 **[前任.skill](https://github.com/titanwings/ex-skill)**，赛博永生一条龙 🌟🌟🌟
>
> 觉得有意思的话，给两个项目都点个 Star 吧！

---

## 支持的数据来源

| 来源 | 支持 | 说明 |
|------|:----:|------|
| **TXT 聊天记录**（推荐） | ✅ | 支持多文件、多人对话，自动识别并过滤目标同事发言 |
| 手动输入描述 | ✅ | 直接描述同事特点，无需任何文件 |
| PDF / 图片 / 截图 | ✅ | 直接上传给 AI 读取 |
| Markdown / 其他文本 | ✅ | 直接上传或粘贴 |

### 支持的 TXT 格式

\`\`\`
# 格式 1 — 带完整时间戳
2024-01-01 10:00:00 张三：消息内容

# 格式 2 — 仅日期
2024-01-01 张三：消息内容

# 格式 3 — 微信导出式（时间 / 发送人 / 内容各占一行）
2024-01-01 10:00:00
张三
消息内容

# 格式 4 — 无时间戳
张三：消息内容

# 格式 5 — Markdown 加粗
**张三**: 消息内容

# 格式 6 — 企业工号格式（制表符分隔）
张三(z00611745)	2026-01-04 15:58:23
消息内容
\`\`\`

多种格式混用同一文件也可以正常解析。

---

## 安装

### Claude Code

> **重要**：Claude Code 从 **git 仓库根目录** 的 `.claude/skills/` 查找 skill。请在正确的位置执行。

\`\`\`bash
# 安装到当前项目（在 git 仓库根目录执行）
mkdir -p .claude/skills
git clone https://github.com/heroak2008/colleague-skill .claude/skills/create-colleague

# 或安装到全局（所有项目都能用）
git clone https://github.com/heroak2008/colleague-skill ~/.claude/skills/create-colleague
\`\`\`

### OpenCode

\`\`\`bash
mkdir -p ~/.opencode/skills
git clone https://github.com/heroak2008/colleague-skill ~/.opencode/skills/create-colleague
# 设置目录变量（若平台未自动注入）
echo 'export SKILL_DIR="$HOME/.opencode/skills/create-colleague"' >> ~/.bashrc && source ~/.bashrc
\`\`\`

### Codex CLI（OpenAI Codex）

\`\`\`bash
mkdir -p ~/.codex/skills
git clone https://github.com/heroak2008/colleague-skill ~/.codex/skills/create-colleague
# 设置目录变量和 API Key
echo 'export SKILL_DIR="$HOME/.codex/skills/create-colleague"' >> ~/.bashrc
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.bashrc
source ~/.bashrc
\`\`\`

详见 [AGENTS.md](AGENTS.md) 了解 Codex 的完整使用说明。

### 依赖（可选）

\`\`\`bash
pip3 install -r requirements.txt
\`\`\`

---

## 使用

在 Claude Code / OpenCode 中输入：

\`\`\`
/create-colleague
\`\`\`

在 Codex CLI 中，将 `AGENTS.md` 作为系统指令载入，然后输入：

\`\`\`
/create-colleague
\`\`\`

按提示输入同事姓名、公司职级（如 `字节 2-1 算法工程师`）、性格标签，然后选择数据来源。所有字段均可跳过，仅凭描述也能生成。

完成后用 `/{slug}` 调用该同事 Skill。

### TXT 聊天记录导入示例

\`\`\`bash
# 解析单个文件，过滤目标同事的发言
python3 tools/txt_parser.py --input chat.txt --target "张三" --output /tmp/out.txt

# 解析整个目录（支持递归）
python3 tools/txt_parser.py --input ./chats/ --target "张三" --output /tmp/out.txt

# 解析多个文件
python3 tools/txt_parser.py --input chat1.txt chat2.txt --target "张三"

# 先列出识别到的说话人，再决定目标
python3 tools/txt_parser.py --input ./chats/ --list-speakers
\`\`\`

工具会自动：
- 识别多种 TXT 格式（混用也没问题）
- 过滤 `[图片]`、`[语音]`、撤回消息等噪声
- 自动探测 UTF-8 / GBK / GB18030 / Big5 编码
- 对消息进行分类（长消息 / 决策类 / 日常）以便 AI 优先分析重要内容
- 若目标同事消息过少，给出明确提示

### 管理命令

| 命令 | 说明 |
|------|------|
| `/list-colleagues` | 列出所有同事 Skill |
| `/{slug}` | 调用完整 Skill（Persona + Work） |
| `/{slug}-work` | 仅工作能力 |
| `/{slug}-persona` | 仅人物性格 |
| `/colleague-rollback {slug} {version}` | 回滚到历史版本 |
| `/delete-colleague {slug}` | 删除 |

---

## 效果示例

> 输入：`字节 2-1 后端工程师，INTJ，甩锅高手，字节范`

**场景一：Code Review**

\`\`\`
用户      ❯ 帮我看一下这个接口设计

同事.skill ❯ 等等，这个接口的 impact 是什么？背景没说清楚。
             （看完后）N+1 查询，改掉。返回结构用统一的
             {code, message, data}，这是规范，不用问为什么。
\`\`\`

**场景二：甩锅**

\`\`\`
用户      ❯ 这个 bug 是你引入的吧

同事.skill ❯ 上线时间对上了吗？那个需求改了好几个地方，还有其他变更。
\`\`\`

---

## 功能特性

### 生成的 Skill 结构

每个同事 Skill 由两部分组成，共同驱动输出：

| 部分 | 内容 |
|------|------|
| **Part A — Work Skill** | 负责系统、技术规范、工作流程、输出偏好、经验知识库 |
| **Part B — Persona** | 5 层性格结构：硬规则 → 身份 → 表达风格 → 决策模式 → 人际行为 |

运行逻辑：`接到任务 → Persona 判断态度 → Work Skill 执行 → 用他的语气输出`

### 支持的标签

**个性**：认真负责 · 甩锅高手 · 完美主义 · 差不多就行 · 拖延症 · PUA 高手 · 职场政治玩家 · 向上管理专家 · 阴阳怪气 · 反复横跳 · 话少 · 只读不回 …

**企业文化**：字节范 · 阿里味 · 腾讯味 · 华为味 · 百度味 · 美团味 · 第一性原理 · OKR 狂热者 · 大厂流水线 · 创业公司派

**职级支持**：字节 2-1~3-3+ · 阿里 P5~P11 · 腾讯 T1~T4 · 百度 T5~T9 · 美团 P4~P8 · 华为 13~21 级 · 网易 · 京东 · 小米 …

### 进化机制

- **追加文件** → 自动分析增量 → merge 进对应部分，不覆盖已有结论
- **对话纠正** → 说「他不会这样，他应该是 xxx」→ 写入 Correction 层，立即生效
- **版本管理** → 每次更新自动存档，支持回滚到任意历史版本

---

## 项目结构

本项目遵循 [AgentSkills](https://agentskills.io) 开放标准，整个 repo 就是一个 skill 目录：

\`\`\`
create-colleague/
├── SKILL.md              # skill 入口（官方 frontmatter）
├── prompts/              # Prompt 模板
│   ├── intake.md         #   对话式信息录入
│   ├── work_analyzer.md  #   工作能力提取
│   ├── persona_analyzer.md #  性格行为提取（含标签翻译表）
│   ├── work_builder.md   #   work.md 生成模板
│   ├── persona_builder.md #   persona.md 五层结构模板
│   ├── merger.md         #   增量 merge 逻辑
│   └── correction_handler.md # 对话纠正处理
├── tools/                # Python 工具
│   ├── txt_parser.py             # TXT 聊天记录解析（主要入口）
│   ├── skill_writer.py           # Skill 文件管理
│   └── version_manager.py        # 版本存档与回滚
├── tests/                # 单元测试
│   └── test_txt_parser.py
├── colleagues/           # 生成的同事 Skill（gitignored）
├── docs/PRD.md
├── requirements.txt
└── LICENSE
\`\`\`

---

## 注意事项

- **原材料质量决定 Skill 质量**：聊天记录 + 长文档 > 仅手动描述
- 建议优先收集：他**主动写的**长文 > **决策类回复** > 日常消息
- TXT 聊天记录至少建议 30 条以上的目标同事消息，才能生成有参考价值的 Skill
- 目前还是一个 demo 版本，如果有 bug 请多多提 issue！

---

## Star History

<a href="https://www.star-history.com/?repos=titanwings%2Fcolleague-skill&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=titanwings/colleague-skill&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=titanwings/colleague-skill&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=titanwings/colleague-skill&type=date&legend=top-left" />
 </picture>
</a>

---

<div align="center">

MIT License © [titanwings](https://github.com/titanwings)


</div>
