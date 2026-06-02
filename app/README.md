# 阶段 1:human-NPC,profile 树

MVP-0 的第一个可跑切片。规格见 [`../docs/mvp-0-spec.md`](../docs/mvp-0-spec.md)。

**它做的唯一一件事:** 你跟 Claw 聊天 → 点「生成枝桠」→ 看你说的话被转写成一根枝桠。
**它要验证的唯一假设(闸门 A):** 看着这些枝桠,你想不想继续说下去。

## 跑起来

```bash
# 1. 在仓库根目录,装依赖(建议用 venv)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. 给 key
export ANTHROPIC_API_KEY=sk-ant-...      # 见 .env.example

# 3. 启动
uvicorn app.main:app --reload

# 4. 打开浏览器
open http://127.0.0.1:8000
```

聊几轮 → 点右边「🌱 把刚才聊的长成一根枝桠」→ 长够 3 根就毕业。
「重新开始」清空 `data.json` 从头来(调 prompt 时常用)。

## 结构

| 文件 | 作用 |
|---|---|
| `prompts.py` | **你最常改这里。** P1(对话)和 P2(枝桠生成)的 prompt。闸门 A 成败全在 P2。 |
| `main.py` | FastAPI:`/api/chat`(P1)、`/api/sprout`(P2)、`/api/state`、`/api/reset`。 |
| `store.py` | 读写 `data.json`(在仓库根目录,已 gitignore)。 |
| `index.html` | 单页前端,原生 JS,无构建。 |

## 调 prompt 的循环

闸门 A 不过(枝桠平淡、不想继续说),**别往下做任何东西** —— 只改 `prompts.py` 里的 `P2_SYSTEM`,重开页面再试。
觉得模型不够强,把 `ES_MODEL=claude-opus-4-8` 试试 P2。

## 坚决不做(见 mvp-0-spec §6)

没有双人、没有森林视图、没有 PVP、没有成熟度/枯萎/推送、没有跨树 placement、没有数据库。
这些不是漏了,是阶段 1 故意不做。想加,先过闸门 A。
