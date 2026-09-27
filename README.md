# Human in the Love Loop

> The agent keeps the state. The human keeps the agency.

**Human in the Love Loop** 是一个本地优先、人工主导的关系决策 agent 实验。
它把程序员熟悉的 human-in-the-loop 原则带进约会场景：工具负责维护状态、检查阶段门、汇总漏斗和提示风险；本人负责判断、改写、同意与行动。

它不是自动代聊器，也不试图用一个 AI 人格替代真实的人。

## 核心原则

- **Human agency**：AI 只做教练、校对和复盘，不替用户发送消息或做关系决定。
- **State before vibes**：用显式状态、可观察事件和阶段门，代替“感觉应该推进了”。
- **Safety as a constraint**：安全、明确拒绝、边界、诚实和平台规则优先于转化优化。
- **Local and de-identified**：数据默认保存在本地，只接受代号和去标识摘要。
- **Optimize the loop, not the person**：指标用来改进流程与时间投入，不给人的价值打分。

## 系统轮廓

```text
真实输入
   ↓
隐私门 → 阶段状态机 → 风险与边界门 → 结构化复盘
   ↑                                      ↓
   └──────────── 人本人批准并行动 ────────────┘
```

内置阶段：

```text
matched → conversing → date_planned → dating → exclusive → relationship
```

工具不会自动推进阶段。公开安全的约会计划、实际完成见面、明确的双方同意等证据会成为进入下一阶段的门槛。

## 快速开始

需要 Python 3.11+，运行时零第三方依赖。

```powershell
python -m unittest discover -s tests -v
python -m dating_agent --data-dir private init
python -m dating_agent --data-dir private new-case --alias Q001
python -m dating_agent --data-dir private list
```

也可以安装可编辑版本后使用 `love-loop`：

```powershell
python -m pip install -e .
love-loop --data-dir private metrics
```

完整命令见 [快速开始](docs/quickstart.md)。

## 仓库内容

```text
dating_agent/       # 状态机、本地存储、隐私校验、复盘和 CLI
docs/               # 架构、决策策略、prompt 契约与 JSON Schema
examples/           # 完全匿名的示例数据
tests/              # 单元测试
```

这个仓库有意只保留 agent 系统实现。原项目中的产品调研、群体先验、个人盘点、资料/消息/约会手册、追踪数据和任何 `private/` 内容均不属于本仓库。

## 进一步阅读

- [Agent 架构](docs/architecture.md)
- [决策策略与阶段门](docs/decision-policy.md)
- [AI 教练调用契约](docs/prompt-contracts.md)
- [快速开始](docs/quickstart.md)

## 隐私提醒

`private/` 默认被 Git 忽略，但忽略规则不是隐私产品。不要保存真实姓名、联系方式、照片、证件、住址、单位或原始聊天记录；只记录完成决策所需的最小摘要。

