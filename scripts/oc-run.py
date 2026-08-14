#!/usr/bin/env python3
"""
oc-run — opencode 中转站（批量并行调度 + 结果汇总）

把若干"工作区目录 + 提示词"任务并行交给 opencode CLI 执行，
全部结束后自动解析 opencode 输出的 JSONL 事件流，汇总每个
Agent 的 session ID、动作次数、最终结果与 tokens 消耗。

无参数运行或 --help 输出详细使用说明（面向大模型）。
纯 Python 标准库，零第三方依赖。
"""

import argparse
import glob
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

PROG = "oc-run"
DEFAULT_MAX_PARALLEL = 6
MAX_PARALLEL_LIMIT = 6
DEFAULT_TIMEOUT = 900

HELP = f"""oc-run — 主 Agent 与 opencode 子 Agent 之间的调度接口
======================================================

你给出若干"工作区目录 + 提示词"，oc-run 并行派发给独立子 Agent，
完成后返回结构化汇总（每个子 Agent 的 session、动作次数、最终报告）。
子 Agent 的搜索、读码、思考都在隔离环境完成，不占你的上下文；
也支持 --session 续跑同一子 Agent，保持它的记忆做多轮迭代。

用法示例
--------
1) 单个任务（阻塞执行，跑完输出汇总）:
   {PROG} --dir /path/to/project --prompt "分析这个项目的技术栈"

2) 多个任务：工作目录与提示词一一对应（主用法，并行度默认 {DEFAULT_MAX_PARALLEL}、上限 {MAX_PARALLEL_LIMIT}）:
   {PROG} --dir /path/A --prompt "分析项目A" --dir /path/B --prompt "分析项目B"
   只给 1 个提示词则广播到所有目录: {PROG} --dir A --dir B --prompt "..."

3) 批量任务文件（每个任务自定义 dir / prompt / title）:
   {PROG} --tasks tasks.json   # 文件为 [{{"dir": "...", "prompt": "...", "title": "..."}}, ...]

4) 接着某个 session 的上下文继续跑（续跑）:
   {PROG} --sessions                                            # 查看历史 session
   {PROG} --dir /path/A --session ses_xxx --prompt "继续上次的分析"
   说明: 续跑经 opencode serve + --attach 实现；原生 run --session 有挂起 bug 勿用。
   续跑时 --dir 仅用于展示/校验，实际工作目录为 session 原属目录。

推荐用法
--------
1) token 外包（单轮）——大量读、简洁报:
   派临时 agent 去读海量资料（网页/代码/文档），回报只要简洁结论+来源。
   子 agent 独立上下文，读再多也不占你的上下文；Flash 便宜，成本可忽略。

2) 主从循环（多轮）——强模型指挥弱模型:
   用 --session 续跑同一 agent（保持它的记忆），按每次回报决定下一轮，
   循环直到结果达标。两条铁律:
   - 任务描述要详细：agent 没有你的全局视野，prompt 就是它的世界
   - 回报格式要明确：你只能看到报告/最后发言——回报至少包含
     结论 + 来源 + 不确定性 + 未完成项 + 关键函数或举措

两种用法均可并行（一次派多个，≤6）、可异步（借宿主环境如
ZCode / Claude Code 的后台任务机制，完成自动通知）

参数说明
--------
  --dir <path>        工作区目录，可重复指定
  --prompt <text>     提示词，可重复指定，与 --dir 按出现顺序一一对应
                      只给 1 个时广播到所有目录
  --session <id>      续跑指定 session（可重复；按顺序与前几个任务一一配对，
                      数量不能超过任务数；不可与 --tasks 同用）
  --sessions [N]      列出最近 N 个 session（默认 15；传大数如 9999 查全部）
                      后退出，--json 时输出 JSON
  --tasks <file>      任务文件（JSON），与 --dir/--prompt 二选一
  --max-parallel N    最大并行数，默认 {DEFAULT_MAX_PARALLEL}，上限 {MAX_PARALLEL_LIMIT}
  --model <m>         指定模型，格式 provider/model（默认用 opencode 配置）
  --timeout <sec>     单个任务超时秒数，默认 {DEFAULT_TIMEOUT}
  --json              汇总结果输出为 JSON（否则输出人类可读表格）
  --truncate <n>      人类可读输出中每条结果的最大字符数（默认不截断，
                      输出全文；给 Agent 消费时建议保持全文）

图片 / 文件输入
------------
  读图或附带文件无需额外参数：把文件路径写进提示词即可
  （如 "读取图片 /path/to/img.png 并描述内容"），子 Agent 会自行读取。
  已验证: opencode/mimo-v2.5-free 可识别图片内容。

行为说明
--------
- 自动携带 --dangerously-skip-permissions（自动批准工具权限）；
  只读分析类任务请勿让 agent 修改文件
- 单个任务失败（目录不存在 / 超时 / opencode 报错）不影响其他任务
- 汇总字段: session ID / 动作统计（按工具名）/ 最终文本 / tokens
"""


