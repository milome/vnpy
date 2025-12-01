# 登录阶段打点 + 长连接检查 TODO 清单

**目标**: 
1. 通过精细打点，定位 UserInfo(1005) 734ms 延迟发生在登录的哪个阶段
2. 检查并优化连接生命周期，避免不必要的重复 connect/close，减少 UserInfo 触发次数

**优先级**: P0  
**预计总耗时**: 2-3小时

---

## 一、登录阶段打点（Login Profiling）

### L1: 为交易连接 `connect_trade()` 增加打点日志（30分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `connect_trade()` 方法（约1186行）

**任务**:
- [ ] 在函数开头记录开始时间
- [ ] 为关键步骤添加时间戳和耗时日志
- [ ] 在函数末尾输出总耗时

**修改前**:
```python
def connect_trade(self) -> None:
    """连接交易服务端"""
    if self.market == "HK":
        self.trade_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.HK, host=self.host, port=self.port,)
    elif self.market == "US":
        self.trade_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host=self.host, port=self.port,)
    elif self.market == "HK_FUTURE":
        self.trade_ctx = OpenFutureTradeContext(host=self.host, port=self.port)

    # ... handler 定义 ...

    # 交易接口解锁
    code, data = self.trade_ctx.unlock_trade(self.password)
    if code == RET_OK:
        self.write_log("交易接口解锁成功")
    else:
        self.write_log(f"交易接口解锁失败，原因：{data}")

    # 连接交易接口
    self.trade_ctx.set_handler(OrderHandler())
    self.trade_ctx.set_handler(DealHandler())
    self.trade_ctx.start()
    self.write_log("交易接口连接成功")
```

**修改后**:
```python
def connect_trade(self) -> None:
    """连接交易服务端"""
    start_time = time()
    self.write_log("[LoginProfile] 开始连接交易接口")
    
    # 步骤1: 创建交易上下文
    step_start = time()
    if self.market == "HK":
        self.trade_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.HK, host=self.host, port=self.port,)
    elif self.market == "US":
        self.trade_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host=self.host, port=self.port,)
    elif self.market == "HK_FUTURE":
        self.trade_ctx = OpenFutureTradeContext(host=self.host, port=self.port)
    step_duration = (time() - step_start) * 1000
    self.write_log(f"[LoginProfile] connect_trade: create_trade_ctx 耗时 {step_duration:.2f}ms")

    # ... handler 定义 ...

    # 步骤2: 交易接口解锁（可能触发 UserInfo）
    step_start = time()
    code, data = self.trade_ctx.unlock_trade(self.password)
    step_duration = (time() - step_start) * 1000
    if code == RET_OK:
        self.write_log(f"[LoginProfile] connect_trade: unlock_trade 耗时 {step_duration:.2f}ms - 解锁成功")
    else:
        self.write_log(f"[LoginProfile] connect_trade: unlock_trade 耗时 {step_duration:.2f}ms - 解锁失败: {data}")

    # 步骤3: 设置 handler
    step_start = time()
    self.trade_ctx.set_handler(OrderHandler())
    self.trade_ctx.set_handler(DealHandler())
    step_duration = (time() - step_start) * 1000
    self.write_log(f"[LoginProfile] connect_trade: set_handler 耗时 {step_duration:.2f}ms")

    # 步骤4: 启动交易接口
    step_start = time()
    self.trade_ctx.start()
    step_duration = (time() - step_start) * 1000
    self.write_log(f"[LoginProfile] connect_trade: start 耗时 {step_duration:.2f}ms")
    
    # 总耗时
    total_duration = (time() - start_time) * 1000
    self.write_log(f"[LoginProfile] connect_trade: 总耗时 {total_duration:.2f}ms")
    self.write_log("交易接口连接成功")
```

**关键点**:
- `unlock_trade()` 的耗时特别关注，因为可能触发 UserInfo(1005)
- 如果 `unlock_trade()` 耗时接近 734ms，说明 UserInfo 很可能在这里被触发

---

### L2: 为行情连接 `connect_quote()` 增加打点日志（20分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `connect_quote()` 方法（约1148行）

**任务**:
- [ ] 在函数开头记录开始时间
- [ ] 为关键步骤添加时间戳和耗时日志
- [ ] 在函数末尾输出总耗时

**修改前**:
```python
def connect_quote(self) -> None:
    """连接行情服务端"""
    self.quote_ctx: OpenQuoteContext = OpenQuoteContext(self.host, self.port)

    # ... handler 定义 ...

    self.quote_ctx.set_handler(QuoteHandler())
    self.quote_ctx.set_handler(OrderBookHandler())
    self.quote_ctx.start()
    print("开始订阅 MHImain")
    self.write_log("行情接口连接成功!!!")
```

