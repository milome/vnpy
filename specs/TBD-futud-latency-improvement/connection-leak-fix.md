# 富途OpenAPI连接泄露问题修复

## 问题描述

错误日志显示：
```
InitConnect fail: 连接个数超过128，请关闭无用连接
```

这表明富途OpenAPI的连接数已经达到上限（128个），无法建立新连接。

## 问题分析

### 可能的原因

1. **Datafeed连接未正确关闭**
   - `Datafeed`类创建了`OpenQuoteContext`连接
   - 虽然有`close()`方法，但可能没有被正确调用
   - 程序异常退出时连接没有清理

2. **Gateway连接重复创建**
   - 多次调用`connect()`方法可能创建多个连接实例
   - 旧连接没有被正确关闭

3. **多个程序实例同时运行**
   - 如果多个vnpy程序实例同时运行，会共享同一个富途OpenD服务
   - 每个实例都会创建连接，导致连接数累加

4. **程序异常退出**
   - 程序崩溃或强制退出时，连接没有通过`close()`方法关闭
   - 富途OpenD服务端的连接没有被释放

## 解决方案

### 方案1：确保Datafeed连接正确关闭（推荐）

检查`MainEngine.close()`方法是否关闭datafeed连接：

```python
# vnpy/trader/engine.py - MainEngine.close()
def close(self) -> None:
    """
    Make sure every gateway and app is closed properly before
    programme exit.
    """
    # Stop event engine first to prevent new timer event.
    self.event_engine.stop()

    # ✅ 添加：关闭datafeed连接
    from vnpy.trader.datafeed import get_datafeed
    datafeed = get_datafeed()
    if datafeed and hasattr(datafeed, 'close'):
        datafeed.close()

    for engine in self.engines.values():
        engine.close()

    for gateway in self.gateways.values():
        gateway.close()
```

### 方案2：在FutuGateway的close方法中确保完全关闭

确保在`close()`方法中：
- 先停止订阅
- 再关闭context
- 清理所有资源

```python
# vnpy_futu/vnpy_futu/futu_gateway.py - FutuGateway.close()
def close(self) -> None:
    """关闭接口"""
    try:
        # ✅ 先停止所有订阅
        if self.quote_ctx:
            # 取消所有订阅（如果有）
            # self.quote_ctx.unsubscribe_all()  # 如果API支持
            
            # 关闭连接
            self.quote_ctx.close()
            self.quote_ctx = None  # ✅ 设置为None，避免重复关闭

        if self.trade_ctx:
            # 解锁交易（如果已锁定）
            try:
                self.trade_ctx.unlock_trade(self.password)
            except:
                pass
            
            # 关闭连接
            self.trade_ctx.close()
            self.trade_ctx = None  # ✅ 设置为None，避免重复关闭
            
    except Exception as e:
        self.write_log(f"关闭连接时出错: {e}")
    
    # 等待线程结束并重置线程对象
    if self.thread and self.thread.is_alive():
        self.thread.join(timeout=5.0)
    
    # 重置线程对象，为下次连接做准备
    self.thread = Thread(target=self.query_data)
```

### 方案3：添加连接管理检查

在`connect()`方法中检查是否已有连接，先关闭旧连接：

```python
# vnpy_futu/vnpy_futu/futu_gateway.py - FutuGateway.connect()
def connect(self, setting: dict) -> None:
    """连接交易接口"""
    # ✅ 如果已有连接，先关闭
    if self.quote_ctx or self.trade_ctx:
        self.write_log("检测到已有连接，先关闭旧连接")
        self.close()
    
    self.host: str = setting["地址"]
    self.port: int = setting["端口"]
    self.market: str = setting["市场"]
    self.password: str = setting["密码"]
    self.env: TrdEnv = setting["环境"]

    self.connect_quote()
    self.connect_trade()
    # ... 其余代码
```

### 方案4：Datafeed的close方法改进

确保Datafeed的close方法更健壮：

```python
# vnpy_futu/vnpy_futu/datafeed.py - Datafeed.close()
def close(self) -> None:
    """关闭连接"""
    try:
        if self.quote_ctx:
            self.quote_ctx.close()
            self.quote_ctx = None  # ✅ 设置为None
            self.inited = False
    except Exception as e:
        # 记录错误但不抛出异常
        print(f"关闭Datafeed连接时出错: {e}")
```

## 临时解决方案

如果连接数已经超过128，需要：

1. **重启富途牛牛客户端**
   - 这会关闭所有OpenD连接
   - 释放所有连接资源

2. **关闭所有vnpy程序实例**
   - 确保所有实例都正确退出
   - 检查是否有僵尸进程

3. **检查是否有多个程序实例**
   - 只运行一个vnpy程序实例
   - 如果需要多个实例，考虑使用不同的OpenD端口

## 预防措施

1. **添加连接数监控**
   - 在连接前检查当前连接数
   - 如果接近上限（如>100），发出警告

2. **使用try-finally确保连接关闭**
   ```python
   try:
       # 使用连接
       pass
   finally:
       # 确保关闭
       if self.quote_ctx:
           self.quote_ctx.close()
   ```

3. **程序退出时确保调用close()**
   - 使用atexit模块注册清理函数
   - 确保异常退出时也能清理连接

## 实施建议

优先实施方案1和方案2，这些是最关键的修复。方案3和方案4作为增强措施。

