# 系统架构

> 用途：定义 Engineered Serendipity 的技术架构，包括模块职责、数据结构、模块间协作方式。
> 原则：Prompt 是无状态函数。所有状态管理、规则判断、流程编排都是确定性代码。
> 依据：基于 mvp-spec.md 的产品设计推导。

## 1. 架构总览

```
┌─────────────────────────────────────────────────────┐
│                   Presentation                       │
│            渲染森林 / 树 / 枝桠 / 对话界面              │
└──────────────────────┬──────────────────────────────┘
                       │ 读取
┌──────────────────────▼──────────────────────────────┐
│                   State Store                        │
│  Forest / Tree / Branch / MemoryFragment / Placement │
│  ConversationSession                                 │
└──┬────────────────┬──────────────────┬──────────────┘
   │ 写入           │ 读取/写入         │ 写入
   │                │                  │
┌──▼─────────┐  ┌───▼──────────┐  ┌───▼──────────┐
│  Game      │  │   Convo      │  │   Event      │
│  Rules     │  │   Manager    │  │   Bus        │
│  Engine    │  │              │  │              │
└──▲─────────┘  └───┬──────────┘  └───▲──────────┘
   │                │                  │
   │  "该结束吗？"    │ 调用              │ 发事件
   │  "该提取吗？"    │                  │
   │                │                  │
   │           ┌────▼──────────┐       │
   └───────────┤  AI Pipeline  ├───────┘
               │  P1 ... P6    │
               └───────────────┘
```

### 核心设计决策

**统一交互管道：** 用户不管在 profile tree 还是 pvp tree，本质上都在和自己的 Claw 对话。对话产出记忆碎片，Claw 根据当前场景的规则把碎片放到树上。场景是变量，管道是统一的。

```
任何场景下：

用户 ↔ Claw 对话（场景不同，Claw 的引导策略不同）
       │
       ▼
   记忆碎片（独立资产）
       │
       ▼
   Claw 根据场景规则更新树
```

**为什么 Prompt 必须无状态：** Prompt 贵、慢、不确定。不能让非确定性的东西管状态。Prompt 只负责"需要语义理解"的环节——接受结构化输入，返回结构化 JSON。所有状态转换、条件判断由确定性代码完成，可写单元测试。

---

## 2. State Store（数据层）

整个游戏的 source of truth。所有其他模块读写这里。六个实体，各自独立。

### Forest

```
Forest
  user_id
  trees: [tree_id]
```

### Tree

```
Tree
  id
  type: "profile" | "pvp"
  participants: [user_id]          // profile 树 1 人，pvp 树 2 人
  status: "inactive" | "active"    // pvp 树创建时 inactive，点亮后 active；profile 树始终 active
  branches: [branch_id]
  maturity_score: number | null    // 计算方式待定，先留接口
  last_activity_at
  created_at
```

**关于 type 字段：** Profile 树只有一棵，其余全是 PVP 树。保留 type 字段的原因：(1) 森林视图统一遍历所有树来渲染，不需要合并两种数据源；(2) Profile 树和 PVP 树的规则差异显著（见 §4 Game Rules），type 是告诉规则引擎用哪套规则的最显式方式。

**关于 participants：** PVP 树属于一段关系，不属于某个人。双方对称，没有 owner/peer 之分。"谁表达的"只存在于 branch 级别的 author 字段。

**关于 maturity_score：** 不在 schema 里定义怎么算。Maturity 是一个可插拔的计算函数（见 §4），其他模块只关心这个数字和 `isReadyToMeet()` 的布尔值。等有真实数据再定义计算方式。

### Branch

```
Branch
  id
  tree_id
  parent_branch_id: null | id     // null = 一级枝桠
  author: user_id                 // 谁的表达长出了这个枝桠
  title:
    subjective: string            // 主态，表达者看到
    objective: string | null      // 客态，对方看到。profile 树无此字段
  description: string             // 仅表达者可见
  state: "single" | "bilateral"   // profile 树所有枝桠永远 single
  children: [branch_id]
  created_at
```

### MemoryFragment

```
MemoryFragment
  id
  raw_text                        // 用户原话
  summary
  topics: []
  source_session_id               // 从哪次对话来的
  created_at
```

**记忆碎片是独立资产。** 不属于任何树。它被"放置"到树上的关系由 Placement 实体记录。一个碎片可以同时影响多棵树——这是 spec §3 "一次表达的价值被放大到多段关系" 的数据基础。

### Placement

