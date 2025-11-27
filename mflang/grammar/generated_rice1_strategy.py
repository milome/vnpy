#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成的策略代码
由麦语言AST代码生成器生成
"""

from vnpy_ctastrategy import (
    CtaTemplate,
    BarData,
    ArrayManager
)

import numpy as np
from mflang import REF, BARSLAST, SUMBARS, BARPOS, HHV, LLV
from mflang.functions import BP, BPK, SPK
from indicators import IndicatorManager

class RICE1Strategy(CtaTemplate):
    """自动生成的策略类"""

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()

        # 创建 IndicatorManager 用于管理跨周期指标
        self.indicator_manager = IndicatorManager(
            vt_symbol=self.vt_symbol,
            storage_path=None,  # 使用默认路径 .vntrader/indicators/
            use_database=True  # 使用数据库加载历史数据
        )

        # 注册导入的模型到IndicatorManager
        # 警告: 模型 米仓I号日内趋势 未解析，无法注册

        # 警告: 模型 米仓I号小时趋势 未解析，无法注册

        # 警告: 模型 米仓I号多周期MACD 未解析，无法注册

        # 警告: 模型 米仓I号追踪区域 未解析，无法注册

        # 警告: 模型 米仓I号单周期MACD 未解析，无法注册

        # 警告: 模型 米仓I号变量赋值 未解析，无法注册


    def on_bar(self, bar: BarData):
        """K线数据回调"""
        self.am.update_bar(bar)

        if not self.am.inited:
            return

        # 获取跨周期引用数据
        # 获取跨周期引用 DAYTREND.SCALEBUYVOL
        scalebuyvol_value = self.indicator_manager.get_indicator_smart(
            "1d",
            "DAYTREND.SCALEBUYVOL",
            "SCALEBUYVOL"
        )
        if scalebuyvol_value is None:
            scalebuyvol_value = np.nan

        # 获取跨周期引用 DAYTREND.SCALESALEVOL
        scalesalevol_value = self.indicator_manager.get_indicator_smart(
            "1d",
            "DAYTREND.SCALESALEVOL",
            "SCALESALEVOL"
        )
        if scalesalevol_value is None:
            scalesalevol_value = np.nan

        # 获取跨周期引用 DAYTREND.SCALEBUY
        scalebuy_value = self.indicator_manager.get_indicator_smart(
            "1d",
            "DAYTREND.SCALEBUY",
            "SCALEBUY"
        )
        if scalebuy_value is None:
            scalebuy_value = np.nan

        # 获取跨周期引用 DAYTREND.SCALESALE
        scalesale_value = self.indicator_manager.get_indicator_smart(
            "1d",
            "DAYTREND.SCALESALE",
            "SCALESALE"
        )
        if scalesale_value is None:
            scalesale_value = np.nan

        # 获取跨周期引用 HOURTREND.ISSKIPDAY
        isskipday_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.ISSKIPDAY",
            "ISSKIPDAY"
        )
        if isskipday_value is None:
            isskipday_value = np.nan

        # 获取跨周期引用 HOURTREND.NUMOFNEWDAY
        numofnewday_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.NUMOFNEWDAY",
            "NUMOFNEWDAY"
        )
        if numofnewday_value is None:
            numofnewday_value = np.nan

        # 获取跨周期引用 MACDIMPORT25.MACD1
        macd1_value = self.indicator_manager.get_indicator_smart(
            "45m",
            "MACDIMPORT25.MACD1",
            "MACD1"
        )
        if macd1_value is None:
            macd1_value = np.nan

        # 获取跨周期引用 MULTIMACD.CURRENTTRACINGPHASE
        currenttracingphase_value = self.indicator_manager.get_indicator_smart(
            "1m",
            "MULTIMACD.CURRENTTRACINGPHASE",
            "CURRENTTRACINGPHASE"
        )
        if currenttracingphase_value is None:
            currenttracingphase_value = np.nan

        # 获取跨周期引用 HOURTREND.KTIME
        ktime_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.KTIME",
            "KTIME"
        )
        if ktime_value is None:
            ktime_value = np.nan

        # 获取跨周期引用 HOURTREND.KOPEN
        kopen_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.KOPEN",
            "KOPEN"
        )
        if kopen_value is None:
            kopen_value = np.nan

        # 获取跨周期引用 HOURTREND.KCLOSE
        kclose_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.KCLOSE",
            "KCLOSE"
        )
        if kclose_value is None:
            kclose_value = np.nan

        # 获取跨周期引用 HOURTREND.KHIGH
        khigh_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.KHIGH",
            "KHIGH"
        )
        if khigh_value is None:
            khigh_value = np.nan

        # 获取跨周期引用 HOURTREND.3KHIGH
        3khigh_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.3KHIGH",
            "3KHIGH"
        )
        if 3khigh_value is None:
            3khigh_value = np.nan

        # 获取跨周期引用 HOURTREND.KLOW
        klow_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.KLOW",
            "KLOW"
        )
        if klow_value is None:
            klow_value = np.nan

        # 获取跨周期引用 HOURTREND.3KLOW
        3klow_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.3KLOW",
            "3KLOW"
        )
        if 3klow_value is None:
            3klow_value = np.nan

        # 获取跨周期引用 HOURTREND.PRE3KOPEN
        pre3kopen_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.PRE3KOPEN",
            "PRE3KOPEN"
        )
        if pre3kopen_value is None:
            pre3kopen_value = np.nan

        # 获取跨周期引用 HOURTREND.120MAINTRENDLLV
        120maintrendllv_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.120MAINTRENDLLV",
            "120MAINTRENDLLV"
        )
        if 120maintrendllv_value is None:
            120maintrendllv_value = np.nan

        # 获取跨周期引用 HOURTREND.PRE12KHIGH
        pre12khigh_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.PRE12KHIGH",
            "PRE12KHIGH"
        )
        if pre12khigh_value is None:
            pre12khigh_value = np.nan

        # 获取跨周期引用 HOURTREND.120MAINTRENDHHV
        120maintrendhhv_value = self.indicator_manager.get_indicator_smart(
            "1h",
            "HOURTREND.120MAINTRENDHHV",
            "120MAINTRENDHHV"
        )
        if 120maintrendhhv_value is None:
            120maintrendhhv_value = np.nan

        # 计算变量（按依赖顺序）
        self.NUMOFDAY = None
        self.BUYVOL = scalebuyvol_value
        self.SALEVOL = scalesalevol_value
        self.DAYBUYSCALE = scalebuy_value
        self.DAYSALESCALE = scalesale_value
        self.NUMOFNEWDAY = 1
        self.NUMOFNEWHOUR = 1
        self.NUMOFPREHOUR = SUMBARS(1, 2)
        self.NUMOF2HOURSAGO = SUMBARS(1, 3)
        self.NUMOF3HOURSAGO = SUMBARS(1, 4)
        self.ISWEAKUPTRENDOFHOUROCCURED = 0
        self.NUMOFYESTERDAY = SUMBARS(1, 2)
        self.NUMOF2DAYSAGO = SUMBARS(1, 3)
        self.NUMOF3DAYSAGO = SUMBARS(1, 4)
        self.ISSKIPDAY = isskipday_value
        self.小时周期 = numofnewday_value
        self.NUMOF4HSHIFT = ((REF(numofnewday_value, 1) if 7 else 0) if 1 else REF(numofnewday_value, 1))
        self.MAINTREND1M = EMA(EMA(None, 3), 3)
        self.TR = max(max(None, abs(None)), abs(None))
        self.ATR = MA(None, 14)
        self.TOTALKDATANUM = 1
        self.DIFF1 = EMA(None, 26)
        self.DEA1 = EMA(None, 9)
        self.MACD1 = None
        self.DIFF3 = EMA(None, 78)
        self.DEA3 = EMA(None, 27)
        self.DIFF25 = EMA(None, 624)
        self.DEA25 = EMA(None, 216)
        self.MACD25 = None
        self.DIFF30 = EMA(None, 780)
        self.DEA30 = EMA(None, 270)
        self.MACD30 = macd1_value
        self.DIFF60F = EMA(None, 13)
        self.DEA60F = EMA(None, 5)
        self.MACD60F = None
        self.DIFF60 = EMA(None, 26)
        self.DEA60 = EMA(None, 9)
        self.MACD60 = None
        self.CLOSE5 = REF(None, 4)
        self.DIFF5M = EMA(None, 26)
        self.DEA5M = EMA(None, 9)
        self.DIFF5 = EMA(None, 130)
        self.DEA5 = EMA(None, 45)
        self.MACD5 = None
        self.CLOSE5H = REF(None, 299)
        self.DIFF300 = EMA(None, 5200)
        self.DEA300 = EMA(None, 1800)
        self.DIFF5H = EMA(None, 26)
        self.DEA5H = EMA(None, 9)
        self.MACD300 = None
        self.MACD3 = None
        self.MACD3MIX = (1 if None else 1)
        self.MACD35 = (1 if None else 1)
        self.ISUPTREND = (1 if None else (0 if None else 1))
        self.ISUPTRENDOVER0 = BARSLAST(None)
        self.ISUPTRENDOVER1 = BARSLAST(None)
        self.ISUPTRENDOVER = BARSLAST(None)
        self.ISDOWNTREND = (1 if None else (0 if None else 1))
        self.ISDOWNTRENDOVER0 = BARSLAST(None)
        self.ISDOWNTRENDOVER1 = BARSLAST(None)
        self.ISDOWNTRENDOVER = BARSLAST(None)
        self.ISWEAKUPTREND = 0
        self.ISWEAKDOWNTREND = 0
        self.当前分钟趋势 = None
        self.ISMACD35CROSSUP = (1 if 0 else 0)
        self.NUMOFMACD35CROSSUP = REF(None, BARSLAST(1))
        self.PRENUMOFMACD35CROSSUP = 1
        self.PRE2NUMOFMACD35CROSSUP = 1
        self.PRE3NUMOFMACD35CROSSUP = 1
        self.PRE4NUMOFMACD35CROSSUP = 1
        self.PRE5NUMOFMACD35CROSSUP = 1
        self.PRE6NUMOFMACD35CROSSUP = 1
        self.PRE7NUMOFMACD35CROSSUP = 1
        self.PRE8NUMOFMACD35CROSSUP = 1
        self.PRE9NUMOFMACD35CROSSUP = 1
        self.PRE10NUMOFMACD35CROSSUP = 1
        self.PRE11NUMOFMACD35CROSSUP = 1
        self.PRE12NUMOFMACD35CROSSUP = 1
        self.PRE13NUMOFMACD35CROSSUP = 1
        self.PRE14NUMOFMACD35CROSSUP = 1
        self.PRE15NUMOFMACD35CROSSUP = 1
        self.PRE16NUMOFMACD35CROSSUP = 1
        self.ISMACD35CROSSDOWN = (1 if 0 else 0)
        self.NUMOFMACD35CROSSDOWN = REF(None, BARSLAST(1))
        self.PRENUMOFMACD35CROSSDOWN = 1
        self.PRE2NUMOFMACD35CROSSDOWN = 1
        self.PRE3NUMOFMACD35CROSSDOWN = 1
        self.PRE4NUMOFMACD35CROSSDOWN = 1
        self.PRE5NUMOFMACD35CROSSDOWN = 1
        self.PRE6NUMOFMACD35CROSSDOWN = 1
        self.PRE7NUMOFMACD35CROSSDOWN = 1
        self.PRE8NUMOFMACD35CROSSDOWN = 1
        self.PRE9NUMOFMACD35CROSSDOWN = 1
        self.PRE10NUMOFMACD35CROSSDOWN = 1
        self.PRE11NUMOFMACD35CROSSDOWN = 1
        self.PRE12NUMOFMACD35CROSSDOWN = 1
        self.PRE13NUMOFMACD35CROSSDOWN = 1
        self.PRE14NUMOFMACD35CROSSDOWN = 1
        self.PRE15NUMOFMACD35CROSSDOWN = 1
        self.PRE16NUMOFMACD35CROSSDOWN = 1
        self.NUMOFLASTYELLOWKOPEN = REF(None, BARSLAST(None))
        self.NUMOFLASTBLUEKOPEN = REF(None, BARSLAST(None))
        self.NUMOFLASTORANGEKOPEN = REF(None, BARSLAST(4))
        self.NUMOFLASTPURPLEKOPEN = REF(None, BARSLAST(4))
        self.NUMOFDAYLASTYELLOWKOPEN = BARSLAST(4)
        self.NUMOFDAYLASTBLUEKOPEN = BARSLAST(4)
        self.NUMOFDAYLASTORANGEKOPEN = BARSLAST(4)
        self.NUMOFDAYLASTPURPLEKOPEN = BARSLAST(4)
        self.NUMOFFIRSTORANGEKOPEN = REF(None, BARSLAST(1))
        self.NUMOFFIRSTPURPLEKOPEN = REF(None, BARSLAST(1))
        self.NUMOFPRELOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE2LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE3LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE4LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE5LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE6LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE7LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE8LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE9LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE10LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE11LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE12LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE13LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE14LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE15LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE16LOWESTTREND = REF(REF(None, LLVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPREHIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE2HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE3HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE4HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE5HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE6HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE7HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE8HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE9HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE10HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE11HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE12HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE13HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE14HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE15HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFPRE16HIGHESTTREND = REF(REF(None, HHVBARS(None, 1)), (None if 0 else None))
        self.NUMOFLASTYELLOWOPENINLASTMACD5CROSSUP = REF(None, (None if 0 else None))
        self.NUMOFLASTBLUEKOPENINLASTMACD5CROSSDOWN = REF(None, (None if 0 else None))
        self.CURRENTTRACINGPHASE = currenttracingphase_value
        self.ISACTIVEHOURS = 0
        self.MAINTREND1H = EMA(EMA(None, 75), 75)
        self.PB6 = 3
        self.MID = MA(None, 300)
        self.TMP2 = STD(None, 300)
        self.TOP = None
        self.BOTTOM = None
        self.OPENMACD35CROSSUP = (None if 0 else REF(None, None))
        self.OPENMACD35CROSSDOWN = (None if 0 else REF(None, None))
        self.CURRENTHIGHESTTREND35 = (HHV(None, 1) if 0 else (HHV(None, 1) if 0 else (REF(HHV(None, None), None) if 0 else (REF(HHV(None, 1), 1) if 0 else 0))))
        self.PREHIGHESTTREND35 = (REF(HHV(None, 1), None) if 0 else (REF(HHV(None, 1), None) if 0 else (REF(HHV(None, 1), None) if 0 else (REF(HHV(None, 1), None) if 0 else 0))))
        self.PRE2HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE3HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE4HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE5HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE6HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE7HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE8HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE9HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE10HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE11HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE12HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE13HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE14HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE15HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE16HIGHESTTREND35 = (REF(None, None) if 0 else 1)
        self.CURRENTLOWESTTREND35 = (LLV(None, 1) if 0 else (LLV(None, 1) if 0 else (REF(LLV(None, 1), None) if 0 else (REF(LLV(None, 1), 1) if 0 else 0))))
        self.PRELOWESTTREND35 = (REF(LLV(None, 1), None) if 0 else (REF(LLV(None, 1), None) if 0 else (REF(LLV(None, 1), None) if 0 else (REF(LLV(None, 1), None) if 0 else 0))))
        self.PRE2LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE3LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE4LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE5LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE6LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE7LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE8LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE9LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE10LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE11LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE12LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE13LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE14LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE15LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.PRE16LOWESTTREND35 = (REF(None, None) if 0 else 1)
        self.ISHIGHERHIGHESTTREND35 = (1 if None else (1 if None else (1 if None else (1 if None else (1 if None else (0 if None else (1 if None else 0)))))))
        self.ISHIGHERLOWESTTREND35 = (1 if None else (1 if None else (1 if None else (1 if None else (0 if None else (1 if None else 0))))))
        self.ISLOWERHIGHESTTREND35 = (1 if None else (0 if None else (0 if None else (1 if None else (0 if None else (1 if None else (1 if None else (0 if None else (0 if None else 0)))))))))
        self.ISLOWERLOWESTTREND35 = (1 if None else (1 if None else (1 if None else (1 if None else (1 if None else (1 if None else 0))))))
        self.LOWERCOUNTER = COUNT(REF(None, 1), None)
        self.COUNTERFLAGLOWERLOWTREND = (1 if None else 0)
        self.NUMOFLOWERLOWTREND = (COUNT(1, BARSLAST(None)) if None else 0)
        self.ACTUALNUMOFLOWERLOWTREND = (16 if min(None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None) else (15 if min(None, None, None, None, None, None, None, None, None, None, None, None, None, None, None) else (14 if min(None, None, None, None, None, None, None, None, None, None, None, None, None, None) else (13 if min(None, None, None, None, None, None, None, None, None, None, None, None, None) else (12 if min(None, None, None, None, None, None, None, None, None, None, None, None) else (11 if min(None, None, None, None, None, None, None, None, None, None, None) else (10 if min(None, None, None, None, None, None, None, None, None, None) else (9 if min(None, None, None, None, None, None, None, None, None) else (8 if min(None, None, None, None, None, None, None, None) else (7 if min(None, None, None, None, None, None, None) else (6 if min(None, None, None, None, None, None) else (5 if min(None, None, None, None, None) else (4 if min(None, None, None, None) else (3 if min(None, None, None) else (2 if min(None, None) else (1 if None else 0))))))))))))))))
        self.HIGHERCOUNTER = COUNT(REF(None, 1), None)
        self.COUNTERFLAGHIGHERERHIGHTREND = (1 if None else 0)
        self.NUMOFHIGHERHIGHTREND = (COUNT(1, BARSLAST(None)) if None else 0)
        self.ACTUALNUMOFHIGHERHIGHTREND = (16 if max(None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None) else (15 if max(None, None, None, None, None, None, None, None, None, None, None, None, None, None, None) else (14 if max(None, None, None, None, None, None, None, None, None, None, None, None, None, None) else (13 if max(None, None, None, None, None, None, None, None, None, None, None, None, None) else (12 if max(None, None, None, None, None, None, None, None, None, None, None, None) else (11 if max(None, None, None, None, None, None, None, None, None, None, None) else (10 if max(None, None, None, None, None, None, None, None, None, None) else (9 if max(None, None, None, None, None, None, None, None, None) else (8 if max(None, None, None, None, None, None, None, None) else (7 if max(None, None, None, None, None, None, None) else (6 if max(None, None, None, None, None, None) else (5 if max(None, None, None, None, None) else (4 if max(None, None, None, None) else (3 if max(None, None, None) else (2 if max(None, None) else (1 if None else 0))))))))))))))))
        self.CURRENTHIGHESTPRICEINDAY = HHV(None, None)
        self.CURRENTLOWESTPRICEINDAY = LLV(None, None)
        self.PREHIGHESTPRICEINDAY = REF(None, None)
        self.PRELOWESTPRICEINDAY = REF(None, None)
        self.PREPREHIGHESTPRICEINDAY = REF(None, None)
        self.PREPRELOWESTPRICEINDAY = REF(None, None)
        self.PREPREPREHIGHESTPRICEINDAY = REF(None, None)
        self.PREPREPRELOWESTPRICEINDAY = REF(None, None)
        self.NUMOFCURRENTHIGHESTPRICEINDAY = HHVBARS(None, None)
        self.NUMOFCURRENTLOWESTPRICEINDAY = LLVBARS(None, None)
        self.TIMEOFHOUR = ktime_value
        self.OPENOFHOUR = (kopen_value if REF(numofnewday_value, 1) else REF(kopen_value, 1))
        self.CLOSEOFHOUR = (kclose_value if REF(numofnewday_value, 1) else REF(kclose_value, 1))
        self.HOFHOUR = (khigh_value if REF(numofnewday_value, 1) else REF(khigh_value, 1))
        self.HOF3KHIGH = (3khigh_value if REF(numofnewday_value, 1) else REF(3khigh_value, 1))
        self.LOFHOUR = (klow_value if REF(numofnewday_value, 1) else REF(klow_value, 1))
        self.LOF3KLOW = (3klow_value if REF(numofnewday_value, 1) else REF(3klow_value, 1))
        self.NUMSHIFTOF4HFORKDRAW = (3 if 7 else 3)
        self.NUMSHIFTOF4HFORCOUNT = BARSLAST(None)
        self.LAST4HKOPEN = REF(pre3kopen_value, 1)
        self.LAST4HKCLOSE = REF(None, SUMBARS(0, 2))
        self.最近的黄线位移 = 1
        self.前一个4K的位移 = SUMBARS(0, 2)
        self.蓝阳阴线最大值 = max(REF(pre3kopen_value, 2), REF(None, 1))
        self.前一个5分钟的收盘价 = REF(None, 1)
        self.前一个5分钟的收盘价0 = REF(None, 1)
        self.前一个5分钟的收盘价1 = REF(None, BARSLAST(4))
        self.ISINRIGHTTREND0 = None
        self.ISINRIGHTTREND1 = None
        self.ISINRIGHTTREND = None
        self.ISINLEFTTREND0 = None
        self.ISINLEFTTREND1 = None
        self.ISINLEFTTREND = None
        self.ISINLEFTRIGHTTREND = None
        self.IS4HTRENDYELLOW = None
        self.IS4HTRENDBACKYELLOW = None
        self.IS4HTRENDBLUE = REF(120maintrendllv_value, 1)
        self.IS4HTRENDLIGHTYELLOW = None
        self.IS4HTRENDDLIGHTBLUE = None
        self.IS4HTRENDDLIGHTBLUER = None
        self.IS4HTRENDCYANRED = None
        self.IS4HTRENDCYAN = None
        self.IS4HTRENDUCYAN = None
        self.IS4HTRENDULIGHTBLUE = None
        self.IS4HTRENDDEEPORANGE = None
        self.IS4HTRENDDOWNDEEPOR = REF(pre12khigh_value, 1)
        self.IS4HTRENDDOWNORANGE = REF(120maintrendhhv_value, 1)
        self.IS4HTRENDDOWNY = None
        self.IS4HTRENDDOWNLY = None
        self.IS4HTRENDPURPLED = REF(120maintrendllv_value, 1)
        self.IS4HTRENDPRED = None
        self.IS4HTRENDPREDUP = None
        self.IS4HTRENDPLB = None
        self.4HRED1 = None
        self.4HRED2 = None
        self.4HRED3 = None
        self.4HRED4 = None
        self.4HRED5 = None
        self.最近青红阴线开盘价 = REF(pre3kopen_value, 2)
        self.是否最近青红阴线 = BARSLAST(None)
        self.4HRED6 = None
        self.4HRED7 = None
        self.4HRED8 = None
        self.4HRED9 = None
        self.4HRED10 = None
        self.4HRED11 = None
        self.IS4HTRENDRED = None
        self.ISDOWN4KNOTLAST4K = REF(None, SUMBARS(0, 2))
        self.4HDOWNRED1 = None
        self.4HDOWNRED2 = None
        self.4HDOWNRED3 = None
        self.4HDOWNRED4 = None
        self.IS4HTRENDDOWNRED = None
        self.IS4HTRENDORANGE = None
        self.IS4HTRENDBACKORANGE = None
        self.IS4HTRENDLIGHTORANGE = None
        self.ISDOWNNREDABSENT = BARSLAST(None)
        self.ISUP16NOTLAST4K = SUMBARS(0, 2)
        self.4HLIGHTGREEN1 = None
        self.4HLIGHTGREEN2 = None
        self.4HLIGHTGREEN3 = None
        self.IS4HTRENDUPGREEN = None
        self.IS4HTRENDDOWNGREEN = None
        self.0.00000000000000000000000000 = None
        self.模型分隔符在这里分割两个模型 = 0.0

        # IF-THEN-BEGIN-END块
        if 1:
        if 1:
        if 0:
        if 1:
        if BARSLAST(None):
        if 1:
        if 1:
        if 0:
        if 1:
        if BARSLAST(None):

        # 交易指令
        BP()