def parse_args(argv):
    p = argparse.ArgumentParser(add_help=False, prog=PROG)
    p.add_argument("--help", "-h", action="store_true", help="显示帮助")
    p.add_argument("--dir", action="append", default=[], metavar="<path>")
    p.add_argument("--prompt", action="append", default=[], metavar="<text>")
    p.add_argument("--session", action="append", default=[], metavar="<session_id>")
    p.add_argument("--sessions", nargs="?", type=int, const=15, metavar="N",
                   help="列出最近 N 个 session（默认 15）后退出")
    p.add_argument("--tasks", metavar="<file.json>")
    p.add_argument("--max-parallel", type=int, default=DEFAULT_MAX_PARALLEL)
    p.add_argument("--model", metavar="<provider/model>")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("--json", action="store_true")
    p.add_argument("--truncate", type=int, default=None, metavar="<n>",
                   help="人类可读输出中每条结果的最大字符数（默认不截断）")
    return p.parse_args(argv)


def build_tasks(args):
    """把参数展开为任务列表: [{"dir", "prompt", "title"}]"""
    tasks = []
    if args.tasks:
        if args.dir or args.prompt:
            sys.exit("错误: --tasks 与 --dir/--prompt 互斥，请二选一。\n")
        try:
            with open(args.tasks, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            sys.exit(f"错误: 找不到任务文件: {args.tasks}\n")
        except json.JSONDecodeError as e:
            sys.exit(f"错误: 任务文件不是合法 JSON（{e}）\n")
        raw = data.get("tasks", data) if isinstance(data, dict) else data
        if not isinstance(raw, list):
            sys.exit("错误: 任务文件需是数组，或 {\"tasks\": [...]} 结构。\n")
        for i, t in enumerate(raw):
            if not isinstance(t, dict) or "dir" not in t or "prompt" not in t:
                sys.exit(f"错误: 任务文件第 {i + 1} 项缺少 dir 或 prompt 字段。\n")
            tasks.append({
                "dir": t["dir"],
                "prompt": t["prompt"],
                "title": t.get("title") or f"任务{i + 1}",
            })
    else:
        if not args.dir:
            sys.exit(HELP + "\n\n错误: 至少需要 --dir 或 --tasks 之一。\n")
        if not args.prompt:
            sys.exit("错误: 需要至少一个 --prompt 提示词。\n")
        n_dir, n_prompt = len(args.dir), len(args.prompt)
        if n_prompt == 1:
            prompts = args.prompt * n_dir  # 单提示词广播到所有目录
        elif n_prompt == n_dir:
            prompts = args.prompt          # 一一对应（主用法）
        else:
            sys.exit(
                f"错误: --dir 有 {n_dir} 个、--prompt 有 {n_prompt} 个，数量不匹配。\n"
                "需一一对应（两者数量相等），或只给 1 个提示词广播到所有目录。\n")
        for d, p in zip(args.dir, prompts):
            tasks.append({
                "dir": d,
                "prompt": p,
                "title": os.path.basename(d.rstrip("/")) or d,
            })
    if args.session:
        if args.tasks:
            sys.exit("错误: --session 与 --tasks 不能同时使用。\n")
        if len(args.session) > len(tasks):
            sys.exit(
                f"错误: --session 有 {len(args.session)} 个、任务只有 {len(tasks)} 个。\n"
                "--session 按顺序与前几个任务配对，数量不能超过任务数。\n")
        for t, sid in zip(tasks, args.session):
            if not sid.startswith("ses_"):
                sys.exit(f"错误: session ID 格式不正确（应以 ses_ 开头）: {sid}\n")
            t["session"] = sid
    return tasks


def parse_events(stdout):
    """解析 opencode --format json 输出的 JSONL 事件流，忽略非 JSON 行"""
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def summarize(task, stdout, stderr, returncode):
    """从一个任务的输出中提取汇总字段"""
    events = parse_events(stdout or "")
    session_id = None
    actions = Counter()
    text_parts = []
    tokens_total = 0

    for ev in events:
        if not isinstance(ev, dict):
            continue
        if ev.get("sessionID"):
            session_id = session_id or ev["sessionID"]
        etype = ev.get("type")
        part = ev.get("part")
        if not isinstance(part, dict):
            part = {}
        if etype == "tool_use":
            tool = part.get("tool") or "?"
            actions[tool] += 1
        elif etype == "text":
            if part.get("text"):
                text_parts.append(part["text"])
        elif etype == "step_finish":
            tk = part.get("tokens") or {}
            tokens_total += tk.get("total", 0) or 0

    final_text = (text_parts[-1] if text_parts else "").strip()
    if returncode == 0 and session_id:
        status = "ok"
    else:
        status = "failed"

    return {
        "title": task["title"],
        "dir": task["dir"],
        "status": status,
        "session_id": session_id,
        "actions": dict(actions),
        "total_actions": sum(actions.values()),
        "final_result": final_text,
        "tokens": tokens_total,
        "exit_code": returncode,
        "stderr_tail": (stderr or "").strip()[-500:],
    }


def _task_error(task, status, message):
    """构造失败任务的汇总条目（统一字段结构）"""
    return {
        "title": task["title"], "dir": task["dir"], "status": status,
        "session_id": None, "actions": {}, "total_actions": 0,
        "final_result": message, "tokens": 0,
        "exit_code": None, "stderr_tail": "",
    }


def kill_tree(proc):
    """向进程组发 SIGTERM，连带 opencode 派生的孙进程"""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass


def run_task(task, model, timeout, serve_url=None):
    if task.get("session"):
        # 续跑模式: 通过 serve + attach 绕开原生 --session 的挂起 bug
        cmd = ["opencode", "run", "--attach", serve_url,
               "--session", task["session"], "--format", "json",
               "--dangerously-skip-permissions"]
    else:
        cmd = [
            "opencode", "run",
            "--dir", task["dir"],
            "--format", "json",
            "--title", task["title"],
            "--dangerously-skip-permissions",
        ]
    if model:
        cmd += ["--model", model]
    cmd.append(task["prompt"])

    try:
        # start_new_session: 独立进程组，超时后可按组清理孙进程
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True,
                                errors="replace", start_new_session=True)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            return summarize(task, stdout, stderr, proc.returncode)
        except subprocess.TimeoutExpired:
            kill_tree(proc)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            return _task_error(task, "timeout", f"超过 {timeout}s 未完成，已终止")
    except FileNotFoundError:
        return _task_error(task, "error", "找不到 opencode 命令，请先安装 (npm i -g opencode-ai)")
    except Exception as e:
        # 兜底: 任何异常都不应中断整批任务
        return _task_error(task, "error", f"执行异常: {e}")


