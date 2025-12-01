"""
富途证券数据服务接口
"""
import pandas as pd
from datetime import datetime
from collections.abc import Callable
from typing import List

from futu import (
    OpenQuoteContext,
    KLType,
    RET_OK,
    RET_ERROR
)

from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.object import HistoryRequest, TickData, BarData
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.utility import ZoneInfo
from vnpy.trader.setting import SETTINGS
from vnpy.trader.locale import _

from .rate_limiter import get_futu_rate_limiter

# 时区设置
CHINA_TZ = ZoneInfo("Asia/Shanghai")

# 交易所映射
EXCHANGE_VT2FUTU = {
    Exchange.SMART: "US",
    Exchange.SEHK: "HK",
    Exchange.HKFE: "HK_FUTURE",
}

# K线周期映射
# 注意：1小时数据禁止直接从富途API下载，必须从1分钟数据合成
INTERVAL_VT2FUTU = {
    Interval.MINUTE: KLType.K_1M,
    # Interval.HOUR: KLType.K_60M,  # 禁止：1小时数据必须从1分钟数据合成
    Interval.DAILY: KLType.K_DAY,
    Interval.WEEKLY: KLType.K_WEEK
}


def convert_symbol_vt2futu(symbol: str, exchange: Exchange) -> str:
    """VeighNa合约名称转换为富途格式"""
    futu_exchange = EXCHANGE_VT2FUTU.get(exchange)
    if not futu_exchange:
        raise ValueError(f"不支持的交易所: {exchange}")
    return f"{futu_exchange}.{symbol}"


def generate_datetime(s: str) -> datetime:
    """生成时间戳"""
    if "." in s:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")
    else:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=CHINA_TZ)
    return dt


def escape_braces(text: str) -> str:
    """
    转义字符串中的花括号，避免loguru格式化错误
    
    Args:
        text: 需要转义的字符串
    
    Returns:
        转义后的字符串
    """
    if not isinstance(text, str):
        text = str(text)
    # 转义花括号，避免loguru将其作为格式化占位符
    return text.replace("{", "{{").replace("}", "}}")


def safe_output(output, message: str) -> None:
    """安全地调用 output 函数"""
    try:
        # 转义消息中的花括号，避免loguru格式化错误
        safe_message = escape_braces(message) if isinstance(message, str) else str(message)
        if callable(output):
            output(safe_message)
        else:
            print(safe_message)
    except (TypeError, AttributeError):
        # 如果 output 不是可调用对象，使用 print
        try:
            safe_message = escape_braces(message) if isinstance(message, str) else str(message)
            print(safe_message)
        except Exception:
            pass  # 如果连 print 都失败，静默忽略


