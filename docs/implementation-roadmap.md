# 实现路径

> 从"大图景与清单"（2026-03-11）提取，记录 MVP 分阶段实现计划。
> mvp-spec.md 负责产品设计，这份文档负责"怎么落地"。

---

## MVP-0：单人 PvE 闭环

**定义：一个人装上 skill，就能和 NPC claw 玩森林游戏。**

必须成立的 5 件事：

1. 可以生成初始树（NPC 对手）
2. Claw 会来问问题
3. 用户回答后，树会生长
4. 枝桠标题和提示语是有意思的
5. 长时间不管，树会枯萎一点

### 为什么先做 MVP-0

验证最核心的问题：

1. 用户会不会回答
2. 树长出来的东西好不好玩
3. Prompt 质量到底够不够

如果这三件事不成立，联网也只是把一个不好玩的东西联网。

---

## MVP-1：双人异步试玩

**定义：两个用户都能通过 claw id 建立关系树，并通过异步事件交换让树继续生长。**

新增内容：

1. 用 claw id 建树
2. 一方更新后，产出可同步事件
3. 另一方拉取后，更新对应树

最薄数据交换格式：

```json
{
  "tree_id": "",
  "branch_id": "",
  "event_type": "new_sprout | answered | deepened | wilted",
  "public_payload": {},
  "teaser": ""
}
```

---

## 5 个最小模块

| # | 模块 | 作用 | 最低完成标准 |
|---|------|------|-------------|
| 1 | **握手入口** | 让树能被创建出来 | 输入 claw id 建树 / 选 NPC 建树 |
| 2 | **Interview Engine** | 让用户愿意持续提供记忆碎片 | Claw 生成自然问题，能追问 1 轮不崩 |
| 3 | **Memory Fragment Extraction** | 把自然语言变成系统可操作的碎片 | 每次回答后抽出 summary + topics + mode |
| 4 | **Placement Engine** | 决定碎片更新哪棵树、哪个枝桠 | 每次最多影响 1-2 棵树，placement 可解释 |
| 5 | **Branch Wording Engine** | 把更新转化成有趣的反馈 | 产出枝桠标题 + teaser + 问题钩子 |

---

## 最短路径

### 阶段 A：冻结边界

冻结 4 件事：MVP-0 定义、5 个最小模块、最小数据结构、明确不做的东西。

### 阶段 B：Prompt 先跑通

先调 3 个 prompt：Interview / Placement / Wording。
目标不是完美，而是能连续跑 5-10 轮而不崩。

### 阶段 C：收敛成单人闭环

让现有 demo 支持：NPC 树初始化 → 用户回答 → prompt 输出 placement → 树状态更新 → 文案反馈。

### 阶段 D：打包成 skill

Skill 只负责：启动游戏、调 prompt、写本地状态、输出森林更新。

### 阶段 E：补双人试玩

单人闭环能玩后，加最薄的双人事件同步。

---

## 6 个 Prompt 清单

| # | Prompt | 说明 | 优先级 |
|---|--------|------|--------|
| P1 | Profile 对话 | 引导用户做深度自我表达 | 最高，第一接触点 |
| P2 | Profile 枝桠生成 | 从用户原话提炼 title + description | 最高，和 P1 配套 |
| P3 | PVP 树点亮 | 对比两人 profile 生成第一批枝桠 | 中 |
| P4 | PVP 回应引导 | 引导深度回应 | 中 |
| P5 | PVP 枝桠更新 | 判断双边状态 + 生成新 title + 判断子枝桠 | 中 |
| P6 | Claw 主动推送 | 把变化包装成有温度的消息 | 低 |

**建议从 P1 + P2 开始**，因为是用户第一接触点，且可以立刻用真人测试。

---

## 记忆碎片最小数据结构

```json
{
  "summary": "",
  "topics": [],
  "mode": "answer | deepen | new_direction",
  "story_strength": 0,
  "intimacy_hint": "light | medium | deep"
}
```
