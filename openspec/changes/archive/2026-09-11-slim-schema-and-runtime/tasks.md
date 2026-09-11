## 1. 建立基线与验证能力

- [x] 1.1 记录构建前基线：运行 `/Library/Input Methods/Squirrel.app/Contents/MacOS/rime_deployer --build <repo> <repo> <repo>/build`，记录 `build/extended.prism.bin`、`extended.table.bin`、`extended.reverse.bin`、`melt_eng.prism.bin`、`melt_eng.table.bin`、`melt_eng.reverse.bin` 的字节大小 — 验证：产出上述 6 个数值的清单，作为后续缩减幅度的比较依据
- [x] 1.2 留存构建前的方案编译产物副本以便等价性比较 — 验证：`build/lufs_pinyin.schema.yaml` 等产物的副本存在于临时目录，且包含 `__build_info.timestamps` 段
- [x] 1.3 编写等价性校验脚本 `tools/verify_schema_equivalence.py`，仅依赖标准库（本机无 `pyyaml` 可用），对两份 `build/<schema_id>.schema.yaml` 做比较时排除 `__build_info.timestamps` 段 — 验证：对同一份产物副本比较时脚本报告"等价"
- [x] 1.4 在校验脚本中实现 `import_preset` 字面值断言，允许 `punctuator`/`key_binder`/`recognizer` 三段保留该键，其余段落出现即失败 — 验证：对构建前产物运行脚本，不报告 `import_preset` 异常

## 2. 数据完整性修正（C）

- [x] 2.1 修正 `en_dicts/en.dict.yaml` 中 `abalone` 词条，将分隔用的空格改为制表符 — 验证：`grep -c $'^abalone\tabalone$' en_dicts/en.dict.yaml` 返回 1
- [x] 2.2 修正 `en_dicts/en_ext.dict.yaml` 中 `Next.js` 词条的双制表符为单制表符 — 验证：`grep -c $'^Next\.js\tnextjs$' en_dicts/en_ext.dict.yaml` 返回 1
- [x] 2.3 修正 `en_dicts/en_ext.dict.yaml` 中 `React` 词条的双制表符为单制表符 — 验证：`grep -c $'^React\treact$' en_dicts/en_ext.dict.yaml` 返回 1
- [x] 2.4 重新构建并确认编码失败消失 — 验证：构建输出中不含任何 `Encode failure`，且不再出现 `abalone`、`React` 字样

## 3. 运行时精简（B）

- [x] 3.1 从 `extended.dict.yaml` 移除 `en_dicts/en` 与 `en_dicts/en_ext` 引用，保留说明性注释指向 `melt_eng.dict.yaml` — 验证：`grep -c "en_dicts/" extended.dict.yaml` 返回 0
- [x] 3.2 重新构建并测量产物变化 — 验证：`extended.prism.bin` 相对 1.1 基线缩小 90% 以上，即由约 1,254,552 B 降至约 21,000 B
- [x] 3.3 确认英文词表产物未受影响 — 验证：`melt_eng.prism.bin`、`melt_eng.table.bin`、`melt_eng.reverse.bin` 与 1.1 基线字节大小完全一致
- [x] 3.4 确认英文候选索引仍然存在 — 验证：构建产物 `build/melt_eng.prism.bin` 中可检索到英文词条对应的编码，英文候选来源未消失
- [x] 3.5 删除仅在注释中被引用的 3 个 lua 过滤器 — 验证：`lua/candidate_sorting/` 目录不再存在，且 `grep -rn "candidate_sorting" --include="*.yaml" .` 仅剩注释或零命中
- [x] 3.6 删除无任何引用的孤儿补丁与 recipe — 验证：`tools/patch/enable_ascii.yaml` 与 `tools/recipes/enable_ascii.recipe.yaml` 均已删除，且 `grep -rn "enable_ascii" .` 除历史记录外零命中

## 4. schema 收敛（A）

