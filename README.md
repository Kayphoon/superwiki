# SuperWiki

## 安装

本仓库就是这个 skill 本身：根目录的 `SKILL.md` 即入口，`references/`、`superwiki-init`、`skills.sh` 一起构成完整分发单元。

```bash
# 走公开的 skills 协议
npx skills add Kayphoon/superwiki

# 或走本仓库自带的安装器（零依赖，默认装到 ~/.agents/skills）
npx github:Kayphoon/superwiki
npx github:Kayphoon/superwiki --target codex
npx github:Kayphoon/superwiki --project ./my-project
```

装好后新开一次会话让运行时重新发现 skill；项目侧的知识库入口用 `superwiki-init` 建立。

项目知识库管理器，以原生 skill 形式保存在项目的 `.wiki/skills/` 目录。每个知识模块是一个 `wiki-*/SKILL.md`：frontmatter 的 `name` + `description` 是发现索引，agent 按任务语义选中后读取完整源文件，并始终以当前代码为真相来源。

SuperWiki 不包含后台注入、常驻任务或独立检索服务。它是否进入当前任务，取决于运行时的原生 skill 路由，或由用户、主 agent 显式加载。

外部资料研究、本地代码库探索等其他通用 skill 不由本仓库提供：它们独立安装、独立管理，由宿主自己的原生 skill 发现选择，没有固定路径，也不是 SuperWiki 的默认依赖。

## 安装与接入

把本仓库放到运行时可发现的 skill 目录，或在项目中建立指向知识库的入口链接：

| 运行时 | 项目入口 |
|---|---|
| Codex / agent-compatible | `.agents/skills -> ../.wiki/skills` |
| OpenCode | `.opencode/skills -> ../.wiki/skills` |
| Claude Code | `.claude/skills -> ../.wiki/skills` |
| Cursor | `.cursor/skills -> ../.wiki/skills` |

也可以手动创建：

```bash
mkdir -p .wiki/skills
mkdir -p .agents
ln -s ../.wiki/skills .agents/skills
```

只接入当前运行时对应的入口。`superwiki-init` 是可选初始化工具，显式传入单个运行时：

```bash
superwiki-init --codex /path/to/project
# 或 --opencode / --claude / --cursor
```

已有同名路径时不要覆盖，先确认冲突。只有用户明确要求多个工具共享同一个项目知识库时才使用 `--all`。

`skills.sh` 是**全局 skill 链接**安装器，只把 `superwiki` 这一个 skill 链接到全局 agent 兼容 skill 目录 `~/.agents/skills`，指向本仓库根目录：

| 目标目录 | 链接 |
|---|---|
| `~/.agents/skills`（agent-compatible） | `superwiki -> 本仓库根目录` |

安装器不再写入 OpenCode、Claude Code、Codex、Cursor 各自的全局 skill 目录（`~/.config/opencode/skills`、`~/.claude/skills`、`${CODEX_HOME:-~/.codex}/skills`、`~/.cursor/skills`），这些目录下的旧链接属于旧安装残留，按需手动处理。

安装器不安装、不链接、也不改写任何其他 skill（外部资料研究、本地代码库探索之类的通用 skill 由各自仓库独立安装），不安装 helper agent，也不写入 agent 定义、模型或权限配置。目标位置已有任何同名条目（文件、目录或符号链接，包括指向别处的链接和悬空链接）时，安装器保留原样并报告跳过，不会覆盖、改指向或自动清理；`superwiki` 自身沿用原有链接更新行为。传入项目路径时仍保留原有的项目初始化入口，但它不显式选择运行时，未选择时沿用 `superwiki-init` 的脚本默认行为（接入全部运行时入口）。需要只接入单个运行时，请直接调用 `superwiki-init --codex|--opencode|--claude|--cursor <project>`。接入后新开会话，让运行时重新发现 skill。

## 使用

由当前运行时的原生 skill 发现按 `name` + `description` 路由，或由用户、主 agent 显式加载。加载语法取决于运行时本身，本仓库不绑定任何特定工具的调用 API。

只读检索（默认）：

1. 直接读 `.wiki/skills`；即使运行时入口尚未建立也照读，不初始化、不创建链接或 staging。
2. 按语义比较各 `wiki-*` 的 `name` + `description` 选出相关条目，读取完整 `SKILL.md` 及支持文件，不加载无关模块。
3. 用当前代码核对知识，不一致时以代码为准并说明差异。只有本次任务本身包含知识写入时才修改。

知识模块写入（新建、正文编辑含只改正文、改名、合并）：先判断本次确实属于待写入知识，然后读 `references/writing.md`。仅建目录或入口链接、不写知识模块的初始化不属于知识模块写入，只需在用户明确要求初始化时按 `references/initialization.md` 执行；写入请求本身不会自动初始化未接入的项目，遇到未初始化项目先告知用户需要显式初始化。

