# Serendipity Engine — MVP 架构（施工图）

**约束：1 个后端 dev / 3-5 天 / Live 全流程 Demo**

---

## Demo 全流程（观众看到的）

```
① 用户 A 导入 ChatGPT Memory → Agent 提取画像 → 用户审批
② 用户 B 同上
③ Agent A 在链上注册 → 发布静态画像
④ Agent A 发现 Agent B → 读取 B 的画像 → 本地评估"值得认识"
⑤ Agent A 向 Agent B 发起协商 → 多轮对话 → 达成共识 → 签 Pact
⑥ 两个用户各自收到通知 → 同意 → 进入 Telegram 群
⑦ 群里任务开始 → 完成 2-3 个任务
⑧ 宝箱解锁 → 看到 Pact
```

观众视角：从 raw memory 到宝箱打开，全程 live。

---

## 残忍的 Scope Cut：什么真的跑 vs 什么是预置的

| 步骤 | 真的跑 | 预置/简化 | 砍掉 |
|------|--------|----------|------|
| Memory 导入 | ✅ 读 ChatGPT 导出文件 | 只支持 ChatGPT JSON | Claude/Gemini 不做 |
| 隐私分层 | ✅ LLM prompt 分类 L1/L2/L3 | 不做用户手动调整界面 | 无 fine-tuned 模型 |
| 画像提取 | ✅ LLM 生成结构化画像 | — | — |
| 用户审批 | ✅ Telegram 里确认 | 简化为 yes/no，不做逐条编辑 | — |
| ERC-8004 注册 | ✅ 测试网上铸 NFT + 发布 agentURI | 用预部署的合约 | 不自己写合约 |
| 静态画像发布 | ✅ JSON 文件上传（IPFS 或 HTTPS）| — | — |
| Discovery 爬取 | ❌ 不做自动爬取 | **预置：Agent A 直接知道 Agent B 的地址** | 全自动 Discovery |
| 兼容性评估 | ✅ Agent A 用 LLM 评估 B 的画像 | — | Embedding 计算 |
| Agent 协商 | ✅ A2A 直接 HTTPS 对话 | 简化为 2 轮（bridge check + expansion map）| 多轮复杂协商 |
| Adjacent Possible 判断 | ✅ LLM 直接判断 | 不建知识图谱 | — |
| Pact 生成 | ✅ 两个 Agent 共同生成 | — | — |
| Pact 存储 | 双方 Agent 本地各存一份 | — | IPFS/链上存储 |
| 匹配通知 | ✅ Telegram 私信 | — | — |
| 群聊创建 | ✅ Telegram Bot 自动创建 | — | — |
| 任务投放 | ✅ 3 个任务（Spark×2 + Depth×1）| 模板 + Agent 填参数 | 完整 8 个任务 |
| 进度系统 | 简化为任务完成计数 | 不做连接度评分 | 动态权重 |
| 宝箱揭示 | ✅ Web 页面展示 Pact | 简单 HTML | 动画/交互 |
| Reputation | ❌ 不做 | demo 讲中提及 | — |
| 偏好调整 | ❌ 不做 | demo 讲中提及 | — |
| Discovery 经济机制 | ❌ 不做 | 文档描述 | — |

---

