# SuperWiki 项目初始化协议

本协议只负责“为项目接入知识库”的写入动作：创建 `.wiki/skills`，并接入当前运行时的项目级 skill 入口。正常已初始化项目不要在只读任务中加载此文件。

## 何时读取和执行

只有一个条件：用户**明确要求**为该项目接入或初始化 SuperWiki（例如"初始化这个项目的知识库"）。这条路径只创建目录和入口，不写项目知识，也不替代任何知识写入流程。

其他任何情况都不构成初始化理由，包括本次任务带有待落地的知识写入。缺失、冲突或无法确认入口本身从不是触发条件：只有在用户明确要求初始化的批次中，才按下方流程处理。除用户明确要求初始化的批次外，未初始化的项目（`.wiki/skills` 不存在）和只读任务都严禁创建 `.wiki/` 目录，一律不写 `.wiki/staging.md`；待办、发现和阻塞点只能在对话回复中直接说明。唯一例外就是用户明确要求初始化（`AUTHORIZATION: explicit-user-setup`）：只有这条明确请求允许创建 `.wiki/skills` 及项目入口；没有这条明确请求时，创建 `.wiki/` 目录或写 staging 一律严禁。以下情况一律不执行本协议、不运行初始化命令、不创建入口链接或 staging，即使路径缺失或入口冲突：

- 检索、解释、审查、只读分析，或任何用户未明确要求初始化的任务；
- 未初始化项目上的知识写入请求：先告知用户"该项目尚未初始化，需要显式初始化"，继续以当前代码为真相来源完成原任务，由用户决定是否初始化。需要记下的待办、发现或阻塞点直接在对话回复中说明，不要写 `.wiki/staging.md`，也不要为此创建 `.wiki/` 目录；
- 仅仅因为加载了 `superwiki` skill、或发现 `.wiki/skills` / 入口不存在；
- 任何没有在任务文本中给出合法 `AUTHORIZATION:` 的调用，包括按旧 agent 名称发起的调用。

只读任务里的正确行为：

- `.wiki/skills` 已存在、只是运行时入口未链接：直接读取 `.wiki/skills/` 下的知识；入口缺失不妨碍读取。
- `.wiki/skills` 不存在：如实报告“当前项目暂无 wiki 知识”，继续以当前代码为真相来源完成原任务。可以给出一条当前运行时的精确初始化命令供用户自行执行，但不要执行它，也不要为此启动子代理。为记录待办、发现或阻塞点而创建 `.wiki/` 目录或 `.wiki/staging.md` 同样被禁止，这些内容只在对话回复里说明。

注意区分“未接入”和“没有知识”：已通过全局 skill 加载 `superwiki`，但项目没有接入当前 agent 的项目级入口，这最多说明项目尚未接入，而不是项目没有知识。`.wiki/skills` 是 SuperWiki 的统一知识目录，不要把 `.agents/skills` 当成唯一入口。

## 授权与执行者

自举只做两件事：创建 `.wiki/skills`，并安全接入当前运行时的项目入口。执行者只能是**当前运行时自己的原生子代理**或**主 agent 自己**；本协议不安装、不注册、不修改任何命名 agent 或 agent 定义文件，也不依赖任何 agent 配置文件。初始化角色的完整行为定义在 `references/roles/initializer.md`，那是一份普通 Markdown 正文，由主 agent 在委派时逐字粘入提示词，不是运行时可发现的 agent 类型。

委派前，主 agent 必须在自包含任务文本中写明 `AUTHORIZATION:` 字段，值只能是 `explicit-user-setup`（用户明确要求接入）。缺少该字段、值不是 `explicit-user-setup`、或任务被标记为只读/检索/审查时，子代理必须返回 `no-write`，不检查路径、不 mkdir、不创建链接、不再委派。

子代理是可选的执行者，不是额外状态机：输入仍是三个可信参数（`RUNTIME`、`PROJECT_ROOT`、`INITIALIZER`）加上任务文本里的 `AUTHORIZATION` 行，输出仍是同一条状态行，不新增状态或模式。子代理只使用父任务显式给出的取值：不重新加载 `superwiki` skill，不读取角色文件或本协议路径，不再委派或派生其他 agent。

不要通过 `CODEX_HOME`、`OPENCODE_*`、`CLAUDE_*` 等环境变量猜当前运行时；这些变量可能同时存在。主 agent 应根据自己的系统身份和可用工具确定运行时，子代理只使用父任务显式给出的 `RUNTIME`：

