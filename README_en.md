<div align="center">

<img src="oc-run.svg" alt="oc-run" width="320">

# oc-run — OpenCode as sub-agents for any harness

![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Deps](https://img.shields.io/badge/Dependencies-zero-brightgreen) ![Type](https://img.shields.io/badge/Type-AI_Skill-orange)

**Free your main agent from model lock-in — the main agent commands, OpenCode sub-agents do the work, with any model you want.**

</div>

---

## What it is

```
  Your main agent (ZCode / Claude Code / Codex …)
              │  oc-run --dir A --prompt "…" --dir B --prompt "…"
              ▼
        oc-run dispatcher ──parallel──▶ opencode sub-agent A (model X)
              │                         └── opencode sub-agent B (model Y)
              ▼
       structured summary: session / tool calls / final report
```

oc-run is a thin adapter: give it workspace dirs + prompts, it dispatches parallel sub-agents (up to 6) that run in isolated contexts, then returns a structured summary. Sub-agents search, read and reason in isolation — your main context stays clean. `--session` resume keeps a sub-agent's memory for multi-round iteration. Pure Python stdlib, zero dependencies.

## ✨ What it can do

- 🎛️ **Model freedom**: OpenCode is provider-agnostic — sub-agents can use any model you configure (DeepSeek, GLM, Kimi, Grok, free tiers, even Claude via a custom provider), never locked to your main agent's vendor
- 💰 **Save premium tokens**: offload the "read a lot" work to cheap models; premium tokens are spent only on commanding and deciding
- ⚡ **Parallel dispatch**: up to 6 sub-agents at once, each with its own workspace dir and prompt
- 🔁 **Multi-round iteration**: `--session` resumes the same sub-agent, keeping its memory, iterate until the result is good
- 📊 **Auto summary**: each sub-agent's session ID, tool calls (grouped by tool), final report, tokens — at a glance
- 🔎 **Cross-project history**: `--sessions` lists sessions across all git projects (native `session list` only shows the current one)
- 🧩 **Runs anywhere**: built-in probe finds opencode even in stripped-PATH environments (cron / scripts / agent subprocesses)

## 🔧 Install

### For AI agents (one-shot install)

**Copy this prompt to your local AI agent (ZCode / Claude Code / Codex etc.) and it will install everything:**

````markdown
Install the oc-run skill (GitHub: https://github.com/RayMorTwinkle/oc-run).

Background: oc-run lets any main agent (ZCode / Claude Code / Codex etc.) command the local OpenCode as sub-agents — parallel dispatch, auto-summarized reports, --session resume, and **sub-agents can use any model, not locked to your main agent's vendor**.
It requires opencode CLI (npm i -g opencode-ai) and python3.

Steps:
1. Download and extract (skip if ~/.agents/skills/oc-run-subagent already exists):
   curl -L -o /tmp/oc-run.zip https://github.com/RayMorTwinkle/oc-run/archive/refs/heads/main.zip
   unzip -o /tmp/oc-run.zip -d /tmp/ && mv /tmp/oc-run-main ~/.agents/skills/oc-run-subagent
   Note: ~/.agents/skills/ is a shared skill dir; if your platform uses another
   (Claude Code: ~/.claude/skills/, OpenCode: ~/.config/opencode/skills/), install there instead.
2. Verify: ~/.agents/skills/oc-run-subagent/SKILL.md and scripts/oc-run.py exist.
3. (Optional but recommended) Put oc-run on PATH:
   ln -sf ~/.agents/skills/oc-run-subagent/scripts/oc-run.py ~/.local/bin/oc-run
4. Verify: `oc-run --help` prints the Chinese usage guide; fallback: python3 ~/.agents/skills/oc-run-subagent/scripts/oc-run.py --help.
5. End-to-end test: `oc-run --sessions 3` lists the 3 most recent sessions (across all git projects).
   If it says "opencode not found", install opencode first; oc-run auto-probes common paths
   (~/.opencode/bin, fnm, workbuddy, homebrew, ...).
6. Confirm to the user and summarize oc-run capabilities: parallel dispatch / resume (--session) /
   cross-project history (--sessions) / model selection (--model).
````

### For humans

1. Clone or download: `git clone https://github.com/RayMorTwinkle/oc-run.git` (or [zip](https://github.com/RayMorTwinkle/oc-run/archive/refs/heads/main.zip))
2. Put the `oc-run` folder into your agent's skill directory and **rename it to `oc-run-subagent`** (Claude Code: `~/.claude/skills/`, OpenCode: `~/.config/opencode/skills/`, shared: `~/.agents/skills/`) — the skill dir name must match the `name` in SKILL.md
3. (Optional) Symlink to PATH: `ln -s "$(pwd)/oc-run/scripts/oc-run.py" ~/.local/bin/oc-run`

## 🚀 Quick start

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

## 🧠 Recommended usage (for LLMs)

1. **Token offloading (one round)** — send a sub-agent to read lots of material (web/code/docs) and report only concise conclusions + sources. Sub-agent context is isolated; your context stays clean. Cheap on Flash.
2. **Master–worker loop (multi-round)** — resume the same sub-agent with `--session` to keep its memory; iterate until the result is good. Two iron rules: give detailed task descriptions (the sub-agent has no global view — the prompt is its world); demand a strict report format (conclusion + sources + uncertainties + unfinished items + key functions/actions).

Both patterns support parallelism (≤6) and async execution (background-task mechanisms of ZCode / Claude Code etc., with completion notification).

## ❓ FAQ

**Why not just run native `opencode run` directly?**
Native handles "run once"; oc-run adds the three things a main agent actually needs: **context isolation** (a sub-agent can burn 480K tokens of reading without touching your context), **model freedom** (`--model` switches freely, no vendor lock-in), and **parallel dispatch + structured summary** (6 at once, one report).

**What does "model freedom" mean exactly?**
OpenCode is a provider-agnostic relay. Configure any model service in opencode and sub-agents can use it — DeepSeek, GLM, Kimi, Grok, free tiers, even Claude via a custom provider, regardless of your main agent's vendor. Keep premium models for commanding; hand the heavy reading to cheap ones.

**oc-run vs oc-run-subagent vs the repo name?**
The command is `oc-run`, the skill is `oc-run-subagent` (skill dir must match the `name` in SKILL.md), the GitHub repo is `oc-run`. After install, the command and the skill both drive the same tool.

## Structure

```
oc-run/                      # repo name; rename to oc-run-subagent when installing as a skill
├── SKILL.md                 # Agent skill definition (name: oc-run-subagent)
├── README.md                # 简体中文文档（主文档）
├── README_en.md             # English docs
├── LICENSE                  # MIT
├── scripts/
│   └── oc-run.py            # Main script (pure Python stdlib)
└── examples/
    └── tasks.example.json   # Batch task template
```

## License

MIT
