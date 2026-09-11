## Why

当前配置同时存在三层浪费：五个 schema 文件重复约 560 行、英文词库被两个翻译器重复挂载导致构建产物膨胀 41%、以及文档与词条数据的静默失真。实测确认 `extended.prism.bin` 因英文词条重复挂载膨胀了 **98.31%**，而构建日志一直在报告 3 条因格式畸形而**被静默丢弃**的词条。这些问题不会报错，只会让配置越用越难维护。

## What Changes

- **消除 schema 重复**：五个 `lufs_*.schema.yaml` 中逐字相同的**七个映射型配置块**（`traditionalize`、`emoji_suggestion`、`grammar`、`punctuator`、`key_binder`、`recognizer`、`custom_phrase`）收敛到 `lufs_shared.yaml`，各方案经 `__include` 引用。各方案行数由 173/172/174/174/170 降至 164/164/166/166/162，共减少 74 行。
- **明确不收敛的内容**：实测各方案间逐字相同的剩余内容仅 33 行/方案，其余为真实差异（`speller` 码表 65 行、`translator` 参数 13 行、`schema` 声明 12 行）。模糊音注释目录经实测**并非重复**——`lufs_pinyin` 47 行、四个双拼方案各 30 行且互不相同。因此不引入生成器，避免为少量行数复现本变更试图消除的同步负担。
- **消除英文词库重复挂载**：从 `extended.dict.yaml` 移除 `en_dicts/en`、`en_dicts/en_ext`，英文统一由 `melt_eng.dict.yaml` 挂载。实测 `extended.prism.bin` 从 1,254,552 B 降至 21,168 B（**-98.31%**），`extended.reverse.bin` -79.85%，`extended.table.bin` -4.20%；构建产物合计由 17,531,184 B 降至 15,450,188 B（**-2,080,996 B，-11.9%**）。`melt_eng.*` 仅因新增 3 条被修正词条而增加 72 B，英文词表未丢失。
  说明：prism 的塌缩幅度远大于 table，原因是英文词条在 `melt_eng` 中仍有完整副本，故 table 只减少冗余部分，而 prism 中的拼音音节组合冗余被完全消除。table.bin 占构建产物约 80%，因此总体降幅为 11.9% 而非 prism 的 98%。
- ****BREAKING** 英文候选排序变化**：英文候选当前来自 `script_translator`（`initial_quality: 1.2`）与 `melt_eng`（`1.1`）两个来源；改动后仅来自 `melt_eng`（`1.1`）。英文候选仍然出现，但相对中文的排序会略微下降。此行为变化需实际使用验证后再定稿。
- **清理死负载**：删除 3 个仅在注释中被引用的 `lua/candidate_sorting/*.lua`，删除无任何引用的 `tools/patch/enable_ascii.yaml` 与其孤儿 recipe `tools/recipes/enable_ascii.recipe.yaml`。
- **修复数据完整性与文档漂移**：修正 3 条畸形词条（`en_dicts/en.dict.yaml:29` 用空格代替 Tab；`en_dicts/en_ext.dict.yaml:2449`、`:2450` 双 Tab 导致空编码字段），使构建日志不再出现 `Encode failure`；修正 `README.md` 中"默认四候选项"与 `page_size: 5` 的漂移。
- **明确不支持的方向**：`import_preset` 经实测对 `engine` / `switches` 静默失效（不报错、直接丢弃内容，37 行配置消失），因此 schema 收敛**不得**采用该机制。被注释停用的四个方案在构建期零成本，`.gram` 文件为五个方案共用，均不纳入精简。

## Capabilities

### New Capabilities

- `dictionary-loading`: 词典挂载与构建产物的行为契约——任何词表在构建图中 MUST 只被挂载一次；词条格式 MUST 合法，非法条目 MUST NOT 被静默丢弃；已有词条的可输入性 MUST 保持不变。
- `schema-consolidation`: 多方案 schema 配置的收敛契约——重复配置 MUST 有唯一事实来源；收敛后各方案解析出的有效配置 MUST 与收敛前等价；对 `import_preset` 等静默失效机制 MUST 有回归防护。

### Modified Capabilities

无。本仓库此前无 `openspec/specs/` 既有能力，本次为首次建立。

## Impact

**受影响配置与数据文件**

- `lufs_pinyin.schema.yaml`、`lufs_dpy.schema.yaml`、`lufs_mspy.schema.yaml`、`lufs_flypy.schema.yaml`、`lufs_pyjj.schema.yaml`：去重与收敛
- `extended.dict.yaml`：移除英文重复挂载
- `en_dicts/en.dict.yaml`、`en_dicts/en_ext.dict.yaml`：修正 3 条畸形词条
- `README.md`：修正候选项数量描述

**删除**

- `lua/candidate_sorting/long_phrase_first.lua`、`single_char_first.lua`、`single_char_only.lua`
- `tools/patch/enable_ascii.yaml`、`tools/recipes/enable_ascii.recipe.yaml`

**构建产物（可测量）**

- `build/extended.prism.bin`、`build/extended.table.bin`、`build/extended.reverse.bin` 体积下降；`build/melt_eng.*` 不变

**行为影响**

- 英文候选相对中文的排序下降（见 What Changes 中的 BREAKING 项）

**不受影响**

- 已启用的方案集合（`default.yaml` 中仅 `lufs_pinyin` 启用）不变
- `zh-hans-t-essay-bgw.gram`：五个方案共用，保留
- `rime.lua`：Rime 自动加载 `lua/*.lua`，缺失无害，不作为问题处理
