# 面向团队协作的 server / channel / agent 持久运行决策

## 元数据

| 字段 | 值 |
| --- | --- |
| **决策日期** | 2026-05-04 |
| **关联 spec** | `00-workspace-tenancy-foundation-plan.md`、`01-workspace-collaboration-plan.md`、`02-workspace-agent-execution-plan.md`、`03-workspace-agent-execution-hardening-plan.md`、`07-workspace-team-kanban-board-rebuild-plan.md` |

---

## 背景

Poco 当前已经完成了一轮围绕 `workspace / board / issue / preset / agent assignment` 的团队协作与执行建模。到目前为止，系统的核心优势仍然是执行层：容器沙箱、会话链路、工具调用、callback 持久化、前端执行回放。这套能力让 Poco 很适合做“围绕 task 跑 agent”的平台。

但这轮产品讨论暴露出一个新的重心变化：用户希望把团队协作本身提升为第一视角，不再只是“在 issue 上挂一个 agent”，而是更接近 `server -> channel -> task -> agent` 的协作模型。换句话说，产品主舞台不再只是 project / issue / session，而是团队频道中的消息、任务、认领、状态流转和 agent 作为队友的协作存在。

如果继续沿用上一轮“先保持 workspace 主干，再慢慢往上包一层 channel/task”的思路，确实最稳，但它默认前提是“我们已经上线，向后兼容成本高”。而当前阶段是敏捷开发、尚未上线，用户明确表达了一个新的偏好：**第一版不需要为了向后兼容增加冗余封装和保护层，可以直接朝 server / channel 语义重构。**

与此同时，另一个设计问题也被同时抬升出来：如果 agent 真正成为频道中的长期成员，它不能只是一段 prompt 配置，也不能完全依赖短期 session。它需要一套持久状态边界来保存身份记忆、工作上下文和任务进度。但这个持久边界也不能简单等价为“永远开着的容器”，否则并发、恢复和状态污染问题会很快失控。

因此，本次决策要同时回答两个问题：

1. Poco 的团队协作主线，是否直接切换到 `server / channel / task / agent`？
2. 如果 agent 需要长期存在，它的身份、记忆、持久状态、执行 runtime 应该如何切分？

## 用户叙事

下面这段用户叙事描述的是这次决策落地后的 MVP 体验，不涉及实现细节，只说明用户侧会看到什么。

**Alice 创建了一个团队 Server，准备让人和 agent 在同一个协作空间里推进开发任务。**

1. **创建协作空间**：Alice 创建一个名为 `Poco Core` 的 server。这个 server 下有 `#general`、`#backend`、`#frontend` 等频道。团队成员加入 server 后，可以根据自己所在的工作流进入不同频道讨论。

2. **在频道中创建任务**：Alice 在 `#backend` 频道中创建一个 task：“把 workspace 语义迁移到 channel 视图”。这个 task 会出现在频道聊天流里，同时也会出现在该频道的看板视图里。看板状态固定为 `todo -> in_progress -> in_review -> done`。

3. **把任务分配给 agent**：Alice 把这个 task 分配给 `@backend-specialist`。这个 agent 不是一条 preset 配置，而是一个在 server 内有身份、名字和长期状态目录的协作成员。系统为它关联一个持久 runtime，并把任务排给它。

4. **agent 在持久状态上工作**：`@backend-specialist` 在自己的持久状态目录里保存 `MEMORY.md`、关键知识、当前上下文和任务状态。它进入自己的持久化容器中工作，逐步更新这些长期状态文件，并在频道中持续同步进展。

5. **处理临时性任务**：另一位成员 Bob 想让同一个 agent 快速验证一个边缘 case，于是触发一个临时 runtime。这个临时 runtime 可以读取 `@backend-specialist` 的长期状态快照，但不能直接修改长期状态文件。它的输出必须在任务结束后由显式合并或人工确认进入长期状态。

6. **避免并发污染**：此时 Alice 又在另一个频道给 `@backend-specialist` 分配了第二个正式任务。系统不会让同一个 agent 的持久容器同时处理两个正式任务，而是把第二个任务排队，或者提示改派给其他 agent。这样可以避免多个任务同时污染同一份长期记忆和工作目录。

7. **持续协作而不是短期执行**：团队最终看到的，不再只是“某个 preset 跑过一个 session”，而是“一个长期存在的 agent 成员在多个频道中按顺序接任务、沉淀记忆、维护工作状态，并通过 task 与频道协作面持续互动”。

## 决策结论

> Poco 的团队协作主线在 MVP 阶段直接切换到 `server / channel / task / agent`。我们不为了未上线系统的向后兼容保留额外包装层，也不在 MVP 中引入 daemon / local runner。Agent 采用“身份、运行配置、持久状态、执行 runtime”四层拆分：每个 agent identity 拥有一份持久状态目录和至多一个可写的持久 runtime；临时 runtime 只能读取持久状态快照，不能直接修改长期状态文件。

---

## 决策路径

