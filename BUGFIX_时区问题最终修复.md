# Bug修复：时区不一致问题最终修复

## 问题

```
[多周期] 检查数据完整性失败: can't subtract offset-naive and offset-aware datetimes，跳过下载
```

## 修复

在 `_check_data_completeness()` 方法中添加时区统一处理：

```python
import pytz
from vnpy.trader.setting import SETTINGS

# 获取数据库时区配置
db_tz_name = SETTINGS.get("database.timezone", "Asia/Shanghai")
database_tz = pytz.timezone(db_tz_name)

# 统一转换所有 datetime 到数据库时区
if db_earliest.tzinfo is None:
    db_earliest = database_tz.localize(db_earliest)
else:
    db_earliest = db_earliest.astimezone(database_tz)

# 对 db_latest, user_start, user_end 进行同样处理...
```

## 关键点

1. **使用数据库配置的时区**：`SETTINGS.get("database.timezone")`
2. **naive datetime 使用 `localize()`**
3. **aware datetime 使用 `astimezone()`**
4. **所有 datetime 统一后才能比较**

## 状态

✅ 修复已应用
✅ logger 保留不变（使用原有的 logger.info 等）

修复完成！🎉

