# VeighNa数据录制使用指南

本目录包含了使用vnpy_datarecorder模块进行实时数据录制的完整示例和配置。

## 功能概述

DataRecorder模块可以实时录制：
- **Tick数据**：逐笔成交数据，包含最新价、买卖盘价格和数量等
- **K线数据**：基于Tick数据自动生成的1分钟K线数据

录制的数据会自动保存到数据库中，可用于：
- 策略回测
- 历史数据分析
- 实盘策略初始化

## 文件说明

- `run_data_recorder.py`: 启动数据录制程序的主文件
- `data_recorder_config.py`: 数据录制配置示例
- `README.md`: 本使用说明文档

## 使用步骤

### 1. 准备工作

确保已安装必要的依赖：
```bash
pip install vnpy_datarecorder
pip install vnpy_futu  # 如果使用富途接口
```

### 2. 启动程序

运行数据录制程序：
```bash
python run_data_recorder.py
```

### 3. 连接交易接口

1. 启动富途牛牛客户端
2. 开启OpenD服务（端口11111）
3. 在VeighNa界面中连接富途接口

### 4. 配置数据录制

#### 方法一：通过界面操作

1. 点击菜单栏的"功能" -> "行情记录"
2. 在"本地代码"输入框中输入合约代码（如：00700.HK）
3. 点击"K线记录"下的"添加"按钮添加K线录制
4. 点击"Tick记录"下的"添加"按钮添加Tick录制

#### 方法二：通过代码配置

使用`data_recorder_config.py`中的配置类：

```python
from data_recorder_config import setup_recording_example

# 在主程序中调用
config = setup_recording_example(main_engine)
```

### 5. 监控录制状态

- 在"行情记录"窗口中可以看到当前录制的合约列表
- 日志区域会显示录制状态和错误信息
- 可以调整"写入间隔"来控制数据写入频率

## 合约代码格式

不同市场的合约代码格式：

### 港股
- 腾讯控股：`00700.HK`
- 中国移动：`00941.HK`
- 友邦保险：`01299.HK`

### 美股
- 苹果：`AAPL.US`
- 微软：`MSFT.US`
- 谷歌：`GOOGL.US`

### 期货
- 恒生指数期货：`HSI2412.HKFE`
- 小型恒生指数期货：`MHI2412.HKFE`

## 数据存储

录制的数据会保存到SQLite数据库中：
- 默认位置：`~/.vnpy/database.db`
- Tick数据表：`dbbardata`
- K线数据表：`dbtickdata`

## 数据查看

可以通过以下方式查看录制的数据：

1. **DataManager模块**：在VeighNa界面中查看和管理数据
2. **直接查询数据库**：使用SQL工具查询SQLite数据库
3. **编程方式**：通过vnpy的数据库接口查询

## 注意事项

1. **交易时间**：只有在交易时间内才能录制到实时数据
2. **网络连接**：确保网络连接稳定，避免数据丢失
3. **存储空间**：Tick数据量较大，注意磁盘空间
4. **合约有效性**：确保输入的合约代码有效且可交易

## 常见问题

### Q: 为什么没有录制到数据？
A: 检查以下几点：
- 交易接口是否正常连接
- 合约代码是否正确
- 是否在交易时间内
- 合约是否有实时行情

### Q: 如何停止录制？
A: 在"行情记录"窗口中选择要停止的合约，点击"移除"按钮

### Q: 数据保存在哪里？
A: 默认保存在用户目录下的`.vnpy/database.db`文件中

### Q: 如何备份录制的数据？
A: 可以直接复制`database.db`文件进行备份

## 高级配置

### 自定义数据过滤

可以在`RecorderEngine`中配置数据过滤参数：
- `filter_window`: Tick数据时间过滤窗口（默认60秒）
- `timer_interval`: 数据写入间隔（默认10秒）

### 批量配置

使用配置文件批量添加录制合约：

```python
# 创建配置文件
recording_config = {
    "tick": ["00700.HK", "00941.HK", "01299.HK"],
    "bar": ["00700.HK", "00941.HK", "01299.HK"]
}

# 批量添加
for symbol in recording_config["tick"]:
    recorder_engine.add_tick_recording(symbol)

for symbol in recording_config["bar"]:
    recorder_engine.add_bar_recording(symbol)
```

## 技术支持

如有问题，请参考：
- [VeighNa官方文档](https://www.vnpy.com)
- [vnpy_datarecorder GitHub](https://github.com/vnpy/vnpy_datarecorder)