| 文件 | 何时读 |
|---|---|
| [`references/writing.md`](references/writing.md) | 任何知识模块写入前必读（仅建目录/入口的初始化不算）：写作范围、查重、条件化索引核对、合并、全量元数据校验、引用后删除、命名与模板 |
| [`references/initialization.md`](references/initialization.md) | 仅当用户明确要求初始化项目知识库、且 `.wiki/skills` 或运行时入口缺失/冲突时（写入请求本身不触发初始化） |
| [`references/delegation.md`](references/delegation.md) | 仅在实际发起委派时：逐字嵌入角色正文、拼装自包含提示词、选择当前运行时的子代理类型、运行时不支持时如何报告 |
| [`references/roles/wiki-auditor.md`](references/roles/wiki-auditor.md) | 委派 wiki 写入审计时，作为提示词正文逐字使用（只审计、不检索、不写入） |
| [`references/roles/initializer.md`](references/roles/initializer.md) | 委派已授权初始化时，作为提示词正文逐字使用 |

已初始化的项目由主线程直接检索时，不需要任何参考文件；加载本 skill 本身、路径缺失、写入请求或检索未命中都不触发初始化。项目 wiki 的检索和条目选择不委派；只有写入审计或用户明确要求初始化时才可能使用上面的入口。

### 委派（可选）

项目 wiki 的检索、条目选择和写入都由主 agent 在主线程完成；只有 wiki 写入审计和用户明确要求初始化（`explicit-user-setup`）时才可能委派，且都不是必需的。缺少委派能力不影响 SuperWiki 的核心工作。

| 委派任务 | 入口 |
|---|---|
| wiki 写入审计 | `references/roles/wiki-auditor.md` |
| 用户明确要求初始化（`explicit-user-setup`） | `references/roles/initializer.md` |

确实要委派时，读 `references/delegation.md` 和恰好一个入口，并把角色文件的**完整正文连同结尾约束逐字粘入**当前运行时的原生子代理提示词，再补项目根目录、任务目标、绝对路径输入、约束和返回格式；不要留占位、不要复制整段用户对话。不要让子代理去读角色文件路径，也不要依赖 skill 继承或"上面已经说过的行为"。

角色文件是普通 Markdown 行为正文（无 frontmatter、模型、昵称或服务档位），不是 agent 定义、agent 类型或配置项。具体子代理类型由当前运行时自己的子代理能力决定：只读审计优先只读类型，初始化只在任务文本带有 `AUTHORIZATION: explicit-user-setup` 时使用可写类型。外部资料研究、本地代码库探索等通用 skill 若已由宿主原生发现提供，属于独立能力，不在本仓库的委派入口内，也没有固定路径。

## 兼容性与知识结构

原生 skill 发现依赖有效的 frontmatter：`name` 与 `description` 必须存在且可解析。实际写入时按 `references/writing.md` 用真实 YAML 解析器校验，缺失或过宽的描述按正文和当前代码重写，不要用正文搜索或关键词堆砌兜底。本仓库只对链接与脚本行为做隔离验证，未对所有运行时的原生路由做端到端测试。

```text
.wiki/skills/
├── wiki-domain-status/SKILL.md
├── wiki-csv-encoding/SKILL.md
└── wiki-fix-xxx-20260611/SKILL.md
```

新建模块统一使用 `wiki-<topic>`，名字与目录名一致；历史遗留的 `wiki_<topic>` 可以继续读取，被写入时必须符合当前格式，但不要顺手批量迁移无关条目。

## 从旧版安装迁移

旧版本可能注册过 SuperWiki 的 memory command，或安装过 `memory-librarian` / `superwiki-initializer` 之类的 helper agent。当前版本只提供 skill、参考文件、`superwiki-init` 与 `superwiki` 全局 skill 链接；不再有 helper 安装步骤，也不需要 agent 注册。

- `librarian` 与 `explorer` 现在是**独立的同级 skill**，单独管理、单独安装，不再随本仓库分发。若旧版本曾通过本仓库的全局安装器建立过它们的链接，这些条目属于旧安装残留：由外部安装流程按需自行维护或移除，升级既不创建也不会改写它们。
- 升级**不会**自动删除已有的 helper 配置、全局链接或 agent 定义；本仓库不提供批量清理脚本，请勿自行广泛删除。
- 只手动移除**能够确认属于 SuperWiki 旧安装**的残留：指向本仓库旧脚本或旧 skill 路径的符号链接，以及旧安装写入的同名 agent 定义或配置条目。
- 归属无法确认的定义、第三方 hook 与其他工具配置一律保留；不确定时先询问用户，不要覆盖、猜测或"顺手清理"。
- 本仓库不再提供 hook、环境变量、自动注入或 agent 安装；迁移完成后不需要保留旧安装，也不需要新增任何 agent 注册。
