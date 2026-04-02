# 影分身.skill 安装说明

---

## 选择你的平台

### A. Claude Code

本项目遵循官方 [AgentSkills](https://agentskills.io) 标准，整个 repo 就是 skill 目录。克隆到 Claude skills 目录即可：

```bash
# ⚠️ 必须在 git 仓库根目录执行！
cd $(git rev-parse --show-toplevel)

# 方式 1：安装到当前项目
mkdir -p .claude/skills
git clone https://github.com/heroak2008/colleague-skill .claude/skills/create-shadow

# 方式 2：安装到全局（所有项目都能用）
git clone https://github.com/heroak2008/colleague-skill ~/.claude/skills/create-shadow
```

然后在 Claude Code 中说 `/create-shadow` 即可启动。

生成的影分身 Skill 默认写入 `./shadows/` 目录。

---

### B. OpenCode

[OpenCode](https://github.com/sst/opencode) 与 Claude Code 使用相同的 AgentSkills 格式。

```bash
# 安装到 OpenCode 的 skills 目录
mkdir -p ~/.opencode/skills
git clone https://github.com/heroak2008/colleague-skill ~/.opencode/skills/create-shadow

# 设置环境变量（加到 ~/.bashrc 或 ~/.zshrc）
echo 'export SKILL_DIR="$HOME/.opencode/skills/create-shadow"' >> ~/.bashrc
source ~/.bashrc
```

重启 OpenCode session，说 `/create-shadow` 启动。

> **注意**：OpenCode 注入的目录变量为 `${OPENCODE_SKILL_DIR}`（若平台支持），否则请确保 `SKILL_DIR` 已设置。

---

### C. Codex CLI（OpenAI Codex）

[Codex CLI](https://github.com/openai/codex) 通过读取 `AGENTS.md` 获取 agent 指令。

```bash
# 1. 安装到 Codex 的 skills 目录
mkdir -p ~/.codex/skills
git clone https://github.com/heroak2008/colleague-skill ~/.codex/skills/create-shadow

# 2. 设置环境变量（加到 ~/.bashrc 或 ~/.zshrc）
echo 'export SKILL_DIR="$HOME/.codex/skills/create-shadow"' >> ~/.bashrc
source ~/.bashrc

# 3. 设置 OpenAI API Key
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

在 Codex CLI 会话中，将 `AGENTS.md` 作为系统指令载入，然后说 `/create-shadow` 启动。

> **工具名映射**（Codex CLI）：
> - `Read` → `read_file`
> - `Write` → `write_file`
> - `Edit` → `edit_file`
> - `Bash` → `shell` / `execute_command`

---

## 依赖安装

```bash
# 基础（Python 3.9+）
pip3 install pypinyin        # 中文名转拼音 slug（可选但推荐）

# 其他格式支持（可选）
pip3 install python-docx     # Word .docx 转文本
pip3 install openpyxl        # Excel .xlsx 转 CSV
```

---

## 快速验证

```bash
# 进入安装目录（根据你的平台替换路径）
cd $SKILL_DIR
# Claude Code:  cd ~/.claude/skills/create-shadow
# OpenCode:     cd ~/.opencode/skills/create-shadow
# Codex CLI:    cd ~/.codex/skills/create-shadow

# 测试 TXT 解析器
python3 tools/txt_parser.py --help

# 列出已有影分身 Skill
python3 tools/skill_writer.py --action list --base-dir ./shadows
```

---

## 目录结构说明

本项目整个 repo 就是一个 skill 目录（AgentSkills 标准格式）：

```
colleague-skill/        ← 克隆到你的平台 skills 目录（名称建议 create-shadow）
├── SKILL.md            # skill 入口（AgentSkills frontmatter，适用 Claude Code / OpenCode）
├── AGENTS.md           # Codex CLI / OpenAI Agent 入口
├── prompts/            # 分析和生成的 Prompt 模板
├── tools/              # Python 工具脚本
├── docs/               # 文档（PRD 等）
│
└── shadows/            # 生成的影分身 Skill 存放处（.gitignore 排除）
    └── {slug}/
        ├── SKILL.md            # 完整 Skill（说话风格 + 知识与能力）
        ├── work.md             # 仅知识与能力
        ├── persona.md          # 仅说话风格
        ├── meta.json           # 元数据
        ├── versions/           # 历史版本
        └── knowledge/          # 原始材料归档
```