**修改后**:
```python
def connect_quote(self) -> None:
    """连接行情服务端"""
    start_time = time()
    self.write_log("[LoginProfile] 开始连接行情接口")
    
    # 步骤1: 创建行情上下文
    step_start = time()
    self.quote_ctx: OpenQuoteContext = OpenQuoteContext(self.host, self.port)
    step_duration = (time() - step_start) * 1000
    self.write_log(f"[LoginProfile] connect_quote: create_quote_ctx 耗时 {step_duration:.2f}ms")

    # ... handler 定义 ...

    # 步骤2: 设置 handler
    step_start = time()
    self.quote_ctx.set_handler(QuoteHandler())
    self.quote_ctx.set_handler(OrderBookHandler())
    step_duration = (time() - step_start) * 1000
    self.write_log(f"[LoginProfile] connect_quote: set_handler 耗时 {step_duration:.2f}ms")

    # 步骤3: 启动行情接口
    step_start = time()
    self.quote_ctx.start()
    step_duration = (time() - step_start) * 1000
    self.write_log(f"[LoginProfile] connect_quote: start 耗时 {step_duration:.2f}ms")
    
    # 总耗时
    total_duration = (time() - start_time) * 1000
    self.write_log(f"[LoginProfile] connect_quote: 总耗时 {total_duration:.2f}ms")
    print("开始订阅 MHImain")
    self.write_log("行情接口连接成功!!!")
```

**关键点**:
- 行情连接通常不涉及 UserInfo，但打点有助于区分交易侧和行情侧的耗时

---

### L3: 在 `query_data()` 首次查询流程打点（25分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `query_data()` 方法（约285行）

**任务**:
- [ ] 在函数开头记录开始时间
- [ ] 为每个查询方法添加时间戳和耗时日志
- [ ] 在函数末尾输出总耗时

**修改前**:
```python
def query_data(self) -> None:
    """查询数据"""
    sleep(2.0)  # 等待两秒直到连接成功

    self.query_contract()
    self.query_trade()
    self.query_order()
    self.query_position()
    self.query_account()
    
    # 初始化主力合约映射
    self._check_main_contract_switch()

    # 初始化定时查询任务
    self.event_engine.register(EVENT_TIMER, self.process_timer_event)
```

**修改后**:
```python
def query_data(self) -> None:
    """查询数据"""
    start_time = time()
    self.write_log("[LoginProfile] 开始首轮数据查询")
    
    sleep(2.0)  # 等待两秒直到连接成功
    wait_duration = 2000.0  # 固定等待时间
    self.write_log(f"[LoginProfile] query_data: sleep(2.0) 等待 {wait_duration:.2f}ms")

    # 查询合约
    step_start = time()
    self.query_contract()
    step_duration = (time() - step_start) * 1000
    self.write_log(f"[LoginProfile] query_data: query_contract 耗时 {step_duration:.2f}ms")

    # 查询交易
    step_start = time()
    self.query_trade()
    step_duration = (time() - step_start) * 1000
    self.write_log(f"[LoginProfile] query_data: query_trade 耗时 {step_duration:.2f}ms")

    # 查询订单
    step_start = time()
    self.query_order()
    step_duration = (time() - step_start) * 1000
    self.write_log(f"[LoginProfile] query_data: query_order 耗时 {step_duration:.2f}ms")

    # 查询持仓
    step_start = time()
    self.query_position()
    step_duration = (time() - step_start) * 1000
    self.write_log(f"[LoginProfile] query_data: query_position 耗时 {step_duration:.2f}ms")

    # 查询账户
    step_start = time()
    self.query_account()
    step_duration = (time() - step_start) * 1000
    self.write_log(f"[LoginProfile] query_data: query_account 耗时 {step_duration:.2f}ms")
    
    # 初始化主力合约映射
    step_start = time()
    self._check_main_contract_switch()
    step_duration = (time() - step_start) * 1000
    self.write_log(f"[LoginProfile] query_data: _check_main_contract_switch 耗时 {step_duration:.2f}ms")

    # 总耗时
    total_duration = (time() - start_time) * 1000
    self.write_log(f"[LoginProfile] query_data: 首轮数据查询总耗时 {total_duration:.2f}ms")

    # 初始化定时查询任务
    self.event_engine.register(EVENT_TIMER, self.process_timer_event)
```