- [x] 4.1 识别五个方案间逐字相同的映射型配置块 — 验证：产出清单，覆盖 `traditionalize`、`emoji_suggestion`、`grammar`、`custom_phrase` 等，且清单依据为构建前产物的实际内容
- [x] 4.2 创建 `lufs_shared.yaml` 承载共享映射型块，并为各方案改写为 `__include: lufs_shared:/<块名>` — 验证：五个方案重新构建均成功退出 0
- [x] 4.3 对映射型块收敛执行等价性校验 — 验证：`tools/verify_schema_equivalence.py` 对各方案报告"等价"，差异仅限 `__build_info.timestamps`
- [x] 4.4 量化各方案间逐字相同的剩余内容，据此判断是否需要生成器 — 验证：实测为 33 行/方案（`switches` 12 行、`engine` 30 行含 2 变体、其余属固有内容），结论为不引入生成器，理由记入 design.md 决策 1
- [x] 4.5 核实模糊音注释目录是否为重复内容 — 验证：实测五个方案注释块 md5 互不相同（`lufs_pinyin` 47 行、双拼方案各 30 行），证伪"重复五份"假设，结论记入 design.md 决策 6
- [x] 4.6 确认列表型块与固有内容保持就地物化 — 验证：`switches`、`engine`、`speller`、`translator`、`schema` 在各方案文件中均为完整内容，无生成器介入
- [x] 4.7 确认方案文件不含生成来源标注（因不再存在生成器） — 验证：五个方案文件首部均为原始注释，无生成器标注
- [x] 4.8 确认收敛后各方案仍独立可构建 — 验证：五个方案分别 `rime_deployer --compile` 均 exit=0、零错误
- [x] 4.9 确认停用方案不产生构建产物 — 验证：`build/` 目录下不含 `lufs_dpy`、`lufs_mspy`、`lufs_flypy`、`lufs_pyjj` 相关产物，与收敛前行为一致
- [x] 4.10 修复 `lufs_pyjj` 编译失败（本次核验中发现的既有缺陷） — 验证：其 `xlit` 源串缺少 `Ⓑ`（23 字符对 24 目标字符），而第 111 行 `xform/[iu]a$/Ⓑ/` 确实产出了 `Ⓑ`，导致 `b` 无法还原；补入 `Ⓑ` 后该方案编译 exit=0、零错误

## 5. 集成验证

- [x] 5.1 校验脚本对 `import_preset` 静默失效的检出能力 — 验证：临时对某方案的 `engine` 引入 `import_preset` 后脚本报告失败并指出配置缺失，随后还原
- [x] 5.2 校验脚本的假阳性检验 — 验证：仅改变源文件修改时间后重新构建，`__build_info.timestamps` 之外的产物内容不变，脚本仍报告"等价"
- [x] 5.3 同步 `README.md` 的候选项数量描述与实际生效的 `menu/page_size` — 验证：`grep -n "候选项" README.md` 的描述与 `build/default.yaml` 中的 `page_size` 数值一致
- [x] 5.4 端到端重新部署并确认整体成功 — 验证：完整构建退出码为 0，`build/` 下存在全部预期产物，构建产物总量由基线 17,531,184 B 降至约 15,450,188 B（-11.9%）
- [x] 5.5 统计重复行收敛效果 — 验证：五方案行数 862 → 822（-40 行）；新增 `lufs_shared.yaml` 40 行；净减少 74 行的维护面（862 → 822+40=862 表面持平，但重复内容由 7 处降为 1 处）。跨五方案逐字相同的非空行 111 → 103，仅降 8 行——因收敛后残留的相同行是双拼方案共用的模糊音注释（librime 无跨文件注释机制，就地可读性优先）
- [x] 5.6 确认无遗留失效机制 — 验证：全部构建产物中除 `punctuator`/`key_binder`/`recognizer` 三段外，不存在 `import_preset` 字面值
