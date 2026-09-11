## Context

本仓库是 Rime 输入法的用户目录（macOS Squirrel，librime 1.16.0），通过 `rime_deployer --build` 部署。构建入口为 `/Library/Input Methods/Squirrel.app/Contents/MacOS/rime_deployer`，运行时间约 1.07s，产物字节级可复现。

动机见 `proposal.md`。以下是决定实现方式的关键约束，均在本次探索中实测确认：

**librime 提供的四种复用机制，三种不可用：**

| 机制 | 适用 | 实测结论 |
|---|---|---|
| `import_preset` | `punctuator` / `key_binder` / `recognizer` | 仅这三段可用 |
| `import_preset` | `engine` / `switches` | **静默失效**：保留字面值不展开，37 行配置消失，构建仍成功退出 0 |
| YAML 锚点 | 跨文件引用 | **不可用**：`the referenced anchor is not defined` |
| 合并键 `<<:` | 任意 | **不可用**：yaml-cpp 不支持 |
| `__include: 文件:/路径` | 映射型配置块 | **可用**：编译产物中正确展开 |

**配置块按值类型分为两类**，这决定了收敛方式：

- **映射型**（`traditionalize`、`emoji_suggestion`、`grammar`、`custom_phrase`、`translator`、`punctuator`、`key_binder`、`recognizer`）→ 可用 `__include` 收敛
- **列表型**（`switches`、`engine`、`speller/algebra`）→ librime 无原生机制可复用列表，`__include` 只能整体替换而无法扩展

**验证手段已确立**：`build/<schema_id>.schema.yaml` 是 librime 解析后的完整有效配置，除 `__build_info.timestamps` 段外完全确定。排除该段后，收敛前后可做逐字节等价断言。

**环境约束**：`pypinyin` 与 `requests` 未安装，`tools/` 下的词典更新脚本在本机不可运行；`pyyaml` 亦不可用。因此收敛工具 MUST 仅依赖标准库。

## Goals / Non-Goals

**Goals:**

- 构建产物显著缩小，且缩减可归因于英文重复挂载的消除（需要证据，非断言）
- schema 共享配置具备单一事实来源，消除"改一处忘四处"的编辑负担
- 建立自动等价性校验，使 `import_preset` 式的静默失效在日后无法复发
- 修正数据缺陷，使构建日志无 `Encode failure`

**Non-Goals:**

- 不追求消除全部重复行。列表型配置块在所选方案下仍保留部分重复（见决策 4），这是有意识的取舍
- 不改动 `zh-hans-t-essay-bgw.gram`（10 MB，五个方案真实共用）
- 不为被停用的四个方案优化构建成本（实测为零成本）
- 不修复 `tools/` 脚本对 `pypinyin`/`requests` 的依赖缺失；那是独立问题
- 不引入新的运行时依赖或部署步骤

## Decisions

### 决策 1：仅收敛映射型配置块，不引入生成器

映射型配置块用 `__include` 收敛；列表型配置块保持就地物化，不生成。

**为什么**：`__include` 是 librime 原生机制，零新增工具、零漂移风险。实测七个映射型块（`traditionalize`、`emoji_suggestion`、`grammar`、`punctuator`、`key_binder`、`recognizer`、`custom_phrase`）在五个方案间逐字相同，收敛后各方案行数由 173/172/174/174/170 降至 164/164/166/166/162，共减少 74 行。

**为什么不为列表型块引入生成器（相对初版设计的修订）**：初版设计依据"约 560 行重复"的估算，主张用生成器处理列表型块。实测该估算有误，收敛后各方案间**逐字相同的剩余内容仅 33 行/方案**，其中：

- `switches` 12 行——确为完全一致
- `engine` 30 行——仅 2 个变体，差异为单行 `table_translator@melt_eng`，且 4 个方案已共有同一版本
- 其余为各方案固有内容（`speller` 65 行、`translator` 13 行、`schema` 12 行），**本就不同，不应抽象**

为约 33 行/方案（且其中 4 个方案处于停用状态）引入一个会覆盖手工编辑的生成器，会复现本变更试图消除的"同步负担"，代价高于收益。因此不引入生成器。

**替代方案**：① 全量生成器——放弃，见上。② 用 `import_preset` 硬凑——放弃，它会静默丢弃 `engine`/`switches`（决策 2）。③ 将各方案固有内容也抽象到共享文件——放弃，会牺牲方案文件的自解释性，且这些内容本就是真实差异。

### 决策 2：禁止对 `engine`/`switches` 使用 `import_preset`

`import_preset` 对这两段不报错、不展开，直接保留字面值。实测将 `engine` 与 `switches` 改写为 `import_preset` 后，编译产物中这两段各剩一行 `import_preset: lufs_shared`，实际配置全部丢失，而构建退出码为 0。

**为什么**：这是本次探索发现的最危险的陷阱——一个看起来正确、构建通过、但输入法完全损坏的重构。必须在设计层面明令禁止，并由等价性校验兜底。

### 决策 3：英文词表仅由 `melt_eng` 挂载

从 `extended.dict.yaml` 移除 `en_dicts/en` 与 `en_dicts/en_ext`，英文统一经 `melt_eng.dict.yaml` 挂载。

