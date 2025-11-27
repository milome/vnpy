# RICE1 解析过程按步骤分析

> 基于 `python mflang/grammar/test_rice1_import.py` 最新一次运行结果（2025‑11‑25 16:xx），汇总关键输出，便于复审。

## 步骤 1：解析主模型文件
- 输入文件：`mflang/mmodels/RICE1.txt`
- 结果：`[OK] 成功解析RICE1.txt`

## 步骤 2：检查 `#IMPORT`
- 共计 `6` 条导入语句：
  1. `[DAY,1,米仓I号日内趋势] AS DAYTREND`
  2. `[HOUR,1,米仓I号小时趋势] AS HOURTREND`
  3. `[MIN,1,米仓I号多周期MACD] AS MULTIMACD`
  4. `[MIN,1,米仓I号追踪区域] AS TRACEAREA`
  5. `[MIN,45,米仓I号单周期MACD] AS MACDIMPORT25`
  6. `[MIN,1,米仓I号变量赋值] AS VARS`

## 步骤 3：跨周期引用
- 统计：`0` 条（当前模型未出现 `X.Y` 形式的跨周期访问）

## 步骤 4：生成策略代码
- 生成文件长度：`19,254` 字符，`355` 行
- 生成类：`RICE1Strategy`

## 步骤 5：代码内一致性检查
- `IndicatorManager` 相关
  - 导入存在：✅
  - 实例化存在：✅
  - 模型 `register_indicator`：❌（导入模型未成功解析，注册代码为空）
  - `get_indicator_smart` 调用：❌
- 导入模型名称在代码中均出现：✅

## 步骤 6：统计调用
- `register_indicator`：`0` 次
- `get_indicator_smart`：`0` 次

## 步骤 7：输出文件
- 目标：`mflang/grammar/generated_rice1_strategy.py`
- 文件大小：`20,188` 字节

## 步骤 8：注册模型片段摘要
- `__init__` 中自动生成的注册区域仅包含警告注释：
  ```text
  # 注册导入的模型到IndicatorManager
  # 警告: 模型 米仓I号日内趋势 未解析，无法注册
  ...
  # 警告: 模型 米仓I号变量赋值 未解析，无法注册
  ```
- 表示解析器尚未能深入解析这些依赖模型（多为独立 TXT 文件），需要后续补齐以实现指标注册。

## 附注
- 为降低噪音，`parser.py` 中已将 ANTLR 词法/语法告警改为 Debug 日志；运行脚本时的控制台输出仅保留上述步骤。