```
Placement
  id
  fragment_id
  tree_id
  branch_id
  action: string                  // 具体枚举待定义
  created_at
```

### ConversationSession

```
ConversationSession
  id
  user_id
  context:
    type: "profile_setup" | "pvp_branch" | "claw_proactive"
    tree_id: id | null            // pvp_branch 时指向哪棵树
    branch_id: id | null          // pvp_branch 时指向哪个枝桠
  turns: [{ role, content, timestamp }]
  fragments_generated: [fragment_id]   // 这次对话产出了哪些碎片
  status: "active" | "completed"
  created_at
```

**Conversation 是用户和自己 Claw 之间的对话记录。** 不是全局的东西，也不和某棵树绑定。它是 Claw 对话引擎的内部状态，P1 用它来生成连续的好问题。按 session 分组，每个 session 有一个 context 标记当前场景。

---

## 3. Convo Manager（对话编排）

**管所有用户和 Claw 的对话。** 是用户唯一的交互入口。

### 职责

1. 创建 / 管理 ConversationSession
2. 每轮对话后：
   - 调 AI Pipeline 生成 Claw 的下一句话（P1）
   - 问 Game Rules：该提取碎片了吗？
     - 是 → 提取 MemoryFragment，存入 State Store
     - 问 Game Rules：这个碎片怎么影响树？
     - 调 AI Pipeline 执行（P2 或 P5，取决于场景）
     - 写入 Placement
   - 问 Game Rules：该结束对话了吗？
     - 是 → 结束 session，发 Event

### 不管的事

- 具体的密度判断逻辑（问 Game Rules）
- 具体的结束条件（问 Game Rules）
- 枝桠 title 怎么生成（调 AI Pipeline）

### 场景差异

Convo Manager 根据 session context 走不同的流程，但管道结构相同：

| 场景属性 | profile_setup | pvp_branch | claw_proactive |
|---------|--------------|------------|----------------|
| Claw 怎么开口 | 开放式探索 | 围绕这个枝桠的话题 | 围绕推送主题 |
| 什么时候提取碎片 | 密度判断（已定义） | 待定 | 待定 |
| 什么时候结束 | 枝桠数 >= 3 | 待定 | 待定 |
| 碎片怎么影响树 | P2 生成新枝桠 | P5 更新枝桠状态 + 可能生子枝桠 | 可能生新枝桠 |

**架构上不需要现在定义所有结束条件。** 只需要保证规则是可插拔的：

```
// Convo Manager 每轮结束后
const rule = gameRules.getSessionRule(session.context.type)
if (rule.shouldExtractFragment(session)) {
  extractAndPlace()
}
if (rule.shouldEnd(session, relevantTree)) {
  endSession()
}
```

先只实现 profile_setup 的规则，其他留接口。

---

## 4. Game Rules Engine（游戏规则）

**纯确定性代码，零 AI。** 所有状态转换、条件判断都在这里。可以写完整的单元测试。

### 密度判断

```
shouldExtractFragment(session) → bool

- profile_setup: 已定义（待具体化参数）
- pvp_branch: 待定义
- claw_proactive: 待定义
```

### 结束判断

```
shouldEndSession(session, tree) → bool

- profile_setup: tree.branches.length >= 3
- pvp_branch: 待定义
- claw_proactive: 待定义
```

### 状态转换

```
applyStateChange(tree, branch, action)

- single + 对方回应 → bilateral
- bilateral + 新信息 → 长子枝桠 (single)
```

### 成熟度（可插拔）

```
computeMaturity(tree) → number
// 先用最简版本（如枝桠总数），以后替换
// 其他模块只调这个函数，不关心内部逻辑

isReadyToMeet(tree) → bool
// return computeMaturity(tree) >= THRESHOLD
// THRESHOLD 也待定
```

### 枯萎

```
checkDecay(tree) → bool

- profile 树: 不枯萎
- pvp 树: 48h 无活动 → decay
```

### Placement 决策

```
whereToPlace(fragment, userForest) → Placement[]

- 一个碎片可以影响多棵树
- 可能需要调 AI Pipeline 来判断匹配度
```

### PVP 树点亮

```
checkAndActivateTrees(user) → void

触发时机：profile_setup_completed 事件
逻辑：找到该用户参与的所有 inactive PVP 树，检查对方 profile 是否 ready，是则点亮。
```