**关键点**:
- `query_contract()` 可能触发 StaticInfo(3202)，关注其耗时
- `_check_main_contract_switch()` 可能触发 FutureInfo(3218)，关注其耗时

---

### L4: 统一打点格式规范（10分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 所有打点位置

**任务**:
- [ ] 确保所有打点日志使用统一前缀 `[LoginProfile]`
- [ ] 确保日志格式统一：`[LoginProfile] <function_name>: <step_name> 耗时 XX.XXms`
- [ ] 确保总耗时日志格式：`[LoginProfile] <function_name>: 总耗时 XX.XXms`

**日志格式规范**:
```
[LoginProfile] <函数名>: <步骤名> 耗时 <数值>ms
[LoginProfile] <函数_name>: 总耗时 <数值>ms
```

**示例**:
- `[LoginProfile] connect_trade: create_trade_ctx 耗时 5.23ms`
- `[LoginProfile] connect_trade: unlock_trade 耗时 734.56ms`
- `[LoginProfile] connect_trade: 总耗时 750.12ms`

---

## 二、长连接检查（Connection Lifecycle Audit）

### C1: 检查网关 `connect()` 是否被重复调用（30分钟）

**文件**: 
- `vnpy_futu/vnpy_futu/futu_gateway.py` - `FutuGateway.connect()`（约265行）
- `vnpy/trader/engine.py` - `MainEngine` 相关方法（可选，用于理解调用链）

**任务**:
- [ ] 在 `connect()` 开头添加状态检查和日志
- [ ] 记录调用堆栈（可选，用于调试）

**修改前**:
```python
def connect(self, setting: dict) -> None:
    """连接交易接口"""
    self.host: str = setting["地址"]
    self.port: int = setting["端口"]
    self.market: str = setting["市场"]
    self.password: str = setting["密码"]
    self.env: TrdEnv = setting["环境"]

    self.connect_quote()
    self.connect_trade()
    # ...
```

**修改后**:
```python
def connect(self, setting: dict) -> None:
    """连接交易接口"""
    # ✅ 新增：检查连接状态
    if self.connected:
        import traceback
        stack = ''.join(traceback.format_stack()[-3:-1])  # 获取调用堆栈
        self.write_log(
            f"[ConnLifecycle] ⚠️ 重复 connect 调用！当前状态: connected=True\n"
            f"调用堆栈:\n{stack}"
        )
        # 暂时不阻止，先观察实际情况
        # TODO: 后续可以改为直接 return，防止重复 connect
    
    self.write_log(f"[ConnLifecycle] 开始 connect，当前状态: connected={self.connected}")
    
    self.host: str = setting["地址"]
    self.port: int = setting["端口"]
    self.market: str = setting["市场"]
    self.password: str = setting["密码"]
    self.env: TrdEnv = setting["环境"]

    self.connect_quote()
    self.connect_trade()
    
    # ... 线程启动代码 ...
    
    # ✅ 新增：标记为已连接
    self.connected = True
    self.connect_time = time()
    self.write_log(f"[ConnLifecycle] connect 完成，标记为 connected=True")
```

---

### C2: 为 `close()` 增加调用日志（15分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `close()` 方法（约2097行）

**任务**:
- [ ] 在函数开头打印当前状态和调用时间
- [ ] 记录连接存活时长
- [ ] 在关闭成功后打印确认日志

**修改前**:
```python
def close(self) -> None:
    """关闭连接"""
    if self.quote_ctx:
        self.quote_ctx.close()

    if self.trade_ctx:
        self.trade_ctx.close()
        
    # ... 线程处理 ...
```

**修改后**:
```python
def close(self) -> None:
    """关闭连接"""
    close_start_time = time()
    
    # ✅ 新增：记录关闭前的状态和连接存活时长
    if self.connected and self.connect_time:
        alive_duration = (close_start_time - self.connect_time) * 1000
        self.write_log(
            f"[ConnLifecycle] 开始 close，连接存活时长: {alive_duration:.2f}ms "
            f"({alive_duration/1000/60:.2f}分钟)"
        )
    else:
        self.write_log(f"[ConnLifecycle] 开始 close，当前状态: connected={self.connected}")
    
    # ✅ 新增：记录关闭前的上下文状态
    quote_ctx_exists = self.quote_ctx is not None
    trade_ctx_exists = self.trade_ctx is not None
    self.write_log(
        f"[ConnLifecycle] close 前状态: quote_ctx={quote_ctx_exists}, trade_ctx={trade_ctx_exists}"
    )

    if self.quote_ctx:
        self.quote_ctx.close()
        self.write_log("[ConnLifecycle] quote_ctx 已关闭")

    if self.trade_ctx:
        self.trade_ctx.close()
        self.write_log("[ConnLifecycle] trade_ctx 已关闭")
    
    # ✅ 新增：标记为未连接
    self.connected = False
    self.last_disconnect_time = close_start_time
    
    # ... 线程处理 ...
    
    close_duration = (time() - close_start_time) * 1000
    self.write_log(f"[ConnLifecycle] close 完成，耗时 {close_duration:.2f}ms")
```