## 实际要 Build 的东西（4 个组件）

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  组件 1: OpenClaw Skill                                  │
│  ───────────────────                                     │
│  运行在每个用户的 OpenClaw 上                              │
│                                                          │
│  功能:                                                   │
│  a) 读 ChatGPT Memory 导出 JSON                         │
│  b) LLM 调用: 隐私分层 (L1/L2/L3)                       │
│  c) LLM 调用: 生成结构化画像                              │
│  d) 调 ERC-8004 合约: 注册 Agent + 发布静态画像           │
│  e) 读取对方 Agent 的静态画像                             │
│  f) LLM 调用: 评估兼容性 (bridge + adjacent possible)    │
│  g) A2A 协商: 向对方发起/接受协商请求                     │
│  h) LLM 调用: 参与协商对话 + 生成 Pact                   │
│  i) 在 Telegram 群里作为 Agent 参与任务                   │
│                                                          │
│  技术: Python (OpenClaw Skill 格式)                      │
│  LLM: OpenClaw 配置的模型 (GPT-4o / Claude)              │
│                                                          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                                                          │
│  组件 2: ERC-8004 链上交互                                │
│  ─────────────────────                                   │
│  不写新合约——直接用已部署的 Identity Registry              │
│                                                          │
│  功能:                                                   │
│  a) register(): 铸 NFT, 获得 agentId                    │
│  b) setAgentURI(): 指向静态画像 JSON                     │
│  c) 读取其他 agent 的 agentURI                           │
│                                                          │
│  技术: ethers.js / web3.py 调用 Sepolia 测试网           │
│  合约地址: 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432    │
│  (Identity Registry on Sepolia)                          │
│                                                          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                                                          │
│  组件 3: Telegram Bot                                    │
│  ────────────────────                                    │
│  我们运营的唯一中心化组件                                  │
│                                                          │
│  功能:                                                   │
│  a) 接收用户注册 (连接 OpenClaw Agent 和 Telegram ID)     │
│  b) 画像审批流程 (发送画像 → 接收 yes/no)                │
│  c) 匹配通知 (发送对方 L1 画像 → 接收同意/拒绝)          │
│  d) 创建群聊 (拉两个用户 + 两个 Agent)                   │
│  e) 投放任务 (按模板 + Agent 填充的参数)                  │
│  f) 追踪任务完成 (用户在群里回复即算完成)                  │
│  g) 宝箱触发 (3 个任务完成 → 发送宝箱链接)               │
│                                                          │
│  技术: Python (python-telegram-bot)                      │
│                                                          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                                                          │
│  组件 4: Treasure Chest 页面                              │
│  ──────────────────────────                              │
│  一个静态 web 页面, 展示 Pact 内容                        │
│                                                          │
│  功能:                                                   │
│  a) 接收 Pact ID 参数                                    │
│  b) 展示: Agent 对话还原 + Expansion Map + 预测           │
│  c) 简单的"打开"动画                                     │
│                                                          │
│  技术: 纯 HTML/CSS/JS, 静态托管                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 1 个后端 Dev 的 3-5 天排期

**前提：你（Tars）负责所有 LLM prompt 设计、产品逻辑、demo 脚本。**
**如果团队里有前端，Treasure Chest 页面可以分出去。**

### Day 1: 地基
- 搭 OpenClaw Skill 骨架（SKILL.md 格式、基本文件结构）
- 搭 Telegram Bot 骨架（注册、基本命令响应）
- 跑通: 用户在 Telegram 发消息 → OpenClaw Skill 收到 → 回复

### Day 2: 画像提取链路
- 实现 Memory 导入（读 ChatGPT JSON）
- 实现隐私分层 + 画像提取（LLM 调用链）
- 实现画像审批（Telegram Bot 发送画像 → 用户确认）
- 跑通: 导入 memory → 自动提取画像 → 用户在 Telegram 审批

### Day 3: 链上注册 + 协商
- 实现 ERC-8004 注册（调 Sepolia 合约, 铸 NFT, 设 agentURI）
- 实现静态画像 JSON 生成 + 上传（先用简单 HTTPS 托管）
- 实现 A2A 协商（两个 Skill 实例之间的 HTTP 对话）
- 实现 Pact 生成
- 跑通: 两个 Agent 注册 → Agent A 读 B 的画像 → 协商 → Pact 生成

### Day 4: 游戏流程
- 实现匹配通知 + 用户同意
- 实现群聊创建
- 实现 3 个任务模板 + Agent 参数填充 + 投放
- 实现任务完成追踪 + 宝箱触发
- 跑通: 通知 → 同意 → 群聊 → 任务 → 宝箱链接

### Day 5: 联调 + Treasure Chest + Demo 练习
- Treasure Chest 页面（或分给前端）
- 全流程联调 with 2 个真实测试用户
- 修 bug
- Demo 排练

---

## Demo 脚本（5 分钟）

```
[0:00] 开场
"每段好的关系都始于一个不太可能的巧合。
 我们把这个巧合工程化了。"

[0:30] 导入 Memory
现场展示: 把一份真实的 ChatGPT Memory 导入 OpenClaw
→ Agent 自动分层 (L1/L2/L3)
→ 提取画像
→ 用户在 Telegram 里审批

[1:30] 链上注册
"你的 Agent 现在在 ERC-8004 上有了身份。
 它的公开画像对全世界的 Agent 可见。"
现场展示: Etherscan 上看到注册的 NFT + agentURI

[2:00] Discovery + 协商
"Agent A 发现了 Agent B。它读了 B 的画像，
 判断值得深入了解。两个 Agent 开始对话。"
现场展示: Agent 协商的实时 log
→ 找到 bridge (共鸣基础)
→ 评估 adjacent novelty (可扩展空间)
→ 达成共识 → Pact 生成

[2:45] 匹配通知 + 进入游戏
现场展示: 用户收到 Telegram 通知
→ 看到对方的 L1 画像
→ 同意
→ 自动被拉进群聊

[3:15] 任务
现场展示: Agent 在群里发布第一个任务
"你们都对 [X] 有强烈观点。说出你最反主流的看法。"
→ 快速演示一个任务完成的流程

[4:00] 宝箱
现场展示: 宝箱页面打开
→ Agent 的对话还原
→ "我们相信你们应该认识，因为...
   你们的共鸣基础是 [bridge]。
   A 能给 B 的新世界是 [adjacent novelty]。
   B 能给 A 的新世界是 [adjacent novelty]。"

[4:30] 收尾
"最好的关系感觉像命运。
 但命运可以被工程化。
 Serendipity Engine: 你的 Agent 替你找到了那个人，
 然后设计了一场游戏让你自己去认识对方。"

[5:00] Q&A
```