> **MVP 场景下的简化：** 用户 B 必须完成 profile setup 才能分享/邀请，所以 B 一定先于 A 完成。A 完成 profile 的瞬间，A-B 的 PVP 树就可以直接点亮，不存在"双方都没完成要互相等"的情况。保留通用检查逻辑是为了未来可能的匹配入口。

---

## 5. AI Pipeline（Prompt 层）

六个无状态函数。接受结构化输入，返回结构化 JSON。彼此不知道对方的存在。

### P1：对话引导

```
P1(conversation_history, known_profile, scene_context)
  → { claw_message, interview_strategy }

调用者：Convo Manager，每轮对话
```

### P2：枝桠生成（Profile 树）

```
P2(memory_fragment, tree_context)
  → { branch_title, branch_description }

调用者：Convo Manager，profile 树长枝桠时
```

### P3：PVP 树点亮

```
P3(profile_A, profile_B)
  → { initial_branches[] }

调用者：Game Rules，PVP 树激活时
```

### P4：PVP 对话开场

```
P4(branch, peer_profile_summary)
  → { claw_opening_message }

调用者：Convo Manager，用户点击 PVP 枝桠开始对话时
```

### P5：PVP 枝桠更新

```
P5(memory_fragment, branch_context, tree_context)
  → { state_change, new_title?, spawn_child? }

调用者：Convo Manager，PVP 树碎片影响枝桠时
```

### P6：主动推送

```
P6(forest_changes_since_last_push)
  → { push_message }

调用者：Event Bus，需要推送时
```

---

## 6. Event Bus（事件系统）

模块间的通知机制。MVP 阶段可以用简单的函数调用代替，不需要消息队列。

### 事件类型

| 事件 | 触发 | 响应 |
|------|------|------|
| `profile_setup_completed` | Convo Manager：profile 对话结束 | Game Rules：检查并点亮 PVP 树 |
| `tree_activated` | Game Rules：PVP 树从 inactive → active | Presentation：更新森林视图 |
| `branch_grew` | Convo Manager：新枝桠写入 | Presentation：更新树视图 |
| `fragment_placed` | Convo Manager：碎片放置到树上（可能多棵） | Presentation：更新受影响的树 |
| `session_ended` | Convo Manager：对话结束 | Presentation：更新对话状态 |
| `tree_decayed` | Game Rules：枯萎检查触发 | Presentation：更新树视觉 |

---

## 7. Presentation（展示层）

**只读 State Store，不写。** 所有写操作通过 Convo Manager 或 Event 触发。

### 职责

1. 渲染森林视图（profile 树居中，pvp 树围绕）
2. 渲染单棵树的枝桠结构
3. 渲染对话界面
4. 根据 `branch.author` + 当前用户决定显示主态/客态
5. 根据 `branch.state` 决定视觉样式
6. 根据 `tree.status` 决定树是否可交互（inactive 树置灰）

---

## 8. User Journey 推演

### 8.1 Profile Setup（新用户第一次进入）

**前提：** 用户 A 通过扫码/邀请链接进入，邀请者 B 已完成 profile setup。

```
系统创建：
  - A 的 Forest
  - A 的 Profile Tree (type: "profile", status: "active")
  - A-B 的 PVP Tree (type: "pvp", status: "inactive")

Presentation：
  A 看到两棵树，Profile 树可交互，PVP 树置灰
  不管点哪棵，引导去完成 profile setup
          │
          ▼
Convo Manager 创建 session(context: { type: "profile_setup" })
          │
          ▼
调 P1(history: [], known_profile: {}, scene: "profile_setup")
  → P1 返回 Claw 的第一句话
  → Presentation 显示
          │
          ▼
用户回答："我最近开始去攀岩"
          │
          ▼
Convo Manager 更新 session.turns
          │
          ├─→ 调 P1 → 返回 Claw 下一句话 → 显示
          │
          └─→ Game Rules: shouldExtractFragment(session)?
                │
                ├─ 不够 → 等下一轮
                └─ 够了 → 提取 MemoryFragment → 存 State Store
                           │
                           ├─→ 调 P2(fragment, profile_tree_context)
                           │   → P2 返回 { title: "把杂音关掉的周末", description: "..." }
                           │   → Game Rules 写入新 Branch
                           │   → 写入 Placement
                           │   → Event: branch_grew
                           │   → Presentation: 用户看到枝桠长出来 ← 核心奖励时刻
                           │
                           └─→ (profile 阶段不做跨树 placement)

...重复，直到...

Game Rules: shouldEndSession(session, profile_tree)?
  → profile_tree.branches.length >= 3 → 是
  → Convo Manager 结束 session
  → Claw 说毕业台词
  → Event: profile_setup_completed
```

