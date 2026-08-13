# oc-run — OpenCode Sub-Agent Orchestrator (AI Skill)

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

> English | [简体中文](./README.md)

**oc-run** is a dispatch interface between a main agent and opencode sub-agents. Give it workspace dirs + prompts, and it dispatches parallel sub-agents (up to 6) that run in isolated contexts, then returns a structured summary — each sub-agent's session ID, tool-call count, and final report. Supports `--session` resume for multi-round iteration, cross-project session history, per-task model selection, and runs in any environment (built-in probe for stripped-PATH shells). Pure Python stdlib, zero dependencies.

## Install

### For AI agents (one-shot install)

**Copy this prompt to your local AI agent (ZCode / Claude Code / Codex etc.) and it will install everything:**

````markdown
Install the oc-run skill (GitHub: https://github.com/RayMorTwinkle/oc-run).

Background: oc-run is an opencode sub-agent orchestrator — parallel dispatch, auto-summarized reports, --session resume.
It requires opencode CLI (npm i -g opencode-ai) and python3.

Steps:
1. Download and extract (skip if ~/.agents/skills/oc-run already exists):
   curl -L -o /tmp/oc-run.zip https://github.com/RayMorTwinkle/oc-run/archive/refs/heads/main.zip
   unzip -o /tmp/oc-run.zip -d /tmp/ && mv /tmp/oc-run-main ~/.agents/skills/oc-run
   Note: ~/.agents/skills/ is a shared skill dir; if your platform uses another
   (Claude Code: ~/.claude/skills/, OpenCode: ~/.config/opencode/skills/), install there instead.
2. Verify: ~/.agents/skills/oc-run/SKILL.md and oc-run.py exist.
3. (Optional but recommended) Put oc-run on PATH:
   ln -sf ~/.agents/skills/oc-run/oc-run.py ~/.local/bin/oc-run
4. Verify: `oc-run --help` prints the Chinese usage guide; fallback: python3 ~/.agents/skills/oc-run/oc-run.py --help.
5. End-to-end test: `oc-run --sessions 3` lists the 3 most recent sessions (across all git projects).
   If it says "opencode not found", install opencode first; oc-run auto-probes common paths
   (~/.opencode/bin, fnm, workbuddy, homebrew, ...).
6. Confirm to the user and summarize oc-run capabilities: parallel dispatch / resume (--session) /
   cross-project history (--sessions) / model selection (--model).
````

### For humans

1. Clone or download: `git clone https://github.com/RayMorTwinkle/oc-run.git` (or [zip](https://github.com/RayMorTwinkle/oc-run/archive/refs/heads/main.zip))
2. Put the `oc-run` folder into your agent's skill directory (Claude Code: `~/.claude/skills/`, OpenCode: `~/.config/opencode/skills/`, shared: `~/.agents/skills/`)
3. (Optional) Symlink to PATH: `ln -s "$(pwd)/oc-run/oc-run.py" ~/.local/bin/oc-run`

## Quick start

```bash
# Single task (blocking, prints summary when done)
oc-run --dir /path/to/project --prompt "Analyze the tech stack"

# Multiple tasks: dirs and prompts paired one-to-one (main usage, up to 6 in parallel)
oc-run --dir /path/A --prompt "Analyze A" --dir /path/B --prompt "Analyze B"

# Broadcast: one prompt to many dirs
oc-run --dir /path/A --dir /path/B --prompt "One-line intro, please"

# Batch task file (per-task dir / prompt / title)
oc-run --tasks tasks.json   # file: [{"dir": "...", "prompt": "...", "title": "..."}, ...]

# Resume a session (multi-round iteration)
oc-run --sessions                                  # list history (all projects)
oc-run --dir /path/A --session ses_xxx --prompt "Continue from last round"

# Machine-readable output + model selection
oc-run --dir /path/A --prompt "..." --json --model opencode-go/deepseek-v4-pro
```

Full parameter reference is in `oc-run --help` (self-describing, Chinese).

## Recommended usage (for LLMs)

1. **Token offloading (one round)** — send a sub-agent to read lots of material (web/code/docs) and report only concise conclusions + sources. Sub-agent context is isolated; your context stays clean. Cheap on Flash.
2. **Master–worker loop (multi-round)** — resume the same sub-agent with `--session` to keep its memory; iterate until the result is good. Two iron rules: give detailed task descriptions (the sub-agent has no global view — the prompt is its world); demand a strict report format (conclusion + sources + uncertainties + unfinished items + key functions/actions).

Both patterns support parallelism (≤6) and async execution (background-task mechanisms of ZCode / Claude Code etc., with completion notification).

## Known issues (opencode version quirks)

- Native `opencode run --session <id>` hangs in 1.18.15 non-interactive resume (zero output) — oc-run works around it via `opencode serve` + `--attach`.
- `opencode session list` only shows the current project's sessions — oc-run queries the SQLite DB directly for cross-project history, with automatic fallback.
- Stripped-PATH environments (cron/scripts/agent subprocesses) — built-in probe finds opencode in common locations.

## Structure

```
oc-run/
├── SKILL.md                  # Agent skill definition
├── README.md                 # 简体中文文档（主文档）
├── README_en.md              # English docs
├── LICENSE                   # MIT
├── oc-run.py                 # Main script (pure Python stdlib)
└── examples/
    └── tasks.example.json    # Batch task template
```

## License

MIT
