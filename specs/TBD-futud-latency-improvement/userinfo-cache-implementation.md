# UserInfo 缓存实现方案

**目标**: 将 UserInfo(1005) 延迟从 734.33ms 降至 <1ms（缓存命中时）  
**优先级**: P0（立即实施）  
**预计耗时**: 1-2小时

## 一、现状分析

### 1.1 调用情况

根据延迟统计：
- **API类型**: UserInfo(1005)
- **调用次数**: 3次（极低频率）
- **平均延迟**: 734.33ms（极高）
- **延迟组成**: 100%为OpenD延迟，无本地处理

### 1.2 调用位置分析

**可能情况**:
1. **富途SDK内部自动调用**: 在连接/初始化时自动查询用户信息
2. **我们的代码中直接调用**: 需要查找代码中的调用位置
3. **通过富途SDK接口间接调用**: 某些操作可能触发用户信息查询

### 1.3 富途SDK接口

根据富途SDK文档，可能的用户信息查询接口：
- `trade_ctx.accinfo_query()` - 查询账户信息（已在代码中使用）
- 可能还有其他用户信息相关接口

**注意**: UserInfo(1005) 可能是富途OpenD协议层面的调用，不一定对应我们代码中的某个具体方法。

## 二、设计方案

### 2.1 策略选择

由于 UserInfo 调用频率极低（仅3次），但延迟极高，我们采用以下策略：

1. **如果找到直接调用位置**: 实现缓存机制
2. **如果是SDK内部调用**: 通过连接池/预连接优化
3. **如果无法直接优化**: 至少添加监控和日志，便于后续分析

### 2.2 缓存结构设计

```python
# 缓存结构
{
    "user_info": dict,           # 用户信息数据
    "cache_time": float,         # 缓存时间戳
    "cache_ttl": int            # 缓存TTL（秒）
}
```

### 2.3 缓存策略

1. **TTL策略**: 
   - 默认TTL: 3600秒（1小时）
   - 用户信息变化频率低，1小时足够

2. **刷新策略**:
   - **启动时查询**: 连接成功后查询一次并缓存
   - **按需刷新**: 提供手动刷新接口
   - **自动失效**: TTL过期后自动失效

3. **缓存失效**:
   - TTL过期自动失效
   - 连接断开时清空缓存
   - 手动刷新接口

## 三、实现步骤

### Step 1: 查找 UserInfo 调用位置

**任务**: 确定 UserInfo 是在哪里被调用的

**方法**:
1. 搜索代码中是否有直接调用用户信息相关接口
2. 检查富途SDK文档，了解 UserInfo(1005) 对应的接口
3. 如果找不到，可能是SDK内部自动调用

**文件**: 整个项目  
**命令**: 
```bash
# 搜索可能的用户信息查询
grep -r "user_info\|UserInfo\|accinfo\|account_info" vnpy_futu/
```

### Step 2: 添加缓存字段到 `__init__`

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `__init__` 方法（约204行）

**修改内容**:
```python
# 在 __init__ 方法中添加
# UserInfo 缓存
self._user_info_cache: Optional[Dict[str, Any]] = None
self._user_info_cache_time: float = 0.0
self._user_info_cache_ttl: int = 3600  # 默认1小时
self._user_info_cache_lock = RLock()  # 缓存读写锁
```

### Step 3: 实现缓存查询方法（如果找到调用位置）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 在 `query_account()` 方法附近（约2016行）

**新增方法**:
```python
def get_user_info_cached(self) -> Optional[Dict[str, Any]]:
    """
    获取用户信息（带缓存）
    
    Returns:
        用户信息字典或None（失败时）
    """
    current_time = time()
    
    with self._user_info_cache_lock:
        # 检查缓存
        if (self._user_info_cache is not None and 
            current_time - self._user_info_cache_time < self._user_info_cache_ttl):
            self.write_log(
                f"[UserInfo缓存] 命中缓存 "
                f"(缓存年龄: {current_time - self._user_info_cache_time:.1f}秒)"
            )
            return self._user_info_cache.copy()  # 返回副本
        
        # 缓存未命中或已过期，查询远程
        self.write_log("[UserInfo缓存] 缓存未命中，查询远程")
        
        # 注意：这里需要根据实际找到的接口来调用
        # 如果 UserInfo 是 SDK 内部调用的，这里可能无法直接优化
        # 示例代码（需要根据实际情况修改）:
        try:
            # 假设有用户信息查询接口（需要根据实际SDK接口调整）
            # ret, data = self.trade_ctx.get_user_info()  # 示例
            # if ret != 0:
            #     self.write_log(f"[UserInfo缓存] 查询失败: {data}")
            #     return None
            
            # 如果找不到直接接口，可能需要通过其他方式获取
            # 例如：通过 accinfo_query 获取部分用户信息
            if not self.trade_ctx:
                self.write_log("[UserInfo缓存] 交易上下文未初始化")
                return None
            
            # 使用账户信息作为用户信息的替代（如果UserInfo无法直接获取）
            code, data = self.trade_ctx.accinfo_query(trd_env=self.env, acc_id=0)
            if code != 0:
                self.write_log(f"[UserInfo缓存] 查询失败: {data}")
                return None
            
            # 构造用户信息（根据实际需求调整）
            user_info = {
                "account_info": data.to_dict('records')[0] if not data.empty else {},
                "query_time": current_time
            }
            
            # 更新缓存
            self._user_info_cache = user_info
            self._user_info_cache_time = current_time
            
            self.write_log("[UserInfo缓存] 已缓存用户信息")
            return user_info.copy()
            
        except Exception as e:
            self.write_log(f"[UserInfo缓存] 查询异常: {str(e)}")
            return None
```

