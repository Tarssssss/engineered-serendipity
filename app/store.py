"""极简持久层:整个阶段 1 的状态就是一个 data.json 文件。

对照 architecture.md 的 Branch,这里只留了阶段 1 用得到的字段。
等阶段 3 真做双人时再加回 author / objective title / state 等。
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data.json"

_lock = threading.Lock()


def _empty_state() -> dict:
    return {
        "session": {"turns": []},
        "profile_tree": {"branches": []},
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load() -> dict:
    if not DATA_PATH.exists():
        return _empty_state()
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # 文件坏了不应该让游戏崩;退回空状态。
        return _empty_state()


def save(state: dict) -> None:
    DATA_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def reset() -> dict:
    state = _empty_state()
    save(state)
    return state


def add_turn(role: str, content: str) -> dict:
    """追加一轮对话(role: 'claw' | 'user')。"""
    with _lock:
        state = load()
        state["session"]["turns"].append(
            {"role": role, "content": content, "ts": now_iso()}
        )
        save(state)
        return state


def add_branch(title: str, description: str) -> dict:
    """长出一根枝桠,返回新枝桠。"""
    with _lock:
        state = load()
        branches = state["profile_tree"]["branches"]
        branch = {
            "id": f"b{len(branches) + 1}",
            "title": title,
            "description": description,
            "created_at": now_iso(),
        }
        branches.append(branch)
        save(state)
        return branch


def transcript(state: dict) -> str:
    """把 turns 渲染成喂给 prompt 的纯文本。"""
    lines = []
    for t in state["session"]["turns"]:
        speaker = "Claw" if t["role"] == "claw" else "用户"
        lines.append(f"{speaker}:{t['content']}")
    return "\n".join(lines)
