# shadow-clone.skill — Codex / OpenAI Agent Instructions

> This file is the entry point for **Codex CLI** (`codex`) and **OpenAI Responses API** agents.
> It contains the same skill logic as `SKILL.md` but references the Codex tooling conventions.
>
> For Claude Code / OpenCode, use `SKILL.md` instead.

---

## Setup (one-time)

```bash
# 1. Clone the skill
git clone https://github.com/heroak2008/colleague-skill ~/.codex/skills/create-shadow

# 2. Set the skill directory variable
echo 'export SKILL_DIR="$HOME/.codex/skills/create-shadow"' >> ~/.bashrc
# (use ~/.zshrc if you use zsh)
source ~/.bashrc

# 3. Install optional dependencies
pip3 install -r ~/.codex/skills/create-shadow/requirements.txt
```

---

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `OPENAI_API_KEY` | OpenAI API key used by Codex CLI | `sk-...` |
| `SKILL_DIR` | Path to this skill's install directory | `~/.codex/skills/create-shadow` |

No Anthropic/Claude keys are required.

---

## Activation

After setup, tell Codex:

```
/create-shadow
```

or simply:

```
Help me create a shadow clone skill
```

---

## What This Skill Does

shadow-clone.skill distills **you** into an AI Skill that can:

- Answer questions in your communication style and voice (Persona)
- Apply your knowledge, frameworks, and writing habits (Knowledge & Capabilities)
- Write articles in your style on your behalf
- Continuously evolve as you provide more source material

**Source materials supported**: your own chat logs, articles, notes, PDFs, screenshots, plain text.

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
| `/create-shadow` | Start creating a new shadow clone Skill |
| `/update-shadow {slug}` | Append new materials to an existing shadow clone |
| `/list-shadows` | List all generated shadow clones |
| `/shadow-rollback {slug} {version}` | Roll back to a previous version |
| `/delete-shadow {slug}` | Delete a shadow clone |

---

## Quick Verification

```bash
# Verify tool scripts work
python3 $SKILL_DIR/tools/txt_parser.py --help
python3 $SKILL_DIR/tools/skill_writer.py --action list --base-dir ./shadows
python3 $SKILL_DIR/tools/version_manager.py --help
```

---

## Migration from colleague.skill

If you were previously using this skill as colleague.skill:

1. Data in `colleagues/` is separate from `shadows/` — you may want to re-create entries.
2. Set `SKILL_DIR` to your install path (see Setup above).
3. Claude-specific environment variables (`ANTHROPIC_API_KEY`, `CLAUDE_SKILL_DIR`) are not needed.
4. Codex uses `OPENAI_API_KEY` — set this in your environment.

For full installation notes, see [INSTALL.md](INSTALL.md).