class Datafeed(BaseDatafeed):
    """
    富途证券数据服务接口
    """

    def __init__(self) -> None:
        """构造函数"""
        super().__init__()
        self.quote_ctx: OpenQuoteContext = None
        self.host: str = SETTINGS.get("datafeed.host", "127.0.0.1")
        self.port: int = SETTINGS.get("datafeed.port", 11111)
        self.inited: bool = False

    def init(self, output: Callable = print) -> bool:
        """
        初始化数据服务连接
        """
        # 先关闭旧连接，避免连接泄露
        if self.quote_ctx:
            try:
                self.quote_ctx.close()
                safe_output(output, "已关闭旧的Datafeed连接")
            except Exception as e:
                safe_output(output, f"关闭旧Datafeed连接时出错: {str(e)}")
            finally:
                self.quote_ctx = None
                self.inited = False
        
        try:
            self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
            self.inited = True
            safe_output(output, "富途数据服务连接成功")
            return True
        except Exception as e:
            # 安全处理异常消息，避免特殊字符导致格式化错误
            error_msg = str(e)
            safe_output(output, f"富途数据服务连接失败: {error_msg}")
            safe_output(output, "提示: 请确保富途牛牛客户端已启动，并开启了OpenD服务")
            return False

    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> List[BarData]:
        """
        查询历史K线数据
        """
        if not self.inited:
            if not self.init(output):
                return []

        bars: List[BarData] = []

        # 检查是否支持该周期
        if req.interval not in INTERVAL_VT2FUTU:
            interval_value = str(req.interval.value)
            if req.interval == Interval.HOUR:
                msg = f"富途数据服务不支持直接下载 {interval_value} 级别的K线数据，请从1分钟数据合成"
            else:
                msg = f"富途数据服务不支持 {interval_value} 级别的K线数据"
            safe_output(output, msg)
            return bars

        try:
            # 转换合约代码
            futu_symbol = convert_symbol_vt2futu(req.symbol, req.exchange)
            
            # 处理主力合约历史数据查询
            # 说明：查询历史数据时，直接使用主连代码（如HK.MHImain），不转换为HK_FUTURE格式
            # 这样返回的是主连历史数据，自动包含各时段的主力合约数据，避免以下问题：
            # - 当提前切换主力合约后（如当前是11月但主力已切换到12月合约MHI2512）
            # - 如果使用当前主力合约查询历史数据，数据不能真实反映当时的成交情况
            # - 直接使用主连代码查询，富途会返回各时段真正的主力合约数据
            if req.symbol.endswith("main") and req.exchange == Exchange.HKFE:
                futu_symbol = f"HK.{req.symbol}"
                safe_output(output, f"查询历史数据：使用主连代码 {futu_symbol}（包含各时段主力合约数据）")
            
            # 转换K线周期
            ktype = INTERVAL_VT2FUTU[req.interval]
            
            # 格式化时间
            start_date = req.start.replace(tzinfo=None).strftime("%Y-%m-%d")
            end_date = req.end.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

            # 使用Rate Limiter限制API调用频率
            rate_limiter = get_futu_rate_limiter()
            rate_limiter.acquire(tokens=1, wait=True)

            # 请求历史K线数据
            ret, history_df, page_req_key = self.quote_ctx.request_history_kline(
                code=futu_symbol,
                start=start_date,
                end=end_date,
                ktype=ktype
            )

            if ret != RET_OK:
                # 安全处理错误消息，避免DataFrame包含花括号导致格式化错误
                error_msg = str(history_df) if isinstance(history_df, str) else "未知错误"
                msg = f"获取K线数据失败: {error_msg}"
                safe_output(output, msg)
                return bars

            # 处理分页数据
            while page_req_key is not None:
                # 使用Rate Limiter限制API调用频率
                rate_limiter = get_futu_rate_limiter()
                rate_limiter.acquire(tokens=1, wait=True)
                
                ret, data, page_req_key = self.quote_ctx.request_history_kline(
                    code=futu_symbol,
                    start=start_date,
                    end=end_date,
                    ktype=ktype,
                    page_req_key=page_req_key
                )
                if ret == RET_OK:
                    history_df = pd.concat([history_df, data], ignore_index=True)
                else:
                    # 安全处理错误消息，避免DataFrame包含花括号导致格式化错误
                    error_msg = str(data) if isinstance(data, str) else "分页数据获取失败"
                    msg = f"获取分页数据失败: {error_msg}"
                    safe_output(output, msg)

            if history_df.empty:
                safe_output(output, "未获取到K线数据")
                return bars

            # 处理时间字段
            history_df["time_key"] = pd.to_datetime(history_df["time_key"])
            # 调整时间（富途返回的时间是K线结束时间，需要调整为开始时间）
            if req.interval == Interval.MINUTE:
                history_df["time_key"] = history_df["time_key"] - pd.Timedelta(1, "m")
            history_df["time_key"] = history_df["time_key"].dt.strftime("%Y-%m-%d %H:%M:%S")

            # 转换为BarData
            for _, row in history_df.iterrows():
                bar = BarData(
                    symbol=req.symbol,
                    exchange=req.exchange,
                    datetime=generate_datetime(row["time_key"]),
                    interval=req.interval,
                    volume=row.get("volume", 0),
                    turnover=row.get("turnover", 0),
                    open_interest=0,
                    open_price=row["open"],
                    high_price=row["high"],
                    low_price=row["low"],
                    close_price=row["close"],
                    gateway_name="FUTU"
                )
                bars.append(bar)

            msg = f"成功获取 {len(bars)} 条K线数据"
            safe_output(output, msg)
            return bars

        except Exception as e:
            # 直接使用f-string，避免_函数可能的问题
            error_msg = str(e)
            msg = f"查询K线数据异常: {error_msg}"
            safe_output(output, msg)
            return bars

    def query_tick_history(self, req: HistoryRequest, output: Callable = print) -> List[TickData]:
        """
        查询历史Tick数据
        注意：富途API暂不支持历史Tick数据查询，此方法返回空列表
        """
        safe_output(output, _("富途数据服务暂不支持历史Tick数据查询"))
        return []

    def close(self) -> None:
        """关闭连接"""
        try:
            if self.quote_ctx:
                self.quote_ctx.close()
                self.quote_ctx = None  # Set to None to prevent double close
                self.inited = False
                safe_output(print, "Datafeed连接已关闭")
        except Exception as e:
            error_msg = str(e)
            safe_output(print, f"关闭Datafeed连接时出错: {error_msg}")