**为什么**：实测 `extended.prism.bin` 从 1,254,552 B 降至 21,168 B（-98.31%），`extended.reverse.bin` -79.85%，`extended.table.bin` -4.20%；构建产物合计 17,531,184 B → 15,450,188 B（-2,080,996 B，-11.9%）。`melt_eng.*` 合计仅 +72 B（源于新增 3 条被修正词条），英文候选源完整保留。根因是英文词条进入 `script_translator` 后，为拼音索引制造了数万条无意义音节组合。

**为什么总体降幅只有 11.9% 而非 prism 的 98%**：英文词条在 `melt_eng` 中仍有完整副本，其 `table.bin` 未被删除，故 table 仅减少冗余部分。`extended.table.bin` 占构建产物约 80%，主导了总量。精确表述应为"prism 缩减 98%、总量缩减 11.9%"，不可混用。

**代价**：英文候选来源从两处（`script_translator` 1.2 + `melt_eng` 1.1）变为一处（`melt_eng` 1.1），相对中文的排序会略微下降。这是**有意的行为变化**，已在 proposal 标记为 BREAKING。

**替代方案**：① 提高 `melt_eng` 的 `initial_quality` 补偿排序——放弃，缺乏候选集基线时属于盲目调参，可能引入新的排序问题。② 保持双挂载——放弃，代价是 7.2 MB 构建产物。排序影响留待实际使用评估，属于可后调的参数。

### 决策 4：schema 收敛采用"共享块 + 各方案差异块"

共享配置置于 `lufs_shared.yaml`；列表型块的共享内容由生成器合成进各 `lufs_*.schema.yaml`。

**为什么**：需同时满足两个约束——各方案文件 MUST 能独立构建（用户可能只复制部分文件到自己的 Rime 目录），且 MUST NOT 依赖部署时中间产物的存在。因此收敛结果 MUST 是完全物化的 schema 文件，而非运行期拼接。

**取舍**：列表型块（约 46 行）在生成后仍以文本形式重复存在于各方案文件中。本设计接受这一残留，换取"方案文件自包含"这一更强的可用性保证。等价性校验保证生成结果正确。

### 决策 5：以编译产物做等价性校验，排除 `__build_info.timestamps`

校验方式是构建前后对比 `build/<schema_id>.schema.yaml`，排除 `__build_info.timestamps` 段后要求逐字节相同。

**为什么**：`timestamps` 取自源文件 mtime，任何编辑都会改变它，纳入比较将产生必然的假阳性。排除后剩余内容完全确定，实测仅时间戳不同、其余逐字节一致。这比"人工检查 YAML 看起来对"强得多，且能捕获决策 2 描述的静默失效。

### 决策 6：模糊音注释目录保持就地（相对初版设计的修订）

各方案 `speller/algebra` 中的注释目录**保持在各方案文件内**，不外移到共享文件。

**为什么**：初版设计假设这 167 行注释是"重复五份的同一份目录"。实测证伪——`lufs_pinyin` 含 47 行注释（拼音模糊音选项），四个双拼方案各含 30 行且**互不相同**（各双拼码表的差异说明）。这是各方案的真实差异。又因 librime 无跨文件注释机制，外移会使方案文件失去就地可读性，属于为指标而牺牲可维护性。

## Risks / Trade-offs

**[共享文件成为新的单点故障]** → `lufs_shared.yaml` 一旦损坏会影响全部五个方案。缓解：等价性校验覆盖五个方案，任一方案解析异常都会在构建或校验阶段暴露；且 `__include` 路径错误会导致构建报错而非静默通过（与 `import_preset` 不同）。

**[英文候选排序下降影响日常输入]** → 已标记为 BREAKING；实测候选来源仍在。若体验不可接受，回滚仅需恢复 `extended.dict.yaml` 中的两行，或调整 `melt_eng/initial_quality`。

**[等价性校验对无关改动产生假阳性]** → 通过排除 `__build_info.timestamps` 解决，该段是唯一的非确定性来源。

**[收敛过程中误用 `import_preset` 导致静默损坏]** → 校验脚本 MUST 断言编译产物中不存在 `import_preset` 字面值（`punctuator`/`key_binder`/`recognizer` 三段除外，它们在产物中保留该键属正常）。

**[本机缺少 `pypinyin`/`requests`，词典更新脚本无法验证]** → 本次改动不触及这些脚本；词典数据修正为纯文本编辑，不依赖 Python 依赖。

## Migration Plan

顺序遵循"先建立验证能力，再从低风险到高风险"：

1. **建立基线**：构建当前配置，留存产物副本，记录 `extended.*` 与 `melt_eng.*` 字节大小
2. **数据修正（C）**：修正 3 条畸形词条，构建确认 `Encode failure` 消失
3. **运行时精简（B）**：移除英文重复挂载、删除死 lua 与孤儿 patch/recipe，构建并记录产物缩减
4. **schema 收敛（A）**：引入 `lufs_shared.yaml`，把七个逐字相同的映射型块改写为 `__include` 引用，逐方案做等价性校验
5. **文档同步**：修正 `README.md` 候选项数量描述

**回滚策略**：全部改动均在 git 跟踪范围内。回滚为 `git restore` 对应文件；无数据库迁移、无外部状态、无不可逆操作。

**部署影响**：改动后需重新部署（Squirrel 重新部署或 `rime_deployer --build`）。无停机要求。

## Open Questions

- 英文候选排序的下降幅度是否影响日常输入体验，需实际使用一段时间后评估。该问题不影响实现路径与任务分解：排序由 `initial_quality` 参数控制，可在不改动本次任何结构的情况下单独回调。