```mermaid
graph TD
    A["Poco 需要从 issue-centered execution 平台演进到 team-centered collaboration 平台"] --> B{"产品主线怎么切？"}
    B --> C["继续以 workspace / board / issue 为主线，仅在上层加少量 channel 包装"]
    B --> D["直接把 server / channel / task / agent 设为新的协作主线"]
    C -->|仍会让用户长期暴露在旧语义中，产品心智无法真正切换，且当前尚未上线不值得为兼容保留两套主线| X["不采用"]
    D -->|✅ 采纳| E["MVP 直接重构到 server / channel / task / agent"]

    E --> F{"MVP 是否同时引入 daemon / local runner？"}
    F --> G["现在就做 cloud control plane + local runner"]
    F --> H["先专注团队协作与云端挂载执行，daemon 后置"]
    G -->|会把 scope 从协作模型扩展到机器注册、token scope、runner 信任和断线恢复，MVP 范围过大| X
    H -->|✅ 采纳| I["MVP 只做 team collaboration + mounted persistent execution"]

    I --> J{"agent 的长期状态边界放在哪里？"}
    J --> K["把 preset 直接扩展为 identity + memory + runtime"]
    J --> L["把持久状态完全绑定在 persistent container 上"]
    J --> M["拆成 identity / preset / persistent state / runtime 四层"]
    K -->|对象职责膨胀，运行配置、协作身份、长期记忆和执行实例耦合过深| X
    L -->|容器变成身份边界后，调度、恢复、回收和并发污染都会变重| X
    M -->|✅ 采纳| N["四层拆分，持久目录作为长期状态边界"]

    N --> O{"同一个 agent 如何处理多个任务？"}
    O --> P["默认允许多个任务共享同一可写持久 runtime 并发执行"]
    O --> Q["每个 agent 最多一个可写 persistent runtime，其他任务排队或显式 clone"]
    P -->|同一工作目录和记忆文件会被并发写入，状态污染风险过高| X
    Q -->|✅ 采纳| R["单 agent 单可写 runtime，默认串行"]

    N --> S{"临时 runtime 如何访问长期状态？"}
    S --> T["直接挂载并允许写持久目录"]
    S --> U["只读快照 + 显式合并"]
    T -->|短任务和试探性执行会污染长期记忆，回滚和审计都困难| X
    U -->|✅ 采纳| V["temporary runtime 只读 persistent state snapshot"]
```

## 关键论点

### 为什么 MVP 可以直接重构到 server / channel / task / agent，而不是继续保留旧主线

如果系统已经上线，保持 `workspace / board / issue` 作为稳定主干、再在上面逐步叠加 `channel / task` 的语义，是更稳的工程路线。但当前用户明确说明：这是敏捷开发阶段，且系统尚未上线，不需要为了向后兼容增加冗余的封装和保护逻辑。

在这个前提下，继续保留双主线反而会带来额外负担：

- **产品心智不清晰**：用户看到的是新概念，开发者维护的却还是旧概念，容易长期两套词汇并存。
- **实现复杂度更高**：每做一个页面和接口，都要同时考虑旧入口和新入口。
- **技术债形成更快**：临时兼容层一旦进入 MVP，很容易因为“先这样用着”而长期遗留。

因此，这次不再把“兼容旧主线”当成默认目标，而是接受直接重构产品语义：`server / channel / task / agent` 成为新的协作第一视角。

### 为什么 daemon / local runner 不进入当前 MVP

Slock daemon 的核心价值是把云端协作面和本地执行面连接起来，这条路线很有吸引力，也很值得后续借鉴。但如果把它纳入本次 MVP，系统 scope 会立刻扩大到另一个层面：

- runner 机器注册与信任模型
- 本地 token scope 与吊销策略
- 本地 runtime 托管与 crash 恢复
- 多机绑定、断线重试、任务回收
- 本地目录隔离与审计

这些问题和“团队协作主线切换”不是同一层复杂度。把两者放在一个 MVP 里，会让团队同时处理产品重构、执行边界重构和部署形态重构，风险过高。

因此，本次明确把 daemon / local runner 后置。当前 MVP 只处理：

- server / channel / task / agent 的协作模型
- 基于云端挂载和持久容器的执行模型

后续如果协作面跑通，再单独评估 `poco-runner` 这条路线。

### 为什么 agent 必须拆成 identity / preset / persistent state / runtime 四层

用户现在希望 preset 不只是 prompt 模板，而是能承载 agent 的记忆、工作状态和长期行为。如果直接把所有能力塞进 preset，会导致单个对象同时承担四种职责：

- 对外可见的协作身份
- 对内可复用的运行配置
- 长期记忆和工作状态
- 当前执行实例

这种设计的问题不是“不优雅”，而是会很快带来具体工程困难：

- **身份和配置难分离**：同一个 agent 想换模型或 skill 集，是否意味着“换了一个人”？
- **长期状态难迁移**：记忆是跟身份走、跟配置走，还是跟容器走？
- **运行时约束难表达**：一个 agent 的当前容器、暂停状态、队列情况，本质上不是 preset 属性。