### Step 4: 在连接成功后查询并缓存（如果找到调用位置）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `connect_trade()` 方法（约1188行）或 `query_data()` 方法（约285行）

**修改内容**:
```python
def query_data(self) -> None:
    """查询数据"""
    sleep(2.0)  # 等待两秒直到连接成功

    self.query_contract()
    self.query_trade()
    self.query_order()
    self.query_position()
    self.query_account()
    
    # ✅ 新增：查询并缓存用户信息（如果找到调用位置）
    # self.get_user_info_cached()  # 取消注释如果实现了缓存方法
    
    # 初始化主力合约映射
    self._check_main_contract_switch()

    # 初始化定时查询任务
    self.event_engine.register(EVENT_TIMER, self.process_timer_event)
```

### Step 5: 添加缓存管理方法

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 在 `get_user_info_cached()` 方法之后

**新增方法**:
```python
def clear_user_info_cache(self) -> None:
    """清空 UserInfo 缓存"""
    with self._user_info_cache_lock:
        self._user_info_cache = None
        self._user_info_cache_time = 0.0
        self.write_log("[UserInfo缓存] 已清空缓存")

def refresh_user_info_cache(self) -> Optional[Dict[str, Any]]:
    """强制刷新 UserInfo 缓存"""
    self.clear_user_info_cache()
    return self.get_user_info_cached()
```

### Step 6: 连接断开时清空缓存

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `close()` 方法（约2097行）

**修改内容**:
```python
def close(self) -> None:
    """关闭连接"""
    # ... 现有代码 ...
    
    # ✅ 新增：清空缓存
    self.clear_user_info_cache()
    
    # ... 现有代码 ...
```

### Step 7: 添加监控和日志（如果无法直接优化）

**如果 UserInfo 是 SDK 内部自动调用的，无法直接优化，至少添加监控**:

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 在连接相关方法中添加日志

**修改内容**:
```python
def connect_trade(self) -> None:
    """连接交易接口"""
    # ... 现有代码 ...
    
    # ✅ 新增：记录连接时间，用于分析UserInfo调用时机
    connect_start_time = time()
    self.write_log(f"[UserInfo监控] 开始连接交易接口: {connect_start_time}")
    
    # ... 现有代码 ...
    
    # 连接成功后
    connect_end_time = time()
    connect_duration = (connect_end_time - connect_start_time) * 1000
    self.write_log(
        f"[UserInfo监控] 交易接口连接完成: "
        f"耗时 {connect_duration:.2f}ms"
    )
```

## 四、替代方案（如果无法直接优化）

### 4.1 连接池优化

如果 UserInfo 是在连接时自动调用的，可以通过以下方式优化：

1. **保持长连接**: 减少重连次数，从而减少 UserInfo 调用
2. **连接复用**: 如果可能，复用已有连接
3. **预连接**: 提前建立连接，避免使用时才连接

### 4.2 异步连接

将连接操作改为异步，不阻塞主流程：

```python
def connect_async(self, setting: dict) -> None:
    """异步连接交易接口"""
    def _connect():
        self.connect(setting)
    
    thread = Thread(target=_connect)
    thread.daemon = True
    thread.start()
```

## 五、测试验证

### 5.1 功能测试

1. **缓存命中测试**:
   - 第一次查询：应该看到 "缓存未命中，查询远程"
   - 第二次查询：应该看到 "命中缓存"
   - 验证延迟：第二次查询应该 <1ms

2. **缓存过期测试**:
   - 设置短TTL（如10秒）
   - 等待TTL过期后查询：应该重新查询远程

3. **缓存清空测试**:
   - 调用 `clear_user_info_cache()`：应该清空缓存
   - 再次查询：应该重新查询远程