# ── opencode serve 生命周期管理（续跑用）────────────────────────────

_serve_proc = None
_serve_url = None
_serve_lock = threading.Lock()


def find_free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get_serve():
    """懒启动一个 headless opencode server，所有续跑任务共用"""
    global _serve_proc, _serve_url
    with _serve_lock:
        # serve 中途崩溃则重置，下次重新启动
        if _serve_proc is not None and _serve_proc.poll() is not None:
            _serve_proc = None
            _serve_url = None
        if _serve_proc is None:
            port = find_free_port()
            _serve_proc = subprocess.Popen(
                ["opencode", "serve", "--port", str(port), "--print-logs"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True)
            url = f"http://localhost:{port}"
            ok = False
            for _ in range(30):
                if _serve_proc.poll() is not None:
                    break  # serve 进程提前退出 = 启动失败
                try:
                    urllib.request.urlopen(url + "/health", timeout=2)
                    ok = True
                    break
                except Exception:
                    time.sleep(1)
            if not ok:
                code = _serve_proc.poll()
                kill_tree(_serve_proc)
                _serve_proc = None
                raise RuntimeError(
                    f"opencode serve 启动失败（进程退出 exit={code}，或 30s 未就绪）")
            _serve_url = url
    return _serve_url


def stop_serve():
    global _serve_proc, _serve_url
    if _serve_proc is not None:
        kill_tree(_serve_proc)
        try:
            _serve_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(_serve_proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        _serve_proc = None
        _serve_url = None


# ── session 历史（--sessions）──────────────────────────────────────

def format_ts(ms):
    """epoch 毫秒 → 本地时间 MM-DD HH:MM"""
    try:
        return time.strftime("%m-%d %H:%M", time.localtime(ms / 1000))
    except (TypeError, ValueError, OSError):
        return str(ms)


def list_sessions(n):
    """列出最近 n 个 session。

    数据源: `opencode db` 直接查 SQLite（opencode.db），跨所有项目——
    `opencode session list` 只显示当前 project（含 global），会漏掉
    其他 git 项目的 session，不能用于子 Agent 派活场景。
    """
    n = max(0, min(n, 10000))  # 钳制 LIMIT：负数在 SQLite 中等于无上限
    query = (
        "SELECT s.id, s.title, p.worktree, s.time_updated, s.model "
        "FROM session s JOIN project p ON s.project_id = p.id "
        "WHERE s.time_archived IS NULL "
        f"ORDER BY s.time_updated DESC LIMIT {n}"
    )
    try:
        p = subprocess.run(["opencode", "db", query, "--format", "json"],
                           capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            raise RuntimeError(p.stderr.strip()[-200:] or f"exit {p.returncode}")
        rows = json.loads(p.stdout)
    except Exception as e:
        # 降级: 旧版 opencode 无 db 子命令或 schema 变化时，回退表格解析
        print(f"警告: opencode db 查询失败（{e}），回退 session list 解析", file=sys.stderr)
        return list_sessions_legacy(n)

    items = []
    for r in rows:
        model = None
        if r.get("model"):
            try:
                model = json.loads(r["model"]).get("id")
            except Exception:
                model = r["model"]
        items.append({
            "session_id": r["id"],
            "title": r["title"] or "(无标题)",
            "worktree": r["worktree"] or "/",
            "updated": format_ts(r.get("time_updated")),
            "model": model,
        })
    return items


def list_sessions_legacy(n):
    """旧路径: 解析 `opencode session list` 表格（仅当前项目的 session）"""
    p = subprocess.run(["opencode", "session", "list"],
                       capture_output=True, text=True, timeout=60)
    items = []
    for line in p.stdout.splitlines():
        m = re.match(r"^(ses_\S+)\s+(.*?)\s+(\d{1,2}:\d{2} [AP]M)$", line)
        if m:
            items.append({
                "session_id": m.group(1),
                "title": m.group(2).strip(),
                "worktree": "/",
                "updated": m.group(3),
                "model": None,
            })
    if not items:
        print("警告: session list 解析无结果（表格格式可能变化）", file=sys.stderr)
    return items[:n]


def print_sessions(items, as_json=False):
    if as_json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return
    print(f"oc-run 历史 session（最近 {len(items)} 条，跨所有项目）")
    for i, it in enumerate(items, 1):
        model = f" · {it['model']}" if it.get("model") else ""
        print(f"  [{i}] {it['session_id']}  {it['title']}{model}")
        print(f"       {it['updated']}  {it['worktree']}")
    print()
    print('续跑方法: oc-run --dir <目录> --session <session_id> --prompt "继续..."')


def truncate(text, n=200):
    text = " ".join(text.split())
    if n <= 1:  # 非法截断长度：直接返回原文
        return text
    return text if len(text) <= n else text[: n - 1] + "…"


def print_human(results, workers, truncate_n=None):
    n_ok = sum(1 for r in results if r["status"] == "ok")
    print(f"oc-run 汇总 · {len(results)} 个任务 · 并行度 {workers} · 成功 {n_ok}/{len(results)}")
    print("─" * 72)
    icons = {"ok": "✅", "failed": "❌", "timeout": "⏱", "error": "⚠️"}
    for i, r in enumerate(results, 1):
        icon = icons.get(r["status"], "·")
        print(f"{icon} [{i}] {r['title']}")
        print(f"    session: {r['session_id'] or '(无)'}")
        acts = " · ".join(f"{k}×{v}" for k, v in sorted(r["actions"].items())) or "(无工具调用)"
        print(f"    动作:   {r['total_actions']} 次 ({acts})")
        print(f"    tokens: {r['tokens']:,}")
        if r["status"] == "ok":
            res = r["final_result"] if not truncate_n else truncate(r["final_result"], truncate_n)
            print(f"    结果:   {res if res else '(无文本输出)'}")
        else:
            detail = r["final_result"] or r["stderr_tail"] or "未知错误"
            print(f"    错误:   {truncate(detail, 160)}")
        print()


def ensure_opencode():
    """确保 subprocess 能找到 opencode。

    环境 PATH 精简时（非交互 shell / 脚本 / cron），`which opencode`
    可能落空；按常见安装路径探测，命中后把所在目录注入 PATH。
    os.path.isfile 会自动过滤悬空软链（目标不存在返回 False）。
    """
    if shutil.which("opencode"):
        return True
    for pat in (
        "~/.opencode/bin",
        "~/.local/bin",
        "~/.local/share/fnm/node-versions/*/installation/bin",
        "~/.workbuddy/binaries/node/versions/*/bin",
        "~/.bun/bin",
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ):
        for d in glob.glob(os.path.expanduser(pat)):
            cand = os.path.join(d, "opencode")
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
                return True
    return False


def main():
    args = parse_args(sys.argv[1:])
    if args.help:
        print(HELP)
        return 0

    if not ensure_opencode():
        sys.exit("错误: 未找到 opencode 命令，请先安装 (npm i -g opencode-ai)。")

    if args.sessions is not None:
        print_sessions(list_sessions(args.sessions), as_json=args.json)
        return 0

    tasks = build_tasks(args)
    if not tasks:
        sys.exit("错误: 没有可执行的任务。\n")
    if args.max_parallel < 1:
        sys.exit("错误: --max-parallel 至少为 1。\n")
    if args.max_parallel > MAX_PARALLEL_LIMIT:
        print(f"警告: --max-parallel 超过上限 {MAX_PARALLEL_LIMIT}，已按上限执行", file=sys.stderr)
    if args.timeout < 1:
        sys.exit("错误: --timeout 至少为 1 秒。\n")
    workers = min(args.max_parallel, MAX_PARALLEL_LIMIT, len(tasks))

    serve_url = None
    if any(t.get("session") for t in tasks):
        try:
            serve_url = get_serve()
        except RuntimeError as e:
            sys.exit(f"错误: {e}")

    t0 = time.time()
    results = [None] * len(tasks)
    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(run_task, t, args.model, args.timeout, serve_url): i
                       for i, t in enumerate(tasks)}
            for fut in as_completed(futures):
                results[futures[fut]] = fut.result()
    finally:
        stop_serve()
    elapsed = time.time() - t0

    if args.json:
        print(json.dumps({
            "summary": {
                "total": len(results),
                "parallel": workers,
                "ok": sum(1 for r in results if r["status"] == "ok"),
                "elapsed_sec": round(elapsed, 1),
            },
            "tasks": results,
        }, ensure_ascii=False, indent=2))
    else:
        print_human(results, workers, args.truncate)
        print(f"总耗时: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
