# UserInfo 缓存实现 TODO 清单

**目标**: 将 UserInfo(1005) 延迟从 734.33ms 降至 <1ms  
**优先级**: P0  
**预计总耗时**: 1-2小时

---

## ⚠️ 前置任务：查找调用位置

**重要**: UserInfo(1005) 可能是富途SDK内部自动调用的，需要先确认调用位置。

### T0: 查找 UserInfo 调用位置（30分钟）

**任务**:
- [ ] 搜索代码中是否有直接调用用户信息相关接口
- [ ] 检查富途SDK文档，了解 UserInfo(1005) 对应的接口
- [ ] 如果找不到，记录为"SDK内部自动调用"

**搜索命令**:
```bash
# 在项目根目录执行
grep -r "user_info\|UserInfo\|accinfo\|account_info" vnpy_futu/
```

**预期结果**:
- **情况1**: 找到直接调用位置 → 可以实现完整缓存机制
- **情况2**: 找不到直接调用位置 → 可能是SDK内部调用，只能添加监控

---

## ✅ T1: 添加缓存字段（10分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `__init__` 方法（约204行）

**任务**:
- [ ] 添加 `_user_info_cache: Optional[Dict[str, Any]] = None`
- [ ] 添加 `_user_info_cache_time: float = 0.0`
- [ ] 添加 `_user_info_cache_ttl: int = 3600`（1小时）
- [ ] 添加 `_user_info_cache_lock = RLock()`

**代码位置**: 在 `self._tick_cache` 之后（约236行）

**代码示例**:
```python
# ✅ 新增：UserInfo 缓存
self._user_info_cache: Optional[Dict[str, Any]] = None
self._user_info_cache_time: float = 0.0
self._user_info_cache_ttl: int = 3600  # 默认1小时
self._user_info_cache_lock = RLock()  # 缓存读写锁
```

---

## ✅ T2: 实现缓存查询方法（30分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 在 `query_account()` 方法之后（约2032行）

**任务**:
- [ ] 实现 `get_user_info_cached()` 方法
- [ ] 实现缓存检查逻辑
- [ ] 实现缓存更新逻辑（根据T0找到的接口）
- [ ] 添加日志输出

**注意**: 
- 如果T0找不到直接调用位置，此方法可能需要使用 `accinfo_query` 作为替代
- 或者标记为"待实现"，先添加监控

**代码框架**:
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
            self.write_log("[UserInfo缓存] 命中缓存")
            return self._user_info_cache.copy()
        
        # 缓存未命中，查询远程
        self.write_log("[UserInfo缓存] 缓存未命中，查询远程")
        
        # TODO: 根据T0找到的接口实现查询逻辑
        # 如果找不到，可以使用 accinfo_query 作为替代
        try:
            if not self.trade_ctx:
                return None
            
            # 示例：使用账户信息作为替代（需要根据实际情况调整）
            code, data = self.trade_ctx.accinfo_query(trd_env=self.env, acc_id=0)
            if code != 0:
                return None
            
            user_info = {
                "account_info": data.to_dict('records')[0] if not data.empty else {},
                "query_time": current_time
            }
            
            # 更新缓存
            self._user_info_cache = user_info
            self._user_info_cache_time = current_time
            
            return user_info.copy()
        except Exception as e:
            self.write_log(f"[UserInfo缓存] 查询异常: {str(e)}")
            return None
```

---

## ✅ T3: 在连接成功后查询并缓存（10分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `query_data()` 方法（约285行）

**任务**:
- [ ] 在 `query_data()` 中调用 `get_user_info_cached()`
- [ ] 确保在连接成功后查询

**修改位置**: 在 `self.query_account()` 之后

**修改前**:
```python
def query_data(self) -> None:
    """查询数据"""
    sleep(2.0)
    self.query_contract()
    self.query_trade()
    self.query_order()
    self.query_position()
    self.query_account()
    
    # 初始化主力合约映射
    self._check_main_contract_switch()
```

**修改后**:
```python
def query_data(self) -> None:
    """查询数据"""
    sleep(2.0)
    self.query_contract()
    self.query_trade()
    self.query_order()
    self.query_position()
    self.query_account()
    
    # ✅ 新增：查询并缓存用户信息
    self.get_user_info_cached()
    
    # 初始化主力合约映射
    self._check_main_contract_switch()
