"""阶段 1 后端:极小 FastAPI 服务。

两个 AI 接口 + 状态读写 + 托管单页。没有别的。
跑:  uvicorn app.main:app --reload   (在仓库根目录)
前提: 环境变量 ANTHROPIC_API_KEY 已设置。
"""

import json
import os
import re

from anthropic import Anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app import prompts, store

# 模型默认 Sonnet 4.6(快、够好)。枝桠如果觉得平,可在 env 里换成 claude-opus-4-8 试 P2。
MODEL = os.environ.get("ES_MODEL", "claude-sonnet-4-6")
GRADUATION_BRANCHES = 3  # 沿用 mvp-spec:长出 3 个枝桠即毕业

app = FastAPI(title="Engineered Serendipity · MVP-0 阶段 1")
_client: Anthropic | None = None


def client() -> Anthropic:
    global _client
    if _client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="没有设置 ANTHROPIC_API_KEY。先 export 一个再启动。",
            )
        _client = Anthropic()
    return _client


def _extract_json(text: str) -> dict:
    """从模型输出里抠出 JSON,容忍 ```json 代码块包裹。"""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        # 退而求其次:取第一个 { 到最后一个 }
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    return json.loads(text)


def call_llm(system: str, user_content: str, max_tokens: int = 1024) -> dict:
    """调一次 Claude,系统 prompt 走 prompt caching,返回解析后的 JSON。"""
    resp = client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=[
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ],
        messages=[{"role": "user", "content": user_content}],
    )
    raw = resp.content[0].text
    try:
        return _extract_json(raw)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=502, detail=f"模型没返回合法 JSON: {e}\n原始输出:{raw[:500]}"
        )


# ── 接口 ────────────────────────────────────────────────────────────────


class ChatIn(BaseModel):
    message: str = ""


def _state_view(state: dict) -> dict:
    branches = state["profile_tree"]["branches"]
    return {
        "turns": state["session"]["turns"],
        "branches": branches,
        "graduated": len(branches) >= GRADUATION_BRANCHES,
        "graduation_target": GRADUATION_BRANCHES,
    }


@app.get("/api/state")
def get_state():
    return _state_view(store.load())


@app.post("/api/chat")
def chat(body: ChatIn):
    msg = (body.message or "").strip()
    if msg:
        store.add_turn("user", msg)
    state = store.load()
    result = call_llm(
        prompts.P1_SYSTEM,
        prompts.build_p1_user(store.transcript(state), msg),
    )
    claw_message = result.get("question", "").strip()
    if not claw_message:
        raise HTTPException(status_code=502, detail="P1 没给出问题。")
    store.add_turn("claw", claw_message)
    return {
        "claw_message": claw_message,
        "move": result.get("interview_move", ""),
        "why_now": result.get("why_now", ""),
    }


@app.post("/api/sprout")
def sprout():
    state = store.load()
    if not state["session"]["turns"]:
        raise HTTPException(status_code=400, detail="还没聊过,先聊几句再生成枝桠。")
    result = call_llm(
        prompts.P2_SYSTEM,
        prompts.build_p2_user(store.transcript(state)),
    )
    title = result.get("title", "").strip()
    description = result.get("description", "").strip()
    if not title:
        raise HTTPException(status_code=502, detail="P2 没给出枝桠标题。")
    branch = store.add_branch(title, description)
    branches = store.load()["profile_tree"]["branches"]
    return {
        "branch": branch,
        "count": len(branches),
        "graduated": len(branches) >= GRADUATION_BRANCHES,
        "graduation_target": GRADUATION_BRANCHES,
    }


@app.post("/api/reset")
def reset():
    store.reset()
    return _state_view(store.load())


# 托管单页(放在最后,避免吃掉 /api 路由)
@app.get("/")
def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))
