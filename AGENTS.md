# colleague-skill — Codex / OpenAI Agent Instructions

> This file is the entry point for **Codex CLI** (`codex`) and **OpenAI Responses API** agents.
> It contains the same skill logic as `SKILL.md` but references the Codex tooling conventions.
>
> For Claude Code / OpenCode, use `SKILL.md` instead.

---

## Setup (one-time)

```bash
# 1. Clone the skill
git clone https://github.com/heroak2008/colleague-skill ~/.codex/skills/create-colleague

# 2. Set the skill directory variable
echo 'export SKILL_DIR="$HOME/.codex/skills/create-colleague"' >> ~/.bashrc
# (use ~/.zshrc if you use zsh)
source ~/.bashrc

# 3. Install optional dependencies
pip3 install -r ~/.codex/skills/create-colleague/requirements.txt
```

---

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `OPENAI_API_KEY` | OpenAI API key used by Codex CLI | `sk-...` |
| `SKILL_DIR` | Path to this skill's install directory | `~/.codex/skills/create-colleague` |

No Anthropic/Claude keys are required.

---

## Activation

After setup, tell Codex:

```
/create-colleague
```

or simply:

```
Help me create a colleague skill for Zhang San
```

---

## What This Skill Does

colleague.skill distills a real colleague into an AI Skill that can:

- Answer questions in their communication style (Persona)
- Apply their technical standards and workflows (Work Skill)
- Continuously evolve as you provide more source material

**Source materials supported**: Feishu messages / docs, DingTalk docs, Slack messages, emails (.eml/.mbox), PDFs, screenshots, plain text.

---

## Tool Conventions (Codex)

Codex CLI uses the following tool names. When executing instructions from `SKILL.md`, map them as follows:

| SKILL.md tool | Codex CLI equivalent |
|---------------|---------------------|
| `Read` | `read_file` |
| `Write` | `write_file` |
| `Edit` | `edit_file` (or `write_file` for full replacement) |
| `Bash` | `shell` / `execute_command` |

All `python3 ${SKILL_DIR}/tools/...` Bash commands remain unchanged — Codex can execute them via the shell tool.

---

## Full Skill Instructions

The complete skill instructions are in `SKILL.md` (in the same directory as this file).

When running under Codex CLI, load and follow `SKILL.md` as your system instructions. The `${SKILL_DIR}` variable should be set to the path of this repository (see Setup above).

```bash
# Quick check that SKILL_DIR is set correctly:
echo $SKILL_DIR
ls $SKILL_DIR/tools/
```

---

## Supported Commands

| Command | Description |
|---------|-------------|
| `/create-colleague` | Start creating a new colleague Skill |
| `/update-colleague {slug}` | Append new materials to an existing Skill |
| `/list-colleagues` | List all generated colleague Skills |
| `/colleague-rollback {slug} {version}` | Roll back to a previous version |
| `/delete-colleague {slug}` | Delete a colleague Skill |

---

## Quick Verification

```bash
# Verify tool scripts work
python3 $SKILL_DIR/tools/feishu_parser.py --help
python3 $SKILL_DIR/tools/email_parser.py --help
python3 $SKILL_DIR/tools/skill_writer.py --action list --base-dir ./colleagues
python3 $SKILL_DIR/tools/version_manager.py --help
```

---

## Migration from Claude Code

If you were previously using this skill with Claude Code:

1. No changes to your data in `colleagues/` — the format is identical.
2. Set `SKILL_DIR` to your install path (see Setup above).
3. Claude-specific environment variables (`ANTHROPIC_API_KEY`, `CLAUDE_SKILL_DIR`) are not needed.
4. Codex uses `OPENAI_API_KEY` — set this in your environment.

For full migration notes, see [INSTALL.md](INSTALL.md).