---

### C3: 引入 `self.connected` 状态并维护（20分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 
- `__init__` 方法（约204行）
- `connect()` 方法（约265行）
- `close()` 方法（约2097行）

**任务**:
- [ ] 在 `__init__` 中添加连接状态字段
- [ ] 在 `connect()` 成功后设置为 `True`
- [ ] 在 `close()` 中设置为 `False`
- [ ] 在异常断开时也设置为 `False`

**修改位置1 - `__init__`**:
```python
def __init__(self, event_engine: EventEngine, gateway_name: str) -> None:
    """构造函数"""
    # ... 现有代码 ...
    
    # ✅ 新增：连接状态管理
    self.connected: bool = False
    self.connect_time: Optional[float] = None
    self.last_disconnect_time: Optional[float] = None
```

**修改位置2 - `connect()`**:
```python
def connect(self, setting: dict) -> None:
    """连接交易接口"""
    # ... 现有代码（包括 C1 的修改） ...
    
    # 在 connect_quote() 和 connect_trade() 成功后
    self.connected = True
    self.connect_time = time()
    self.write_log(f"[ConnLifecycle] connect 完成，标记为 connected=True")
```

**修改位置3 - `close()`**:
```python
def close(self) -> None:
    """关闭连接"""
    # ... 现有代码（包括 C2 的修改） ...
    
    # 在关闭上下文后
    self.connected = False
    self.last_disconnect_time = time()
```

**修改位置4 - 异常处理**（如果有异常断开逻辑）:
```python
# 在异常处理中也要设置
try:
    # ... 连接逻辑 ...
except Exception as e:
    self.connected = False
    self.write_log(f"[ConnLifecycle] 连接异常，标记为 connected=False: {str(e)}")
    raise
```

---

### C4: 增加"长连接"运行期统计（可选，20分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 
- `__init__` 方法（已在 C3 中添加字段）
- `connect()` 方法（已在 C3 中记录时间）
- `close()` 方法（已在 C2 中记录时间）

**任务**:
- [ ] 字段已在 C3 中添加，这里主要是确保统计逻辑完整
- [ ] 在 `close()` 中计算并打印连接存活时长（已在 C2 中实现）
- [ ] 可选：添加定期统计日志（在 `process_timer_event` 中）

**可选增强 - 定期统计**:
```python
def process_timer_event(self, event) -> None:
    """定时事件处理"""
    # ... 现有代码 ...
    
    # ✅ 可选：每60秒打印一次连接状态统计
    if self.count % 60 == 0 and self.connected and self.connect_time:
        alive_duration = (time() - self.connect_time) / 60  # 分钟
        self.write_log(
            f"[ConnLifecycle] 连接状态: 已连接 {alive_duration:.1f} 分钟"
        )
```

---

### C5: 整理"长连接 best practice" 文档条目（15分钟）

**文件**: 
- `specs/004-fix-realtime-tick/futud-latency-analysis.md` 或
- `performance/富途OpenAPI长连接建议.md`（新建）

**任务**:
- [ ] 创建文档说明长连接的重要性
- [ ] 列出最佳实践建议
- [ ] 说明频繁重连的影响

**文档内容框架**:
```markdown
## 长连接最佳实践

### 为什么需要长连接？

1. **减少初始化开销**: 
   - 每次 `connect()` 都会触发 UserInfo(1005) 734ms、StaticInfo(3202) 463ms 等慢查询
   - 频繁重连会导致这些慢查询反复触发，严重影响性能

2. **保持状态一致性**:
   - 长连接可以保持订阅状态、订单状态等
   - 避免重连后需要重新订阅、重新查询

### 最佳实践

1. **应用生命周期内只 connect 一次**:
   - 在应用启动时连接
   - 在应用关闭时 disconnect
   - 避免在策略/业务逻辑中频繁 connect/close

2. **异常重连策略**:
   - 只在连接异常断开时才重连
   - 使用指数退避策略，避免频繁重连
   - 重连前先检查 `self.connected` 状态

3. **避免的操作**:
   - ❌ 不要在策略中调用 `gateway.connect()`
   - ❌ 不要在定时任务中重复 connect
   - ❌ 不要为了"刷新"而 disconnect 再 connect

### 性能影响

- **单次 connect 开销**: 约 1-2 秒（包括 UserInfo、StaticInfo 等）
- **频繁重连影响**: 如果每分钟重连一次，每天会有 1440 次慢查询
- **优化收益**: 保持长连接可以避免 99% 的慢查询
```