---

## 3 个 MVP 任务模板

只做 3 个，全部跑通比做 8 个半成品重要。

### 任务 1: 反主流宣言 (Spark)
```
模板: "你们都对 {domain} 有强烈看法。
      各自说出你在这个领域最反主流的观点。"

Agent 填充: {domain} — 从两人 L1 画像的共同兴趣中选取

完成条件: 双方都在群里发了回复
```

### 任务 2: 3首歌盲盒 (Spark)
```
模板: "各自分享 3 首最近单曲循环的歌。
      从对方的 3 首里选一首你最想聊的。"

Agent 填充: 无（通用任务）
Agent 介入: 对方选完后, Agent 分享一条洞察
            "有意思, 你们对 {genre} 的品味有微妙的交集。"

完成条件: 双方都分享了 + 双方都选了对方的一首
```

### 任务 3: 你想被问的问题 (Depth)
```
模板: Agent 私聊用户 A: "有没有一个你特别希望有人问你的问题？"
      Agent 私聊用户 B: 同上
      然后 Agent 在群里对 B 提出 A 的问题, 对 A 提出 B 的问题

Agent 填充: Agent 微调问题的措辞, 让对方更容易切入

完成条件: 双方都回答了对方的"梦想问题"
```

---

## LLM Prompt 清单（Tars 负责）

你需要写 5 个核心 prompt, 每个都需要仔细调试:

| Prompt | 输入 | 输出 | 优先级 |
|--------|------|------|--------|
| 隐私分层 | ChatGPT Memory 原文 | 每条标记 L1/L2/L3 | P0 |
| 画像提取 | 分层后的 Memory | 结构化画像 JSON (demographics, personality, interests, values, attraction_signals) | P0 |
| 兼容性评估 | A 的完整画像 + B 的 L1 画像 | bridge nodes + adjacent novelty + alien count + 是否值得协商 | P0 |
| 协商对话 | 双方画像 + 兼容性评估 | 多轮对话 + 最终 Pact 文本 | P0 |
| 任务参数化 | 双方画像 + 任务模板 | 填充后的任务文本 + Agent 洞察 | P1 |

---

## 风险 & 备选方案

| 风险 | 概率 | 后果 | 备选 |
|------|------|------|------|
| ERC-8004 Sepolia 合约调用有问题 | 中 | 链上注册跑不通 | 退化为本地 JSON 文件模拟注册, demo 时用 Etherscan 截图展示"这是我们会用的合约" |
| A2A 协商的两个 OpenClaw 实例网络不通 | 中 | Agent 无法直接对话 | 退化为通过一个轻量中间 API 转发消息（本质上是个消息队列, 几十行代码）|
| LLM 画像提取质量不稳定 | 高 | demo 时画像太泛或太离谱 | 准备 2-3 份预调试好的 Memory 文件, demo 时用这些。现场"导入"但其实 Agent 之前已经调试过这些 Memory |
| 3-5 天做不完 | 中 | 全流程缺环节 | Day 3 结束时评估: 如果链上注册没跑通, 砍掉 ERC-8004, 全部本地化, 文档里讲链上愿景 |

---

## 团队分工建议

| 人 | 负责 | 产出 |
|----|------|------|
| **后端 Dev** | OpenClaw Skill + ERC-8004 调用 + A2A 协商 + Telegram Bot | 4 个组件全部能跑 |
| **Tars (你)** | 5 个 LLM Prompt 设计调试 + 产品逻辑 + Demo 脚本 + Pitch | Prompt 库 + Demo 脚本 |
| **前端 (如果有)** | Treasure Chest 页面 | 1 个 HTML 页面 |
| **其他成员** | 测试用户 + 准备 Memory 数据 + Pitch deck 辅助 | 测试反馈 + 素材 |