### 5.2 性能测试

**测试脚本**:
```python
import time
from vnpy_futu import FutuGateway

gateway = FutuGateway(event_engine, "FUTU")
gateway.connect(setting)

# 等待连接完成
time.sleep(3)

# 第一次查询（应该慢，如果实现了缓存方法）
start = time.time()
user_info = gateway.get_user_info_cached()  # 如果实现了
first_time = (time.time() - start) * 1000
print(f"第一次查询耗时: {first_time:.2f}ms")

# 第二次查询（应该快）
start = time.time()
user_info = gateway.get_user_info_cached()  # 如果实现了
second_time = (time.time() - start) * 1000
print(f"第二次查询耗时: {second_time:.2f}ms")

if first_time > 0:
    print(f"性能提升: {first_time / second_time:.1f}x")
```

## 六、TODO 清单

### T1: 查找 UserInfo 调用位置（30分钟）

**任务**:
- [ ] 搜索代码中是否有直接调用用户信息相关接口
- [ ] 检查富途SDK文档，了解 UserInfo(1005) 对应的接口
- [ ] 如果找不到，记录为"SDK内部自动调用"

**文件**: 整个项目  
**方法**: 
```bash
grep -r "user_info\|UserInfo\|accinfo\|account_info" vnpy_futu/
```

---

### T2: 添加缓存字段（10分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `__init__` 方法（约204行）

**任务**:
- [ ] 添加 `_user_info_cache: Optional[Dict[str, Any]] = None`
- [ ] 添加 `_user_info_cache_time: float = 0.0`
- [ ] 添加 `_user_info_cache_ttl: int = 3600`
- [ ] 添加 `_user_info_cache_lock = RLock()`

---

### T3: 实现缓存查询方法（30分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 在 `query_account()` 方法附近（约2016行）

**任务**:
- [ ] 实现 `get_user_info_cached()` 方法
- [ ] 实现缓存检查逻辑
- [ ] 实现缓存更新逻辑（根据实际找到的接口）
- [ ] 添加日志输出

**注意**: 
- 如果找不到直接调用位置，此任务可能需要调整
- 可能需要使用 `accinfo_query` 作为替代方案

---

### T4: 在连接成功后查询并缓存（10分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `query_data()` 方法（约285行）

**任务**:
- [ ] 在 `query_data()` 中调用 `get_user_info_cached()`
- [ ] 确保在连接成功后查询

---

### T5: 添加缓存管理方法（15分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 在 `get_user_info_cached()` 方法之后

**任务**:
- [ ] 实现 `clear_user_info_cache()` 方法
- [ ] 实现 `refresh_user_info_cache()` 方法
- [ ] 添加日志输出

---

### T6: 连接断开时清空缓存（5分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `close()` 方法（约2097行）

**任务**:
- [ ] 在 `close()` 方法中调用 `self.clear_user_info_cache()`

---

### T7: 添加监控和日志（可选，15分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `connect_trade()` 方法（约1188行）

**任务**:
- [ ] 添加连接时间监控
- [ ] 添加日志输出，便于分析 UserInfo 调用时机

---

### T8: 编写测试用例（20分钟）

**文件**: `tests/test_futu_userinfo_cache.py`（新建）

**任务**:
- [ ] 测试缓存命中（如果实现了缓存方法）
- [ ] 测试缓存过期
- [ ] 测试缓存清空
- [ ] 性能测试（验证延迟降低）

---

## 七、预期效果

### 7.1 如果找到直接调用位置并实现缓存

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 单次查询延迟 | 734.33ms | <1ms | >700x |
| 3次查询总耗时 | 2.2秒 | <3ms | >700x |
| 缓存命中率 | 0% | >66% | - |

### 7.2 如果是SDK内部调用

- **无法直接优化**: 但可以通过连接池/预连接减少调用次数
- **监控价值**: 至少可以监控和分析调用时机

## 八、注意事项

1. **调用位置不确定**: UserInfo 可能是 SDK 内部自动调用的，需要先确认
2. **接口可能不存在**: 如果找不到直接的用户信息查询接口，可能需要使用替代方案
3. **调用频率低**: 虽然延迟高，但调用频率极低（仅3次），优化收益相对较小
4. **优先级**: 相比 StaticInfo（787次调用），UserInfo 的优先级可以稍低

## 九、实施建议

1. **先执行 T1**: 查找调用位置，确定是否可以直接优化
2. **如果找到调用位置**: 执行 T2-T6，实现完整缓存机制
3. **如果找不到调用位置**: 执行 T7，至少添加监控
4. **最后执行 T8**: 编写测试用例验证

**预计总耗时**: 1-2小时（取决于是否找到调用位置）