---

## 三、验证与后续动作

### V1: 收集一段时间的登录/连接日志（1-7天）

**任务**:
- [ ] 部署上述所有打点后，在实际环境运行
- [ ] 收集包含 `[LoginProfile]` 和 `[ConnLifecycle]` 前缀的日志
- [ ] 分析日志，关注以下指标：

**分析指标**:
1. **登录阶段耗时**:
   - `connect_trade: unlock_trade` 的耗时是否接近 734ms？
   - `query_data: query_contract` 的耗时是否接近 463ms？
   - 总登录耗时是多少？

2. **连接生命周期**:
   - 是否存在短时间内多次 `connect/close`？
   - 连接平均存活时长是多少？
   - 是否有不必要的重连？

3. **UserInfo 触发时机**:
   - UserInfo 是否只在 `unlock_trade()` 时触发？
   - 是否在其他地方也被触发？

**日志收集命令**:
```bash
# 收集登录阶段日志
grep "\[LoginProfile\]" vnpy_trader.log > login_profile.log

# 收集连接生命周期日志
grep "\[ConnLifecycle\]" vnpy_trader.log > conn_lifecycle.log

# 统计 connect 次数
grep "\[ConnLifecycle\].*开始 connect" vnpy_trader.log | wc -l

# 统计 close 次数
grep "\[ConnLifecycle\].*开始 close" vnpy_trader.log | wc -l
```

---

### V2: 基于日志，决定是否需要进一步改造

**情况1: 发现频繁 connect/close**

**如果日志显示**:
- 短时间内多次 `connect/close`
- 连接存活时长很短（< 1小时）

**后续 TODO**:
- [ ] 在 `connect()` 中添加短路逻辑：`if self.connected: return`
- [ ] 检查上层调用代码，找出重复 connect 的原因
- [ ] 修复上层逻辑，避免不必要的重连

**情况2: UserInfo 只在 unlock_trade 时触发**

**如果日志显示**:
- `unlock_trade` 耗时接近 734ms
- UserInfo 只在登录时触发一次

**后续 TODO**:
- [ ] 在报告中标记 UserInfo 为"一次性、可接受"
- [ ] 降低 UserInfo 优化优先级
- [ ] 重点关注 StaticInfo 和 RequestHistoryKL 优化

**情况3: 发现其他触发点**

**如果日志显示**:
- UserInfo 在其他地方也被触发
- 需要进一步分析触发原因

**后续 TODO**:
- [ ] 深入分析触发点
- [ ] 考虑是否需要其他优化策略

---

## 实施顺序建议

### 第一阶段：登录阶段打点（约1.5小时）
1. **L1** → **L2** → **L3** → **L4**
2. 目标：定位 UserInfo 延迟发生在哪个阶段

### 第二阶段：长连接检查（约1.5小时）
1. **C3** → **C1** → **C2** → **C4**（可选）→ **C5**
2. 目标：检查并优化连接生命周期

### 第三阶段：验证与分析（1-7天）
1. **V1** → **V2**
2. 目标：基于日志数据，决定后续优化方向

---

## 预期效果

### 登录阶段打点
- ✅ 精确定位 UserInfo 734ms 延迟发生在哪个步骤
- ✅ 识别登录阶段的性能瓶颈
- ✅ 为后续优化提供数据支持

### 长连接检查
- ✅ 识别是否存在频繁重连问题
- ✅ 建立连接状态管理机制
- ✅ 为后续"防重复 connect"提供基础

### 整体收益
- 📊 **数据驱动**: 基于真实日志数据做决策，而不是猜测
- 🎯 **精准优化**: 知道优化重点在哪里，避免无效优化
- 📈 **性能提升**: 减少不必要的重连，降低慢查询频率

---

## 注意事项

1. **日志量**: 打点会增加日志量，建议在生产环境适度使用
2. **性能影响**: 打点本身有微小性能开销，但可以忽略不计
3. **向后兼容**: 所有修改都是新增日志，不影响现有功能
4. **可配置**: 后续可以考虑通过配置开关控制打点日志

