---
name: oc-run
description: OpenCode 子 Agent 调度器（中转站）——把多个"工作区目录 + 提示词"任务并行派给 opencode 子 Agent（≤6 个），完成后自动汇总每个子 Agent 的 session、动作次数、最终报告；支持 --session 续跑同一子 Agent（保持上下文多轮迭代）和跨项目 session 历史查询。当用户提到 oc-run、opencode 中转站、并行派子 Agent、批量调度 opencode、opencode 子 Agent、续跑 opencode session、token 外包搜索时使用。
version: 1.0.0
license: MIT
---

# oc-run — OpenCode 子 Agent 调度器

oc-run 是主 Agent 与 opencode 子 Agent 之间的调度接口：给出若干"工作区目录 + 提示词"，它并行派发给独立子 Agent，完成后返回结构化汇总（每个子 Agent 的 session、动作次数、最终报告）。子 Agent 的搜索、读码、思考都在隔离环境完成，不占主 Agent 上下文；支持 `--session` 续跑同一子 Agent，保持它的记忆做多轮迭代。

## 安装

前置要求：opencode CLI（`npm i -g opencode-ai` 或按 opencode 官方方式安装）+ Python 3.9+。

```bash
# 把 oc-run.py 放进 PATH（示例：软链到 ~/.local/bin）
ln -s "$(pwd)/oc-run.py" ~/.local/bin/oc-run
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

# 机器可读输出（给 LLM / 脚本消费）
oc-run --dir /path/A --prompt "..." --json

# 指定模型（不传则用 opencode 默认模型）
oc-run --dir /path/A --prompt "..." --model opencode-go/deepseek-v4-pro
```

完整参数见 `oc-run --help`（输出面向 LLM 的中文使用说明）。

## 从 LLM / Agent 中调用

把 oc-run 当作可外包的执行单元，报告是唯一接口。两种推荐用法：

1. **token 外包（单轮）——大量读、简洁报**：派临时子 Agent 去读海量资料（网页/代码/文档），回报只要简洁结论+来源。子 Agent 独立上下文，读再多也不占你的上下文。
2. **主从循环（多轮）——强模型指挥弱模型**：用 `--session` 续跑同一子 Agent（保持记忆），按每次回报决定下一轮，循环直到结果达标。两条铁律：
   - 任务描述要详细：子 Agent 没有你的全局视野，prompt 就是它的世界
   - 回报格式要明确：你只能看到报告/最后发言——回报至少包含 结论 + 来源 + 不确定性 + 未完成项 + 关键函数或举措

两种用法均可并行（一次派多个，≤6）、可异步（借宿主环境如 ZCode / Claude Code 的后台任务机制，完成自动通知）。

## 已知坑（opencode 版本相关）

- **原生 `opencode run --session <id>` 非交互续跑在 1.18.15 会挂起**（零输出）：oc-run 已通过 `opencode serve` + `--attach` 绕开，无需手动处理。
- **`opencode session list` 只显示当前 project 的 session**（cwd 非 git 时归 global，会漏掉其他 git 项目的 session）：oc-run 的 `--sessions` 直接查 opencode 的 SQLite（`opencode.db`）跨项目列出全部，失败时自动降级回退。

## License

MIT