| 当前运行时 | `RUNTIME` | 初始化参数 | 项目入口 |
|---|---|---|---|
| Codex / agent-compatible | `codex` | `--codex` | `.agents/skills` |
| OpenCode | `opencode` | `--opencode` | `.opencode/skills` |
| Claude Code | `claude` | `--claude` | `.claude/skills` |
| Cursor | `cursor` | `--cursor` | `.cursor/skills` |

## 执行流程

0. **授权判定**：按上文确认用户确实明确要求初始化。未授权时，只读和写入任务都直接报告无写入并继续原任务；子代理返回 `no-write`，不做任何检查。不要为了输出状态而启动子代理。
1. 确定当前项目根目录，并把 `SKILL.md` 所在目录解析为 SuperWiki 根目录。
2. 只检查 `<PROJECT_ROOT>/.wiki/skills` 和当前运行时映射的那一个入口，不要探测或创建其他运行时入口。两者都已正确就位时直接视为 `already-initialized`，不执行命令。
3. 如果入口已存在但不是指向 `.wiki/skills` 的符号链接，不修改任何文件，报告 `conflict`，等待用户决定。
4. 如果 `.wiki/skills` 或映射入口缺失，只执行对应的单运行时命令（`<INITIALIZER>` 为 `superwiki-init` 的绝对路径）：

   ```bash
   <INITIALIZER> --codex   <PROJECT_ROOT>
   <INITIALIZER> --opencode <PROJECT_ROOT>
   <INITIALIZER> --claude  <PROJECT_ROOT>
   <INITIALIZER> --cursor  <PROJECT_ROOT>
   ```

   按当前运行时选择其中一行，不组合参数，不追加其他运行时。
5. 验证 `.wiki/skills` 是目录，且映射入口解析到该目录。
6. 子代理执行时：回报一行状态后结束，不要继续处理用户主任务。主 agent 直接执行时：完成第 2–5 步后继续原任务，不需要输出子代理状态行。

## 委派（仅在确实需要时）

主 agent 只有在确实要发起委派时，才读取 `references/delegation.md` 和 `references/roles/initializer.md`，并按以下方式组装提示词：

1. 按 `references/delegation.md` 的完整粘入义务，把 `references/roles/initializer.md` 的完整正文原样放进提示词的角色部分。不要改写、压缩、摘要或翻译，也不要写成“按角色文件执行”。
2. 追加自包含实例，只包含本次任务的取值：

   ```text
   TASK: Initialize SuperWiki for this project only.
   AUTHORIZATION: explicit-user-setup
   RUNTIME: <codex|opencode|claude|cursor>
   PROJECT_ROOT: <absolute path>
   INITIALIZER: <absolute path>/superwiki-init
   ```

3. 子代理的授权判定、单运行时范围、命令细节和输出格式一律以粘入的角色正文为准；本协议只规定何时委派、如何投递和如何解读结果，不重复角色行为规则。任务相关路径必须是绝对路径，不得留占位、待补字段或含糊指代。
4. 子代理看到的就是提示词里的文字：不要让它自己读取角色文件或本协议，不要给它加载 `superwiki` skill，避免递归；也不要要求它继续处理用户主任务。

当前运行时没有可用的原生子代理能力时：

- 如实报告具体限制（当前运行时没有子代理能力，或该能力不可用），不要编造已委派。
- 如果本次请求明确要求必须由子代理完成，这是阻塞项：不得静默改为主线程执行，也不得改用外部 CLI 或注册自定义 agent 顶替。
- 如果请求本身不要求子代理，主 agent 可以在主线程按同一协议执行第 2–5 步；授权判定和初始化范围不因降级而改变。

## 结果处理

以下状态行是子代理或 initializer 的回报接口。主 agent 直接执行时，按相同语义处理 `conflict`、`no-write` 或 `error`，但完成安全处理后继续原任务，不因状态行而结束。

- `initialized` 或 `already-initialized`：子代理结束；主 agent 继续原任务。
- `conflict`：向用户说明冲突路径，等待决定；不要覆盖。
- `no-write`：说明未写入的原因；只读任务到此继续原任务。若属于已授权但未执行，给出当前运行时的精确单运行时命令。
- `error`：报告短错误信息；不要静默改用 `--all`，也不要猜测当前运行时。

`--all` 会同时接入多个运行时，只有用户明确要求多个工具共享同一个项目知识库时才使用；不要在自举中自行扩大范围。无法识别或映射当前运行时时返回 `error`，不要猜测，也不要默认创建全部入口。

## 边界

- 只接入项目知识库，不复制全局 `superwiki` skill 的内容进项目 wiki。
- 不安装、不注册、不修改任何 agent 定义，也不写工具、模型或全局配置。
- 不修改与本次入口无关的配置、其他工具入口或用户主任务。
- 不把临时判断写成项目知识；初始化结果只说明路径是否可用。
