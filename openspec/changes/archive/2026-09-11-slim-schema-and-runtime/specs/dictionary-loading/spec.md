## Purpose

约束 Rime 词典的挂载关系、构建产物规模与词条格式合法性，确保任何词表都不会被重复挂载到多个翻译器，且非法词条不会在构建期被静默丢弃。

## ADDED Requirements

### Requirement: 单一挂载来源

每个词表 MUST 在构建图中只被一个翻译器挂载。若同一词表同时被多个 translator 引用，则其词条会重复进入候选空间，并放大索引体积。

#### Scenario: 英文词表仅由 melt_eng 挂载

- **WHEN** 检查 `extended.dict.yaml` 与 `melt_eng.dict.yaml` 的 `import_tables`
- **THEN** `en_dicts/en` 与 `en_dicts/en_ext` MUST 仅出现在 `melt_eng.dict.yaml` 中
- **AND** `extended.dict.yaml` MUST NOT 引用任何 `en_dicts/` 路径

#### Scenario: 消除重复挂载后拼音索引显著缩小

- **WHEN** 从 `extended.dict.yaml` 移除英文词表引用并重新构建
- **THEN** `build/extended.prism.bin` 相对构建前 MUST 缩小 90% 以上（实测 1,254,552 B → 21,168 B，-98.31%）
- **AND** MUST NOT 通过删除任何其他词表来达成该缩减

#### Scenario: 构建产物总量缩减

- **WHEN** 比较消除重复挂载前后的 `build/` 全部产物总和
- **THEN** 总量 MUST 缩减至少 10%（实测 17,531,184 B → 15,450,188 B，-11.9%）
- **AND** 该降幅 MUST 小于 prism 的降幅，因为英文词条在 `melt_eng` 中仍保留完整副本

#### Scenario: 英文词表构建产物不受影响

- **WHEN** 在消除重复挂载后比较 `build/melt_eng.prism.bin`、`build/melt_eng.table.bin`、`build/melt_eng.reverse.bin` 与构建前的字节大小
- **THEN** 三者 MUST 与构建前基本一致，波动小于 1%
- **AND** 若存在波动，MUST 可归因于畸形词条修正后新增的被索引词条，而非英文词表丢失

### Requirement: 词条格式合法性

词典文件中的每个词条 MUST 以制表符分隔字段，且 MUST NOT 含空字段。词条的 `word` 字段 MUST NOT 以空格代替制表符充当分隔符。

注：`word` 字段内部合法地允许空格（如 `Buenos Aires`、`iPhone 17 Pro`），此类多词词条经实测可正常编码，不属于缺陷。

#### Scenario: 构建日志无编码失败

- **WHEN** 以 `rime_deployer --build` 构建全部已启用方案
- **THEN** 构建输出 MUST NOT 出现任何 `Encode failure` 记录

#### Scenario: 修正已知畸形词条

- **WHEN** 检查以下位置
- **THEN** `en_dicts/en.dict.yaml` 中 `abalone` 词条 MUST 使用制表符分隔而非空格
- **AND** `en_dicts/en_ext.dict.yaml` 中 `Next.js` 词条 MUST 仅含一个制表符
- **AND** `en_dicts/en_ext.dict.yaml` 中 `React` 词条 MUST 仅含一个制表符

### Requirement: 既有词条可输入性保持

修正畸形词条与调整挂载关系后，修正前可正常输入的词条 MUST 保持可输入。

#### Scenario: 英文候选仍然出现

- **WHEN** 在消除重复挂载后以英文前缀触发候选
- **THEN** 英文候选 MUST 仍由 `melt_eng` 翻译器产出
- **AND** 英文候选 MUST NOT 因移除 `extended.dict.yaml` 的英文引用而完全消失

#### Scenario: 修正后的词条不再报编码失败

- **WHEN** 修正 3 条畸形词条并重新构建
- **THEN** 构建输出 MUST NOT 再出现针对 `abalone`、`Next.js`、`React` 的 `Encode failure`
- **AND** 这 3 条词条 MUST 全部具备合法格式

#### Scenario: 构建日志的编码失败全部消除

- **WHEN** 完成修正后完整构建
- **THEN** 构建输出中 `Encode failure` 出现次数 MUST 为 0
- **AND** 修正前该次数 MUST 大于 0（基线为 2 类、共 4 次）
