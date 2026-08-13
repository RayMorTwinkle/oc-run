# oc-run

**OpenCode 子 Agent 调度器 / 中转站** — 把多个"工作区目录 + 提示词"任务并行派发给 opencode 子 Agent，完成后自动汇总每个子 Agent 的 session、动作次数与最终报告。

> oc-run 是主 Agent 与 opencode 子 Agent 之间的调度接口：子 Agent 的搜索、读码、思考都在隔离环境完成，不占主 Agent 上下文；支持 `--session` 续跑同一子 Agent，保持记忆做多轮迭代。纯 Python 标准库，零第三方依赖。

## 功能

- **并行派活**：一次派多个任务（默认并行 6、上限 6），各自独立工作目录 + 独立提示词（一一对应）
- **自动汇总**：解析 opencode JSONL 事件流，输出每个子 Agent 的 session ID、动作次数（按工具名分组）、最终报告、tokens
- **续跑（多轮迭代）**：`--session` 接着某子 Agent 的上下文继续跑，主 Agent 按报告循环指挥
- **跨项目历史**：`--sessions` 直接查 opencode 的 SQLite，列出所有 git 项目的 session（`opencode session list` 只能看到当前项目）
- **模型可选**：`--model provider/model` 任意指定（opencode 免费档 / opencode-go 主力档 / 自定义 provider 均可）
- **任意环境可跑**：内置探测，PATH 精简环境（cron / 脚本 / Agent 子进程）也能找到 opencode
- **机器可读**：`--json` 结构化输出，供 LLM / 脚本继续消费

## 安装

前置要求：opencode CLI（`npm i -g opencode-ai`）+ Python 3.9+。

```bash
git clone https://github.com/<your-name>/oc-run.git
ln -s "$(pwd)/oc-run/oc-run.py" ~/.local/bin/oc-run   # 放进 PATH
```

## 快速开始

```bash
# 单个任务
oc-run --dir /path/to/project --prompt "分析这个项目的技术栈"

# 多任务并行（目录与提示词一一对应，主用法）
oc-run --dir /path/A --prompt "分析项目A" --dir /path/B --prompt "分析项目B"

# 续跑某子 Agent（多轮迭代）
oc-run --sessions
oc-run --dir /path/A --session ses_xxx --prompt "继续上次的分析"

# 机器可读 + 指定模型
oc-run --dir /path/A --prompt "..." --json --model opencode-go/deepseek-v4-pro
```

完整参数与推荐用法见 `oc-run --help`（输出面向 LLM 的中文说明，本仓库同时是 Agent skill，见 [SKILL.md](SKILL.md)）。

## 推荐用法（给 LLM 的编排建议）

1. **token 外包（单轮）**：派临时子 Agent 去读海量资料（网页/代码/文档），回报只要简洁结论+来源——读再多不占主上下文，Flash 便宜成本可忽略。
2. **主从循环（多轮）**：用 `--session` 续跑同一子 Agent 保持记忆，按回报循环迭代直到达标。两条铁律：任务描述要详细（子 Agent 没有你的全局视野）；回报格式要明确（结论 + 来源 + 不确定性 + 未完成项 + 关键函数或举措，防虚假收敛）。

## 已知坑（opencode 版本相关）

- opencode 1.18.15 原生 `opencode run --session <id>` 非交互续跑会挂起（零输出）；oc-run 通过 `opencode serve` + `--attach` 绕开。
- `opencode session list` 只显示当前 project 的 session；oc-run 的 `--sessions` 直接查 `opencode.db`（SQLite）跨项目列出，失败自动降级。

## License

MIT
