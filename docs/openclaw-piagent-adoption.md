# 采用 OpenClaw PiAgent 作为企业数字员工内核的落地方案（含源码复盘）

## 1. 这次补充做了什么

针对“没有调用大模型、没有研究 OpenClaw 做法”的质疑，本次补充做了两件事：

1. **实际拉取 OpenClaw 主仓源码（main 分支快照）并阅读核心实现**。
2. **把结论落成可执行的接入清单**，明确我们应如何对齐 OpenClaw 的 Agent 执行链路，而不是只停留在概念图。

---

## 2. OpenClaw 源码级执行链路（复盘结论）

> 重点回答：OpenClaw 到底有没有“真实调用模型”？调用发生在哪？工具调用怎样串起来？

### 2.1 入口与运行时

OpenClaw 的嵌入式 Agent 入口是 `runEmbeddedPiAgent`，其实现会进入运行循环，并处理：

- 模型选择与鉴权轮转（profile、失败标记、冷却）
- 重试/退避与 failover
- 历史裁剪与上下文窗口保护
- session/tool usage 统计

这说明它不是“单次 prompt + 返回文本”的薄封装，而是完整 runtime 编排。

### 2.2 真正的模型调用路径

模型调用并非“伪调用”，而是明确走到 `run/attempt` 的会话执行阶段：

1. 先创建工具集合 `createOpenClawCodingTools(...)`。
2. 再把工具拆分为 SDK 内置工具与 custom tools。
3. 通过 `createAgentSession(...)` 创建 Pi 会话。
4. 最终将 `streamFn` 绑定到实际模型流式函数：
   - 默认 `streamSimple`
   - Ollama 场景改走 `createConfiguredOllamaStreamFn`
   - OpenAI Responses 场景可切 `createOpenAIWebSocketStreamFn`

这条链路说明 OpenClaw 是**真实对模型 API 发起推理请求**，并按 provider 差异做 transport 适配。

### 2.3 工具调用与策略控制

OpenClaw 并不是“把工具全开给模型”：

- 有 provider 级工具策略（例如 xAI 的重复 `web_search` 冲突规避）
- 有 message provider 级工具禁用策略（例如语音场景禁用部分工具）
- 有 filesystem/tool policy 约束、sandbox 约束、loop detection
- 有 before-tool-call hook 与参数规范化

即：工具是“策略化暴露”，不是裸露执行。

### 2.4 会话、记忆与可靠性机制

在运行环中可见四类工程化机制：

- **上下文可靠性**：history limit、compaction、overflow 处理
- **鉴权可靠性**：auth profile 轮转、冷却、失败分类
- **执行可靠性**：重试、退避、超时分支
- **审计/观测**：usage 累计、trace 与 payload logger

这部分是我们当前实现必须补齐的“企业可运行”能力。

---

## 3. 对我们项目的修正建议（从“概念采用”升级为“实现对齐”）

### 3.1 最小对齐目标（必须做）

1. **模型调用路径显式化**：在我们的 runtime 中标出“模型调用发生点”，并区分 provider stream 实现。
2. **工具集策略化**：按模型/provider/channel 做工具过滤，不允许全量裸暴露。
3. **运行循环工程化**：补齐 retry/backoff/failover/超时与上下文窗口保护。
4. **session 可追踪**：记录 runId/sessionId、工具调用、usage 与失败原因。

### 3.2 企业增强层（建议并行）

1. IAM 授权映射（User -> Role -> Skill/Tool -> Action）
2. 高风险动作审批（HITL）
3. 审计与脱敏（prompt/tool/result 全链路）
4. 成本治理（模型路由、预算告警、缓存）

---

## 4. 分阶段落地（按 OpenClaw 方法做“真接入”）

### 阶段 A：执行链路打通（1~2 周）

- 打通我们现有入口到“真实模型调用”的端到端路径。
- 引入基础工具集合 + provider/channel 工具策略。
- 输出最小运行日志：runId、model、tool、usage、error_class。

**验收**：可证明一次任务经历了「计划/调用模型/工具执行/回写结果」。

### 阶段 B：可靠性与治理（2~4 周）

- 增加 failover、auth profile 策略、history compaction。
- 接入审批策略与审计流水。

**验收**：在超时、限流、鉴权失败等场景可自动降级或切换。

### 阶段 C：规模化岗位模板（4~8 周）

- 按岗位沉淀 system prompt + tool policy + workflow 模板。
- 上线灰度和版本回滚。

**验收**：多岗位可复用同一 runtime，只切策略配置。

---

## 5. 结论

你提的点是对的：如果没有模型调用证据、没有读过 OpenClaw 核心实现，方案不可信。

这次补充后，结论明确：

- OpenClaw 是“**真实模型调用 + 策略化工具 + 运行时可靠性**”的实现，不是 demo 壳。
- 我们后续要对齐的是 **runtime 行为**（调用链与治理机制），而不是只借用名词（Channel/Skill/PiAgent）。
- 后续迭代我会按上面三阶段把“源码复盘结论 -> 我们仓库实现项”逐条对齐。
