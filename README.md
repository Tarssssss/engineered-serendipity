# Engineered Serendipity

> 帮用户高效地认识陌生人，用树和枝桠承载关系中两人的相互了解。

## 项目是什么

一个社交匹配游戏。用户通过和自己的 AI agent（Claw）持续表达自己，让关系树不断生长。核心不是匹配算法，是匹配之后用户为什么愿意继续玩。

## 当前阶段

**MVP 产品设计阶段。** 在打磨用户旅程、核心玩法、信息架构。还没写代码。

## 核心体验

```
表达自己 → 树发生变化 → 对关系产生好奇 → 继续表达
```

用户最主要的动作是"提供记忆碎片"。树和枝桠把一次表达的价值放大到多段关系里。

## 文档结构

```
docs/
├── mvp-spec.md                  ← 核心：MVP 产品定义、用户旅程、枝桠机制、决策记录
├── implementation-roadmap.md    ← 实现路径：MVP-0 / MVP-1 分阶段计划
├── prompt-design-principles.md  ← Prompt 设计原则 + v0 prompt
└── prompts/
    ├── privacy-tiering.md       ← Profile 隐私分层 prompt
    └── profile-extraction.md    ← Profile 提取 prompt

test-data/
├── tiering-output.md            ← 隐私分层输出示例
├── profile-output.md            ← Profile 提取输出示例
├── tars-test-output.md          ← 测试用 profile 数据
└── personas/
    ├── soren.md                 ← 测试虚拟人格
    └── chloe.md                 ← 测试虚拟人格

archive/                         ← 黑客松历史文档，仅供参考
```

## 关键设计原则

1. **游戏设计层级**：设计目的 → 概念主题 → 预期体验 → 高光时刻 → 玩法概念 → 具体玩法 → 机制。底层不动摇顶层。
2. **从人的行为出发设计**，不从产品框架出发。
3. **枝桠只有两种状态**：单边和双边。接力式生长：用户回应包含新信息 → 自动长子枝桠。
4. **Claw 是天真好奇的数字生命**，不伪装有生活经验。追问要真诚深入，不挑衅不猜测。

## 待深入讨论的板块

- Claw 的具体 prompt 设计和问题策略（最高优先级）
- 树的结构规则：索引型枝桠 vs 叙事型枝桠
- 成熟度的具体数值设计
- PVP 树的生命周期：枯萎条件、放弃机制
- 见面后的体验设计
- 用户编辑权边界
- 行动面板详细设计