```

---

## ✅ T4: 添加缓存管理方法（15分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 在 `get_user_info_cached()` 方法之后

**任务**:
- [ ] 实现 `clear_user_info_cache()` 方法
- [ ] 实现 `refresh_user_info_cache()` 方法
- [ ] 添加日志输出

**代码示例**:
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

---

## ✅ T5: 连接断开时清空缓存（5分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `close()` 方法（约2097行）

**任务**:
- [ ] 在 `close()` 方法中调用 `self.clear_user_info_cache()`

**修改位置**: 在 `if self.trade_ctx:` 之前

**修改前**:
```python
def close(self) -> None:
    """关闭连接"""
    if self.quote_ctx:
        self.quote_ctx.close()
    if self.trade_ctx:
        self.trade_ctx.close()
```

**修改后**:
```python
def close(self) -> None:
    """关闭连接"""
    # ✅ 新增：清空缓存
    self.clear_user_info_cache()
    
    if self.quote_ctx:
        self.quote_ctx.close()
    if self.trade_ctx:
        self.trade_ctx.close()
```

---

## ✅ T6: 添加监控和日志（可选，15分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `connect_trade()` 方法（约1188行）

**任务**:
- [ ] 添加连接时间监控
- [ ] 添加日志输出，便于分析 UserInfo 调用时机

**代码示例**:
```python
def connect_trade(self) -> None:
    """连接交易接口"""
    # ✅ 新增：记录连接开始时间
    connect_start_time = time()
    self.write_log(f"[UserInfo监控] 开始连接交易接口")
    
    # ... 现有代码 ...
    
    # 连接成功后
    connect_end_time = time()
    connect_duration = (connect_end_time - connect_start_time) * 1000
    self.write_log(
        f"[UserInfo监控] 交易接口连接完成: 耗时 {connect_duration:.2f}ms"
    )
```

---

## ✅ T7: 编写测试用例（20分钟）

**文件**: `tests/test_futu_userinfo_cache.py`（新建）

**任务**:
- [ ] 测试缓存命中（如果实现了缓存方法）
- [ ] 测试缓存过期
- [ ] 测试缓存清空
- [ ] 性能测试（验证延迟降低）

**测试脚本框架**:
```python
def test_userinfo_cache_hit():
    """测试缓存命中"""
    gateway = FutuGateway(event_engine, "FUTU")
    gateway.connect(setting)
    
    # 等待连接完成
    time.sleep(3)
    
    # 第一次查询（应该慢）
    start = time.time()
    user_info1 = gateway.get_user_info_cached()
    first_time = (time.time() - start) * 1000
    
    # 第二次查询（应该快）
    start = time.time()
    user_info2 = gateway.get_user_info_cached()
    second_time = (time.time() - start) * 1000
    
    assert second_time < 10  # 应该 <10ms
    if first_time > 0:
        assert first_time / second_time > 100  # 性能提升 >100x
```

---

## 实施顺序

### 情况1: 找到直接调用位置

1. **T0** → **T1** → **T2** → **T3** → **T4** → **T5** → **T7**
2. **预计耗时**: 约1.5小时

### 情况2: 找不到直接调用位置（SDK内部调用）

1. **T0** → **T1** → **T6**（只添加监控）
2. **预计耗时**: 约1小时
3. **后续**: 考虑连接池/预连接优化

---

## 验证清单

完成所有任务后，验证以下内容：

- [ ] 第一次查询用户信息：日志显示 "缓存未命中，查询远程"（如果实现了）
- [ ] 第二次查询用户信息：日志显示 "命中缓存"，延迟 <1ms（如果实现了）
- [ ] 连接断开：缓存被清空
- [ ] 性能测试：延迟降低 >700x（如果实现了）

---

## 预期效果

### 如果找到调用位置并实现缓存

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 单次查询延迟 | 734.33ms | <1ms | >700x |
| 3次查询总耗时 | 2.2秒 | <3ms | >700x |
| 缓存命中率 | 0% | >66% | - |

### 如果是SDK内部调用

- **无法直接优化**: 但可以通过连接池/预连接减少调用次数
- **监控价值**: 至少可以监控和分析调用时机
- **后续优化**: 考虑保持长连接，减少重连次数

---

## 注意事项

1. **调用位置不确定**: 需要先执行 T0 确认
2. **接口可能不存在**: 如果找不到直接接口，可能需要使用替代方案
3. **调用频率低**: 虽然延迟高，但调用频率极低（仅3次），优化收益相对较小
4. **优先级**: 相比 StaticInfo（787次调用），UserInfo 的优先级可以稍低

