# oc-run — OpenCode 子 Agent 调度器（AI skill）

> [English](./README_en.md) | 简体中文

oc-run 是**主 Agent 与 opencode 子 Agent 之间的调度接口**：给出若干"工作区目录 + 提示词"，它并行派发给独立子 Agent（≤6 个），完成后返回结构化汇总（每个子 Agent 的 session、动作次数、最终报告）。子 Agent 的搜索、读码、思考都在隔离环境完成，不占主 Agent 上下文；支持 `--session` 续跑同一子 Agent，保持记忆做多轮迭代。纯 Python 标准库，零第三方依赖。

## 下载与安装

### 面向 AI 智能体（一键安装，推荐）

**把下面这段提示词直接复制给你的本地 AI Agent（ZCode / Claude Code / Codex 等），它就能自动完成安装：**

````markdown
请帮我安装 oc-run skill（GitHub: https://github.com/RayMorTwinkle/oc-run）。

背景：oc-run 是 opencode 子 Agent 调度器——并行派活、自动汇总报告、支持 --session 续跑。
它依赖本机已安装的 opencode CLI（npm i -g opencode-ai）和 python3。

安装步骤：
1. 下载并解压（如果 ~/.agents/skills/oc-run 已存在则先跳过，直接验证）：
   curl -L -o /tmp/oc-run.zip https://github.com/RayMorTwinkle/oc-run/archive/refs/heads/main.zip
   unzip -o /tmp/oc-run.zip -d /tmp/ && mv /tmp/oc-run-main ~/.agents/skills/oc-run
   说明：~/.agents/skills/ 是多个 AI 工具共用的 skill 目录；如果你的平台用别的目录
   （如 Claude Code: ~/.claude/skills/，OpenCode: ~/.config/opencode/skills/），装到对应目录即可。
2. 验证 skill 结构：确认 ~/.agents/skills/oc-run/SKILL.md 和 scripts/oc-run.py 存在。
3. （可选但推荐）把 oc-run 命令放进 PATH，方便直接调用：
   ln -sf ~/.agents/skills/oc-run/scripts/oc-run.py ~/.local/bin/oc-run
4. 验证命令：oc-run --help 应输出中文使用说明；若 PATH 里没有，用 python3 ~/.agents/skills/oc-run/scripts/oc-run.py --help。
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
2. 将 `oc-run` 目录放入智能体的 skill 目录（Claude Code: `~/.claude/skills/`；OpenCode: `~/.config/opencode/skills/`；通用共享: `~/.agents/skills/`）
3. （可选）软链命令到 PATH：`ln -s "$(pwd)/oc-run/scripts/oc-run.py" ~/.local/bin/oc-run`

## 安装后验证

安装完成后，按顺序执行以下检查：

```bash
# 1. 依赖检查
python3 --version        # 需要 >= 3.9
opencode --version       # 需要已安装 opencode CLI

# 2. 命令可用性（若已软链到 PATH）
oc-run --help            # 应输出中文使用说明

# 3. 真实调用测试
oc-run --sessions 3      # 应列出最近 3 个 session（跨所有 git 项目）
```

## 快速开始

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

## 智能体日常使用

oc-run 命令本身是**自描述**的：`oc-run --help` 输出完整的中文使用说明（用法示例、参数说明、推荐用法、已知坑）。智能体在不确定用法时先跑 `oc-run --help` 即可，无需查阅本文档。

两种推荐用法：

1. **token 外包（单轮）——大量读、简洁报**：派临时子 Agent 去读海量资料（网页/代码/文档），回报只要简洁结论+来源。子 Agent 独立上下文，读再多也不占你的上下文；Flash 便宜，成本可忽略。
2. **主从循环（多轮）——强模型指挥弱模型**：用 `--session` 续跑同一子 Agent（保持记忆），按每次回报决定下一轮，循环直到结果达标。两条铁律：
   - 任务描述要详细：子 Agent 没有你的全局视野，prompt 就是它的世界
   - 回报格式要明确：你只能看到报告/最后发言——回报至少包含 结论 + 来源 + 不确定性 + 未完成项 + 关键函数或举措

两种用法均可并行（一次派多个，≤6）、可异步（借宿主环境如 ZCode / Claude Code 的后台任务机制，完成自动通知）。

## 已知坑（opencode 版本相关）

- **原生 `opencode run --session <id>` 非交互续跑在 1.18.15 会挂起**（零输出）：oc-run 已通过 `opencode serve` + `--attach` 绕开，无需手动处理。
- **`opencode session list` 只显示当前 project 的 session**（cwd 非 git 时归 global，会漏掉其他 git 项目的 session）：oc-run 的 `--sessions` 直接查 opencode 的 SQLite（`opencode.db`）跨项目列出全部，失败时自动降级回退。
- **PATH 精简环境**（cron / 脚本 / Agent 子进程）：oc-run 内置探测，`which` 落空时按常见路径（`~/.opencode/bin`、fnm node-versions、workbuddy、`~/.bun/bin`、homebrew）自动查找 opencode 并注入 PATH。

## 文件结构

```
oc-run/
├── SKILL.md                  # 面向 AI 智能体的 skill 定义（触发词/用法/已知坑）
├── README.md                 # 简体中文说明文件（主文档）
├── README_en.md              # 英文说明文件
├── LICENSE                   # MIT
├── scripts/
│   └── oc-run.py             # 主脚本（纯 Python 标准库，零依赖）
└── examples/
    └── tasks.example.json    # 批量任务文件模板
```

## License

MIT