### 8.2 PVP 树点亮

**前提：** 紧接 8.1，A 刚完成 profile setup。B 早已完成。

```
Event: profile_setup_completed (user: A)
          │
          ▼
Game Rules: checkAndActivateTrees(A)
  → 找到 A 参与的所有 inactive PVP 树
  → A-B 树：B 的 profile ready 吗？→ 是（B 必须完成才能邀请）
          │
          ▼
调 P3(A 的 profile, B 的 profile)
  → P3 返回 initial_branches[]
    示例：[
      { title: "你们都喜欢用身体换安静", state: "bilateral" },
      { title_objective: "[她]在厨房里找创造力", state: "single", author: B }
    ]
          │
          ▼
Game Rules 执行：
  - A-B Tree: inactive → active
  - 写入 initial branches
  → Event: tree_activated
          │
          ▼
Presentation: 双方森林里 A-B 树从灰色变活，展示第一批枝桠
```

### 8.3 PVP 树生长（枝桠交互）

**前提：** PVP 树已激活，A 看到 B 的单边枝桠。

```
A 在森林里点进 A-B 树
  → Presentation 渲染：
    - 双边枝桠（正常显示）
    - B 的单边枝桠（客态 title）← 可点击
    - A 的单边枝桠（主态 title）

A 点击 B 的单边枝桠 "[她]在厨房里找创造力"
          │
          ▼
Convo Manager 创建 session(context: {
  type: "pvp_branch",
  tree_id: A-B 树,
  branch_id: 该枝桠
})
          │
          ▼
调 P4(branch, A_profile_summary)
  → P4 返回 Claw 的开场引导
  → 比如："你平时做饭吗？还是更像是偶尔心血来潮？"
  → Presentation 显示对话界面
          │
          ▼
A 回答："我不太做饭，但我很喜欢逛菜市场，看那些东西摆在一起"
          │
          ▼
Convo Manager 更新 session.turns
          │
          ├─→ 调 P1 → Claw 可能继续追问（取决于场景规则）
          │
          └─→ Game Rules: shouldExtractFragment(session)?
                │
                └─→ 是 → 提取 MemoryFragment → 存 State Store
                          │
                          ├─→ 当前树：调 P5(fragment, branch_context, tree_context)
                          │   → P5 返回：
                          │     {
                          │       state_change: "bilateral",
                          │       new_title: "你们用不同的方式泡在食物里",
                          │       spawn_child: { title: "逛菜市场的人", author: A, state: "single" }
                          │     }
                          │   → Game Rules 执行状态转换：
                          │     - 原枝桠 single → bilateral，title 更新
                          │     - 长出子枝桠 (single, author: A)
                          │   → 写入 Placement
                          │   → Event: branch_grew
                          │
                          └─→ 跨树 placement：
                              Game Rules: whereToPlace(fragment, A 的其他树)?
                              → 检查 A 的其他 PVP 树
                              → 如果有匹配 → 调 P2/P5 → 写入 Placement
                              → Event: fragment_placed（多棵树可能同时有变化）
          │
          ▼
Presentation:
  - A 看到枝桠从 single 变 bilateral，title 变了
  - 新的子枝桠长出来
  - 可能其他树也有新动态（森林视图更新）
  → 通知 B："你和 A 的树有新动态"
```

---

## 9. 已确定 vs 待定

| 领域 | 已确定 | 待定 |
|------|--------|------|
| **Schema** | 六个实体结构及字段 | Placement.action 枚举值 |
| **Game Rules** | profile_setup 结束条件（3 枝桠）、状态转换规则（single↔bilateral）、枯萎规则（profile 不枯萎、pvp 48h）、PVP 树点亮流程 | 密度判断具体参数、pvp_branch 和 claw_proactive 的结束条件、maturity 计算公式 |
| **AI Pipeline** | P1-P6 的输入输出契约、P1/P2 的 v0 prompt | P3-P6 的具体 prompt、所有 prompt 的输出 JSON schema 验证 |
| **Convo Manager** | 统一管道模型、场景路由机制 | 各场景下 Claw 的对话策略差异 |
| **Event Bus** | 事件类型定义 | MVP 是否需要独立实现，还是直接函数调用 |
| **Presentation** | 信息分层规则（主态/客态、三层分类）、森林布局概念 | 技术选型、具体交互形式 |