更稳妥的边界是：

- `AgentIdentity`：协作层身份，负责名字、头像、描述、所属 server/channel 权限。
- `RuntimePreset`：运行配置，负责 prompt、skills、MCP、模型、工具权限、容器策略。
- `PersistentState`：长期状态目录，负责 `MEMORY.md`、知识笔记、当前上下文、任务状态。
- `RuntimeContainer`：执行实例，负责承载一次持续执行。

这样，身份、配置、状态、运行实例可以各自演进，而不会在一个对象里互相绑死。

### 为什么长期状态的第一边界必须是 agent-owned persistent state，而不是 persistent container

Persistent container 对执行很重要，但它不是最好的长期状态所有者。原因在于：

- **容器是执行载体，不是知识载体**：容器更适合承载进程、依赖、临时文件和当前任务工作区。
- **容器生命周期不够稳定**：重建、迁移、回收、镜像升级都会让“把记忆绑在容器上”变得昂贵。
- **并发污染更难控制**：一旦容器既是执行实例又是长期状态边界，多个任务共享它时很容易互相覆盖状态。

因此，这次明确长期状态应首先落在 agent-owned 目录，例如：

```text
agents/<agent_id>/
  profile.json
  MEMORY.md
  notes/
    key-knowledge.md
    active-context.md
  state/
    task-state.json
    channel-state.json
  artifacts/
```

容器负责挂载和使用这份目录，而不是拥有这份目录。

### 为什么每个 agent identity 在任一时刻最多只能有一个可写的 persistent runtime

如果用户希望 agent 在多个频道中长期工作，并持续维护自己的记忆、进度和上下文，那么默认无限并行会立刻引入状态污染：

- 两个任务同时写 `MEMORY.md`
- 两个频道同时修改 `active-context`
- 同一个工作目录被并发改动
- 队列状态和当前任务状态互相覆盖

这类问题不是靠“约定大家别乱写”能解决的。产品和系统必须从一开始就明确单写者模型：

- 一个 `AgentIdentity` 在任一时刻最多一个**可写** persistent runtime
- 新任务默认进入该 agent 队列，或要求改派
- 如果未来需要并行，必须走显式 clone / worker runtime 路线，而不是共享可写状态

这个约束会让早期调度看起来更保守，但换来的回报是：长期状态可解释、可恢复、可审计。

### 为什么 temporary runtime 必须只能读取 persistent state snapshot，而不能直接写长期状态

用户已经明确希望临时性容器不能修改持久化相关文件。这个方向是对的，但仅仅写成“不能修改文件”还不够，必须进一步明确交互模型，否则实现时很容易出现“虽然逻辑上不该写，但实际上还是共享挂载了目录”的情况。

更稳的设计是：

1. temporary runtime 启动时读取 persistent state 的快照；
2. persistent state 对 temporary runtime 是只读的；
3. temporary runtime 的输出如果想进入长期状态，必须经过显式 merge / promote，或人工确认。

这样可以把短任务、验证任务和试探性修改限制在自己的边界里，避免它们自动污染长期知识和任务进度。

### 为什么看板在新主线里保留为 channel 下 task 的视图，而不是继续作为独立领域对象

当前团队已经接受一个事实：协作主线要转向频道和任务，而不是继续围绕 issue 页面组织工作。这并不意味着看板价值消失，而是它的定位发生变化。

看板的价值在于：

- 按状态查看任务堆积
- 快速拖动和推进工作流
- 在固定的四阶段中观察团队负载

这些价值完全可以保留，但它不再需要单独承担“组织上下文”的角色。新的组织上下文由 channel 提供，看板成为 channel 下 task 的一种视图即可。这与用户已经接受的 `todo -> in_progress -> in_review -> done` 模型是完全一致的。

## 约束与前提

- 这份决策以“系统尚未上线、可以接受直接语义重构”为前提。如果未来已有大量生产数据或外部 API 依赖，迁移策略需要重新评估。
- 当前 MVP 不包含 daemon / local runner、本地机器注册、runner token scope、多机调度和断线恢复。
- 当前 MVP 允许使用云端挂载和持久容器承载长期 agent runtime，但长期状态所有权仍属于 agent-owned persistent state。
- 当前 MVP 默认一个 agent identity 只处理一个 active writable runtime；并发 clone / worker 机制不在本轮范围内。
- temporary runtime 只能读取 persistent state snapshot，不直接修改长期状态文件；任何长期状态写入都必须回到 persistent runtime 或显式 merge 流程。
- `RuntimePreset` 仍然是执行配置来源，但不再承担完整 identity / memory / runtime 语义。

## 历史变更

| 日期 | 变更内容 | 原因 |
| --- | --- | --- |
| 2026-05-04 | 初次记录 | 团队协作主线从 workspace / board / issue 切换到 server / channel / task / agent，并明确 agent 持久状态与 runtime 边界 |
