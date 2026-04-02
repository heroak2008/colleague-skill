<div align="center">

# shadow-clone.skill

> *"The original is too busy — time to send a shadow clone."*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)](https://claude.ai/code)
[![OpenCode](https://img.shields.io/badge/OpenCode-Compatible-blue)](https://github.com/sst/opencode)
[![Codex CLI](https://img.shields.io/badge/Codex%20CLI-Compatible-green)](https://github.com/openai/codex)
[![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)](https://agentskills.io)

<br>

You've answered the same questions a hundred times and still have to start from scratch?<br>
You know what you want to write, but staring at a blank page kills the momentum?<br>
Years of chat logs, notes, and docs full of your hard-won insights, sitting unused?<br>
You want an AI that actually thinks like you — not a generic assistant, but *you*?<br>

**Distill your own thinking, habits, and knowledge into an AI shadow clone —**<br>
**let it answer questions, write articles, and handle requests on your behalf.**

<br>

Feed it your **TXT chat logs, notes, articles** (multiple files supported) or a manual description<br>
and get an **AI Skill that actually sounds and thinks like you**<br>
It answers in your voice, writes in your style, and knows when to say "no"

[Supported Sources](#supported-data-sources) · [Install](#install) · [Usage](#usage) · [Demo](#demo) · [Detailed Install](INSTALL.md) · [**中文**](README.md)

</div>


## Supported Data Sources

| Source | Support | Notes |
|--------|:-------:|-------|
| **TXT chat logs** (recommended) | ✅ | Multi-file, multi-person; auto-extracts your own messages |
| Personal notes / articles / Markdown | ✅ | Upload directly; extracts your knowledge and writing style |
| Manual description | ✅ | Describe yourself — no files needed |
| PDF / Images / Screenshots | ✅ | Upload directly for AI to read |

### Supported TXT Formats

```
# Format 1 — Full timestamp
2024-01-01 10:00:00 Zhang San: message content

# Format 2 — Date only
2024-01-01 Zhang San: message content

# Format 3 — WeChat-style (timestamp / sender / content on separate lines)
2024-01-01 10:00:00
Zhang San
message content

# Format 4 — No timestamp
Zhang San: message content

# Format 5 — Markdown bold
**Zhang San**: message content

# Format 6 — Enterprise ID format (tab-separated)
Zhang San(z00611745)	2026-01-04 15:58:23
message content
```

Mixing formats within the same file is fine.

---

## Install

### Claude Code

> **Important**: Claude Code looks for skills in `.claude/skills/` at the **git repo root**. Make sure you run this in the right place.

```bash
# Install to current project (run at git repo root)
mkdir -p .claude/skills
git clone https://github.com/heroak2008/colleague-skill .claude/skills/create-shadow

# Or install globally (available in all projects)
git clone https://github.com/heroak2008/colleague-skill ~/.claude/skills/create-shadow
```

### OpenCode

```bash
mkdir -p ~/.opencode/skills
git clone https://github.com/heroak2008/colleague-skill ~/.opencode/skills/create-shadow
# Set the skill directory variable (if not injected by the platform)
echo 'export SKILL_DIR="$HOME/.opencode/skills/create-shadow"' >> ~/.bashrc && source ~/.bashrc
```

### Codex CLI (OpenAI Codex)

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/heroak2008/colleague-skill ~/.codex/skills/create-shadow
# Set the skill directory variable and API key
echo 'export SKILL_DIR="$HOME/.codex/skills/create-shadow"' >> ~/.bashrc
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

See [AGENTS.md](AGENTS.md) for full Codex setup instructions.

### Dependencies (optional)

```bash
pip3 install -r requirements.txt
```

---

## Usage

In Claude Code or OpenCode, type:

```
/create-shadow
```

In Codex CLI, load `AGENTS.md` as your system instructions, then type:

```
/create-shadow
```

Follow the prompts: enter a codename for your shadow clone, your background (profession / domains / focus areas), and personality tags. All fields can be skipped — even a manual description alone can generate a Skill.

Once created, activate your shadow clone with `/{slug}`.

### Commands

| Command | Description |
|---------|-------------|
| `/list-shadows` | List all shadow clone Skills |
| `/{slug}` | Activate shadow clone (full version) |
| `/{slug}-work` | Knowledge & capabilities only |
| `/{slug}-persona` | Speaking style only |
| `/shadow-rollback {slug} {version}` | Rollback to a previous version |
| `/delete-shadow {slug}` | Delete |

---

## Demo

> Input: `tech blogger, backend engineer, INTJ, direct and sharp, ByteDance-style`

**Scenario 1: Answering a question on your behalf**

```
User             ❯ How do you handle distributed transactions in microservices?

shadow-clone.skill ❯ Quick question — do you need strong consistency or eventual consistency here?
                     If eventual consistency works, Saga + compensation is the most practical path.
                     Don't jump straight to 2PC — that's asking for trouble.
                     What's your tech stack? I'll walk you through the specifics.
```

**Scenario 2: Writing an article in your style**

```
User             ❯ Write an article arguing that AI won't replace programmers

shadow-clone.skill ❯ Title: "AI Won't Replace Programmers — But It Will Replace Those Who Don't Use AI"
                     
                     (Following your writing style: conclusion first, counter the opposing view,
                      then back it up with data and examples...)
```

---

## Features

### Generated Shadow Clone Structure

Each shadow clone Skill has two parts that work together:

| Part | Content |
|------|---------|
| **Part A — Knowledge & Capabilities** | Your domains, knowledge base, mental models, writing habits, output style |
| **Part B — Speaking Style** | 5-layer structure: hard rules → identity → expression → decisions → interpersonal |

Execution: `Receive task → Style layer decides attitude → Knowledge layer executes → Output in your voice`

### Supported Tags

**Personality**: Direct & sharp · Perfectionist · Good enough · Procrastinator · Quiet · Read-no-reply · Always-online · Flip-flopper · Big-picture thinker …

**Domain culture**: ByteDance-style · Alibaba-style · Tencent-style · Tech-first · First-principles · OKR-obsessed · Startup-mode …

**Professional background**: Backend · Frontend · ML/AI · Product · Design · Data · Indie developer · Tech blogger · Researcher …

### Evolution

- **Append files** → auto-analyze delta → merge into relevant sections, never overwrite existing conclusions
- **Conversation correction** → say "I wouldn't do that, I'd actually be xxx" → writes to Correction layer, takes effect immediately
- **Version control** → auto-archive on every update, rollback to any previous version

---

## Project Structure

This project follows the [AgentSkills](https://agentskills.io) open standard. The entire repo is a skill directory:

```
create-shadow/
├── SKILL.md              # Skill entry point (official frontmatter)
├── prompts/              # Prompt templates
│   ├── intake.md         #   Dialogue-based info collection
│   ├── work_analyzer.md  #   Knowledge & capability extraction
│   ├── persona_analyzer.md #  Speaking style extraction (with tag translation)
│   ├── work_builder.md   #   work.md generation template
│   ├── persona_builder.md #   persona.md 5-layer structure
│   ├── merger.md         #   Incremental merge logic
│   └── correction_handler.md # Conversation correction handler
├── tools/                # Python tools
│   ├── txt_parser.py             # TXT chat log parser (main entry)
│   ├── skill_writer.py           # Skill file management
│   └── version_manager.py        # Version archive & rollback
├── tests/                # Unit tests
│   └── test_txt_parser.py
├── shadows/              # Generated shadow clone Skills (gitignored)
├── docs/PRD.md
├── requirements.txt
└── LICENSE
```

---

## Notes

- **Source material quality = shadow clone quality**: your chat logs + articles + notes > manual description only
- Prioritize collecting: long-form writing **by you** > **decision-making replies** > casual messages
- Aim for at least 30 of your own messages in the TXT logs for a meaningful shadow clone
- This is still a demo version — please file issues if you find bugs!

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
