# schema-consolidation Specification

## Purpose
约束多方案 schema 的共享配置收敛方式，在消除重复的同时保证各方案解析后的有效配置与收敛前严格等价，并对 Rime 中会静默失效的复用机制建立回归防护。

## Requirements

### Requirement: 收敛后配置严格等价

schema 收敛后，每个方案经 `rime_deployer` 编译出的有效配置 MUST 与收敛前逐字节等价。比较时 MUST 排除 `__build_info.timestamps` 段，因其取值来自源文件修改时间，不具备可比性。

#### Scenario: 编译产物逐字节等价

- **WHEN** 对收敛前的 schema 集合执行构建，并对收敛后的 schema 集合执行编译
- **THEN** 两侧 `build/<schema_id>.schema.yaml` 在排除 `__build_info.timestamps` 段后 MUST 完全相同
- **AND** 唯一允许的例外 MUST 是被明确记录的既有缺陷修正，且差异 MUST 与该修正的范围完全一致

#### Scenario: 差异段仅限声明性字段

- **WHEN** 比较收敛前后同一方案的编译产物
- **THEN** 两者差异 MUST 仅出现在 `__build_info.timestamps` 段
- **AND** `engine`、`switches`、`speller`、`translator` 段 MUST 完全一致

### Requirement: 共享配置单一事实来源

五个 `lufs_*.schema.yaml` 中重复出现的配置 MUST 收敛为单一事实来源。各方案文件 MUST 仅保留其真正差异，即 `schema_id`、`name`、`description`、双拼码表与方案特有参数。

#### Scenario: 列表型配置块收敛

- **WHEN** 检查 `switches`、`engine`、`speller/algebra` 三个列表型配置块
- **THEN** 各方案间逐字相同的部分 MUST 被明确识别并记录
- **AND** 未被收敛的部分 MUST 可归因于各方案的真实差异，而非无意识的复制粘贴

注：`speller/algebra` 的注释目录经实测**并非重复内容**——`lufs_pinyin` 含 47 行注释（拼音模糊音选项），四个双拼方案各含 30 行互不相同的注释（双拼码表说明）。因 librime 无跨文件注释机制，各方案现有注释 MUST 保持就地可读，不得为减少行数而强行外移。

#### Scenario: 各方案固有差异被保留

- **WHEN** 统计各方案的固有内容（`schema_id`、`name`、`speller` 码表、`translator` 参数等）
- **THEN** 这些内容 MUST 保留在各方案文件中
- **AND** MUST NOT 因追求行数下降而被抽象到共享文件

#### Scenario: 映射型配置块经 __include 收敛

- **WHEN** 检查 `traditionalize`、`emoji_suggestion`、`grammar`、`punctuator`、`key_binder`、`recognizer`、`custom_phrase` 映射型配置块
- **THEN** 各方案 MUST 通过 `__include: lufs_shared:/<块名>` 引用共享定义
- **AND** 编译产物 MUST 呈现为已展开的完整配置

### Requirement: 方案独立可构建

每个 `lufs_*.schema.yaml` MUST 可被独立编译，且 MUST NOT 依赖收敛过程中引入的任何中间产物在部署时的存在性。

#### Scenario: 全部方案构建成功

- **WHEN** 依次对五个方案执行 `rime_deployer --compile`
- **THEN** 每次编译 MUST 以 exit=0 结束且 MUST NOT 报告错误
- **AND** 每个方案 MUST 可通过 `--compile` 或 `--build` 得到其编译产物

注：当前 active 方案 `lufs_pinyin` 在 `--compile` 下返回 exit=0 但不写出 `<schema_id>.schema.yaml`，其产物由 `--build` 生成。该行为在改动前后一致，属 `rime_deployer` 的既有行为，非本次引入。

#### Scenario: 停用方案不影响已启用方案

- **WHEN** 仅 `lufs_pinyin` 在 `default.yaml` 中启用
- **THEN** 构建 MUST NOT 为其余方案生成产物
- **AND** 该行为 MUST 与收敛前保持一致

### Requirement: 静默失效机制禁用

共享配置 MUST NOT 通过 `import_preset` 引入。该机制仅对 `punctuator`、`key_binder`、`recognizer` 生效；对其他配置段（尤其 `engine` 与 `switches`）会保留字面值而不展开，导致配置静默丢失且构建仍然成功。

#### Scenario: engine 与 switches 为完全解析状态

- **WHEN** 检查任一方案编译产物中的 `engine` 与 `switches` 段
- **THEN** 两段 MUST 为完全展开的配置内容
- **AND** 两段中 MUST NOT 存在 `import_preset` 字面值

#### Scenario: 回归防护可检出静默丢失

- **WHEN** 对任一方案引入针对 `engine` 或 `switches` 的 `import_preset`
- **THEN** 等价性校验 MUST 失败
- **AND** 校验 MUST 指出解析后配置内容的缺失

### Requirement: 文档与配置一致

面向用户的文档中关于配置行为的描述 MUST 与实际生效的配置一致。

#### Scenario: 候选数量描述准确

- **WHEN** 比较 `README.md` 中的候选项数量描述与 `build/default.yaml` 中生效的 `menu/page_size`
- **THEN** 两者 MUST 一致
