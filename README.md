<div align="center">

> [English](./README_en.md) | 简体中文

<img src="oc-run.svg" alt="oc-run" width="320">

# oc-run — 把 OpenCode 变成任意 Harness 的子 Agent

![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Deps](https://img.shields.io/badge/Dependencies-zero-brightgreen) ![Type](https://img.shields.io/badge/Type-AI_Skill-orange)

**把你的主 Agent 从模型绑定中解放出来——主 Agent 负责指挥，OpenCode 子 Agent 负责干活，用任何模型，干任何活。**

</div>

---

## 它是什么

```
  你的主 Agent（ZCode / Claude Code / Codex …）
              │  oc-run --dir A --prompt "…" --dir B --prompt "…"
              ▼
        oc-run 调度器 ──并行──▶ opencode 子 Agent A（模型 X）
              │                  └── opencode 子 Agent B（模型 Y）
              ▼
       结构化汇总：session / 动作次数 / 最终报告
```

oc-run 是一层薄薄的适配器：给出若干"工作区目录 + 提示词"，它并行派发给独立子 Agent（≤6 个），完成后返回结构化汇总。子 Agent 的搜索、读码、思考都在隔离环境完成，不占主 Agent 上下文；支持 `--session` 续跑同一子 Agent，保持记忆做多轮迭代。纯 Python 标准库，零第三方依赖。

## ✨ 它能干什么

- 🎛️ **模型自由**：OpenCode 本身 provider 中立——子 Agent 可以用你配置的任何模型（DeepSeek、GLM、Kimi、Grok、免费档，甚至自定义 provider 里的 Claude），完全不绑定主 Agent 同家供应商
- 💰 **省高级 token**："大量读"的活外包给便宜的模型，高级模型 token 只花在指挥决策上
- ⚡ **并行派活**：一次最多 6 个子 Agent 同时干活，各自独立工作目录与提示词
- 🔁 **多轮迭代**：`--session` 续跑同一子 Agent，保持它的记忆，按报告循环指挥直到达标
- 📊 **自动汇总**：每个子 Agent 的 session ID、动作次数（按工具分组）、最终报告、tokens，一目了然
- 🔎 **跨项目历史**：`--sessions` 列出所有 git 项目的 session（原生 `session list` 只能看到当前项目）
- 🧩 **任意环境可跑**：内置探测，PATH 精简环境（cron / 脚本 / Agent 子进程）也能找到 opencode

## 🔧 安装

### 面向 AI 智能体（一键安装，推荐）

**把下面这段提示词直接复制给你的本地 AI Agent（ZCode / Claude Code / Codex 等），它就能自动完成安装：**

````markdown
请帮我安装 oc-run skill（GitHub: https://github.com/RayMorTwinkle/oc-run）。

背景：oc-run 让任何主 Agent（ZCode/Claude Code/Codex 等）都能把本机的 OpenCode 当子 Agent 指挥——并行派活、自动汇总报告、--session 续跑、**子 Agent 可用任意模型，不绑定主 Agent 的模型供应商**。
它依赖本机已安装的 opencode CLI（npm i -g opencode-ai）和 python3。

安装步骤：
1. 下载并解压（如果 ~/.agents/skills/oc-run-subagent 已存在则先跳过，直接验证）：
   curl -L -o /tmp/oc-run.zip https://github.com/RayMorTwinkle/oc-run/archive/refs/heads/main.zip
   unzip -o /tmp/oc-run.zip -d /tmp/ && mv /tmp/oc-run-main ~/.agents/skills/oc-run-subagent
   说明：~/.agents/skills/ 是多个 AI 工具共用的 skill 目录；如果你的平台用别的目录
   （如 Claude Code: ~/.claude/skills/，OpenCode: ~/.config/opencode/skills/），装到对应目录即可。
2. 验证 skill 结构：确认 ~/.agents/skills/oc-run-subagent/SKILL.md 和 scripts/oc-run.py 存在。
3. （可选但推荐）把 oc-run 命令放进 PATH，方便直接调用：
   ln -sf ~/.agents/skills/oc-run-subagent/scripts/oc-run.py ~/.local/bin/oc-run
4. 验证命令：oc-run --help 应输出中文使用说明；若 PATH 里没有，用 python3 ~/.agents/skills/oc-run-subagent/scripts/oc-run.py --help。
5. 端到端测试：oc-run --sessions 3 应列出最近 3 个 session（跨所有 git 项目）。
   若报"未找到 opencode"，请先安装 opencode 或告知用户；oc-run 有内置探测，
   会按常见路径（~/.opencode/bin、fnm、workbuddy、homebrew 等）自动查找。
6. 向用户确认安装成功，并简述 oc-run 的能力：并行派活 / 续跑（--session）/ 跨项目历史（--sessions）/ 模型可选（--model）。
````

### 面向人类用户

1. 克隆或下载仓库：
   ```bash
   git clone https://github.com/RayMorTwinkle/oc-run.git
   # 或下载 zip: https://github.com/RayMorTwinkle/oc-run/archive/refs/heads/main.zip
   ```
2. 将 `oc-run` 目录放入智能体的 skill 目录并**重命名为 `oc-run-subagent`**（Claude Code: `~/.claude/skills/`；OpenCode: `~/.config/opencode/skills/`；通用共享: `~/.agents/skills/`）——skill 目录名须与 SKILL.md 的 `name` 一致
3. （可选）软链命令到 PATH：`ln -s "$(pwd)/oc-run/scripts/oc-run.py" ~/.local/bin/oc-run`

## 🚀 快速开始

```bash
# 单个任务（阻塞执行，跑完输出汇总）
oc-run --dir /path/to/project --prompt "分析这个项目的技术栈"

# 多个任务：工作目录与提示词一一对应（主用法，并行度默认 6、上限 6）
oc-run --dir /path/A --prompt "分析项目A" --dir /path/B --prompt "分析项目B"

# 多个目录共用同一个提示词（广播）
oc-run --dir /path/A --dir /path/B --prompt "用中文简述这个项目"

# 批量任务文件（每任务自定义 dir / prompt / title）
oc-run --tasks tasks.json   # 文件为 [{"dir": "...", "prompt": "...", "title": "..."}, ...]

# 续跑：接着某个 session 的上下文继续跑
oc-run --sessions                                  # 查看历史 session（跨所有项目）
oc-run --dir /path/A --session ses_xxx --prompt "继续上次的分析"

# 机器可读输出（给 LLM / 脚本消费）+ 指定模型
oc-run --dir /path/A --prompt "..." --json --model opencode-go/deepseek-v4-pro
```

完整参数与推荐用法见 `oc-run --help`（输出面向 LLM 的中文使用说明）。

## 🧠 推荐用法（给 LLM 的编排建议）

1. **token 外包（单轮）——大量读、简洁报**：派临时子 Agent 去读海量资料（网页/代码/文档），回报只要简洁结论+来源。子 Agent 独立上下文，读再多也不占你的上下文；Flash 便宜，成本可忽略。
2. **主从循环（多轮）——强模型指挥弱模型**：用 `--session` 续跑同一子 Agent（保持记忆），按每次回报决定下一轮，循环直到结果达标。两条铁律：
   - 任务描述要详细：子 Agent 没有你的全局视野，prompt 就是它的世界
   - 回报格式要明确：你只能看到报告/最后发言——回报至少包含 结论 + 来源 + 不确定性 + 未完成项 + 关键函数或举措

两种用法均可并行（一次派多个，≤6）、可异步（借宿主环境如 ZCode / Claude Code 的后台任务机制，完成自动通知）。

## ❓ 常见疑问

**为什么不用原生 `opencode run` 直接跑？**
原生命令只解决"跑一次"；oc-run 补上三件主 Agent 真正需要的事：**上下文隔离**（子 Agent 读 48 万 tokens 资料，你的上下文一滴不占）、**模型自由**（--model 任意切，不绑定主 Agent 供应商）、**并行调度 + 结构化汇总**（一次派 6 个，统一收报告）。

**"模型自由"具体指什么？**
OpenCode 本身是 provider 中立的中转。你可以在 opencode 配置里接任意模型服务，oc-run 的子 Agent 就能用它们——包括主 Agent（如 Claude Code）供应商之外的 DeepSeek、GLM、Kimi、Grok、免费档，甚至自定义 provider 里的 Claude。高级模型只留给主 Agent 指挥，跑量的活交给便宜的。

**oc-run、oc-run-subagent、仓库名是什么关系？**
命令叫 `oc-run`，skill 名叫 `oc-run-subagent`（skill 目录名与 SKILL.md 的 `name` 一致），GitHub 仓库名 `oc-run`。装好 skill 后，用命令、用 skill 触发都指向同一个工具。

## 文件结构

```
oc-run/                      # 仓库名；作为 skill 安装时重命名为 oc-run-subagent
├── SKILL.md                 # 面向 AI 智能体的 skill 定义（name: oc-run-subagent）
├── README.md                # 简体中文说明文件（主文档）
├── README_en.md             # 英文说明文件
├── LICENSE                  # MIT
├── scripts/
│   └── oc-run.py            # 主脚本（纯 Python 标准库，零依赖）
└── examples/
    └── tasks.example.json   # 批量任务文件模板
```

## License

MIT
