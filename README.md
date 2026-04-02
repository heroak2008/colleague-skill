<div align="center">

# 影分身.skill

> *"本体太忙了，派个影分身出去帮我搞定吧"*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)](https://claude.ai/code)
[![OpenCode](https://img.shields.io/badge/OpenCode-Compatible-blue)](https://github.com/sst/opencode)
[![Codex CLI](https://img.shields.io/badge/Codex%20CLI-Compatible-green)](https://github.com/openai/codex)
[![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)](https://agentskills.io)

<br>

你回答过太多重复问题，每次都要从头解释一遍？<br>
你写文章总是卡在"怎么开头"，明明脑子里有东西就是倒不出来？<br>
你有大量聊天记录、笔记、文档，里面藏着你多年的判断和思路？<br>
你希望有个懂你的 AI，不是通用助手，而是你自己的分身？<br>

**把自己的思维方式、说话习惯、知识体系蒸馏成 AI 影分身——**<br>
**让影分身代替本体回答问题、写文章、处理日常。**

<br>

提供你的 **TXT 聊天记录、笔记、文章**（支持多文件）或手动描述<br>
生成一个**真正像你的 AI Skill**<br>
用你的知识框架回答问题，用你的语气写文章，知道你什么时候会直接说"不"

[数据来源](#支持的数据来源) · [安装](#安装) · [使用](#使用) · [效果示例](#效果示例) · [详细安装说明](INSTALL.md) · [**English**](README_EN.md)

</div>

---

### 🌟 同系列项目：[前任.skill](https://github.com/titanwings/ex-skill)

> 想把前任也蒸馏成 AI？试试 **[前任.skill](https://github.com/titanwings/ex-skill)**！
>
> 自己跑了用 **影分身.skill**，前任跑了用 **[前任.skill](https://github.com/titanwings/ex-skill)**，赛博永生一条龙 🌟🌟🌟
>
> 觉得有意思的话，给两个项目都点个 Star 吧！

---

## 支持的数据来源

| 来源 | 支持 | 说明 |
|------|:----:|------|
| **TXT 聊天记录**（推荐） | ✅ | 支持多文件、多人对话，自动识别并提取你自己的发言 |
| 个人笔记 / 文章 / Markdown | ✅ | 直接上传，提取你的知识体系和写作风格 |
| 手动输入描述 | ✅ | 直接描述自己的特点，无需任何文件 |
| PDF / 图片 / 截图 | ✅ | 直接上传给 AI 读取 |

### 支持的 TXT 格式

```
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
```

多种格式混用同一文件也可以正常解析。

---

## 安装

### Claude Code

> **重要**：Claude Code 从 **git 仓库根目录** 的 `.claude/skills/` 查找 skill。请在正确的位置执行。

```bash
# 安装到当前项目（在 git 仓库根目录执行）
mkdir -p .claude/skills
git clone https://github.com/heroak2008/colleague-skill .claude/skills/create-shadow

# 或安装到全局（所有项目都能用）
git clone https://github.com/heroak2008/colleague-skill ~/.claude/skills/create-shadow
```

### OpenCode

```bash
mkdir -p ~/.opencode/skills
git clone https://github.com/heroak2008/colleague-skill ~/.opencode/skills/create-shadow
# 设置目录变量（若平台未自动注入）
echo 'export SKILL_DIR="$HOME/.opencode/skills/create-shadow"' >> ~/.bashrc && source ~/.bashrc
```

### Codex CLI（OpenAI Codex）

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/heroak2008/colleague-skill ~/.codex/skills/create-shadow
# 设置目录变量和 API Key
echo 'export SKILL_DIR="$HOME/.codex/skills/create-shadow"' >> ~/.bashrc
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

详见 [AGENTS.md](AGENTS.md) 了解 Codex 的完整使用说明。

### 依赖（可选）

```bash
pip3 install -r requirements.txt
```

---

## 使用

在 Claude Code / OpenCode 中输入：

```
/create-shadow
```

在 Codex CLI 中，将 `AGENTS.md` 作为系统指令载入，然后输入：

```
/create-shadow
```

按提示输入影分身代号、你的背景（职业/领域/方向）、风格标签，然后选择数据来源。所有字段均可跳过，仅凭描述也能生成。

完成后用 `/{slug}` 激活你的影分身。

### TXT 聊天记录导入示例

```bash
# 解析单个文件，提取你自己的发言
python3 tools/txt_parser.py --input chat.txt --target "你的名字" --output /tmp/out.txt

# 解析整个目录（支持递归）
python3 tools/txt_parser.py --input ./chats/ --target "你的名字" --output /tmp/out.txt

# 解析多个文件
python3 tools/txt_parser.py --input chat1.txt chat2.txt --target "你的名字"

# 先列出识别到的说话人，再确认目标名字
python3 tools/txt_parser.py --input ./chats/ --list-speakers
```

工具会自动：
- 识别多种 TXT 格式（混用也没问题）
- 过滤 `[图片]`、`[语音]`、撤回消息等噪声
- 自动探测 UTF-8 / GBK / GB18030 / Big5 编码
- 对消息进行分类（长消息 / 决策类 / 日常）以便 AI 优先分析重要内容
- 若你的消息数量过少，给出明确提示

### 管理命令

| 命令 | 说明 |
|------|------|
| `/list-shadows` | 列出所有影分身 Skill |
| `/{slug}` | 激活影分身（完整版） |
| `/{slug}-work` | 仅知识与能力 |
| `/{slug}-persona` | 仅说话风格 |
| `/shadow-rollback {slug} {version}` | 回滚到历史版本 |
| `/delete-shadow {slug}` | 删除 |

---

## 效果示例

> 输入：`技术博主，后端工程师，INTJ，直接犀利，字节味`

**场景一：代替本体回答技术问题**

```
用户         ❯ 微服务架构下怎么处理分布式事务？

影分身.skill ❯ 先问一下，你这个场景的一致性要求是强一致还是最终一致？
               如果是最终一致，Saga 模式 + 补偿机制是最务实的选择，
               别上来就搞 2PC，那是给自己找麻烦。
               你们现在的技术栈是什么？我帮你看看具体怎么落地。
```

**场景二：用本体风格写文章**

```
用户         ❯ 帮我写一篇关于 AI 替代程序员的文章，我的观点是"不会"

影分身.skill ❯ 标题：《AI 不会取代程序员，但会取代不用 AI 的程序员》
               
               （按你的写作习惯：结论先行，先怼反方观点，再用数据和案例支撑...）
```

---

## 功能特性

### 生成的影分身结构

每个影分身 Skill 由两部分组成，共同驱动输出：

| 部分 | 内容 |
|------|------|
| **Part A — 知识与能力** | 你的专业领域、知识体系、思维框架、写作习惯、输出风格 |
| **Part B — 说话风格** | 5 层结构：硬规则 → 身份 → 表达习惯 → 决策模式 → 人际行为 |

运行逻辑：`接到任务 → 风格层判断态度 → 知识层执行 → 用你的语气输出`

### 支持的标签

**个性**：直接犀利 · 完美主义 · 差不多就行 · 拖延症 · 话少话多 · 只读不回 · 秒回强迫症 · 反复横跳 · 爱讲大道理 …

**领域偏好**：字节范 · 阿里味 · 腾讯味 · 华为味 · 技术至上 · 第一性原理 · OKR 狂热者 · 创业公司派 …

**职业背景**：后端 · 前端 · 算法 · 产品 · 设计 · 数据分析 · 独立开发者 · 技术博主 · 研究员 …

### 进化机制

- **追加文件** → 自动分析增量 → merge 进对应部分，不覆盖已有结论
- **对话纠正** → 说「我不会这样，我应该是 xxx」→ 写入 Correction 层，立即生效
- **版本管理** → 每次更新自动存档，支持回滚到任意历史版本

---

## 项目结构

本项目遵循 [AgentSkills](https://agentskills.io) 开放标准，整个 repo 就是一个 skill 目录：

```
create-shadow/
├── SKILL.md              # skill 入口（官方 frontmatter）
├── prompts/              # Prompt 模板
│   ├── intake.md         #   对话式信息录入
│   ├── work_analyzer.md  #   知识与能力提取
│   ├── persona_analyzer.md #  说话风格提取（含标签翻译表）
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
├── shadows/              # 生成的影分身 Skill（gitignored）
├── docs/PRD.md
├── requirements.txt
└── LICENSE
```

---

## 注意事项

- **原材料质量决定影分身质量**：你的聊天记录 + 文章 + 笔记 > 仅手动描述
- 建议优先收集：你**主动写的**长文 > **决策类回复** > 日常消息
- TXT 聊天记录至少建议 30 条以上你自己的消息，才能生成有参考价值的影分身
- 目前还是一个 demo 版本，如果有 bug 请多多提 issue！

---

## Star History

<a href="https://www.star-history.com/?repos=heroak2008%2Fcolleague-skill&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=heroak2008/colleague-skill&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=heroak2008/colleague-skill&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=heroak2008/colleague-skill&type=date&legend=top-left" />
 </picture>
</a>

---

<div align="center">

MIT License © [heroak2008](https://github.com/heroak2008)


</div>
