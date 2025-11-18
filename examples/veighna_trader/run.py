from vnpy_futu import FutuGateway
from vnpy.event import EventEngine

from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy.trader.setting import SETTINGS

from vnpy_ctp import CtpGateway
# from vnpy_ctptest import CtptestGateway
# from vnpy_mini import MiniGateway
# from vnpy_femas import FemasGateway
# from vnpy_sopt import SoptGateway
# from vnpy_uft import UftGateway
# from vnpy_esunny import EsunnyGateway
# from vnpy_xtp import XtpGateway
# from vnpy_tora import ToraStockGateway, ToraOptionGateway
# from vnpy_ib import IbGateway
# from vnpy_tap import TapGateway
# from vnpy_da import DaGateway
# from vnpy_rohon import RohonGateway
# from vnpy_tts import TtsGateway

# from vnpy_paperaccount import PaperAccountApp
from vnpy_ctastrategy import CtaStrategyApp
from vnpy_ctabacktester import CtaBacktesterApp
# from vnpy_spreadtrading import SpreadTradingApp
# from vnpy_algotrading import AlgoTradingApp
# from vnpy_optionmaster import OptionMasterApp
# from vnpy_portfoliostrategy import PortfolioStrategyApp
# from vnpy_scripttrader import ScriptTraderApp
from vnpy_chartwizard import ChartWizardApp
# from vnpy_rpcservice import RpcServiceApp
# from vnpy_excelrtd import ExcelRtdApp
from vnpy_datamanager import DataManagerApp
from vnpy_datarecorder import DataRecorderApp
# from vnpy_riskmanager import RiskManagerApp
from vnpy_webtrader import WebTraderApp
# from vnpy_portfoliomanager import PortfolioManagerApp


def main():
    """"""
    # 配置数据服务（datafeed）
    # 如果全局配置文件中没有设置，可以在这里设置
    # 常见的数据服务包括: futu, rqdata, xt, tushare, wind, ifind, tqsdk, udata 等
    if not SETTINGS.get("datafeed.name"):
        # 示例1：使用富途（Futu）数据服务（需要富途牛牛客户端运行并开启OpenD服务）
        SETTINGS["datafeed.name"] = "futu"
        SETTINGS["datafeed.host"] = "127.0.0.1"  # 富途OpenD服务地址，默认127.0.0.1
        SETTINGS["datafeed.port"] = 11111        # 富途OpenD服务端口，默认11111
        
        # 示例2：使用 tushare 数据服务（需要安装 vnpy_tushare）
        # SETTINGS["datafeed.name"] = "tushare"
        # SETTINGS["datafeed.username"] = "your_username"  # 数据服务用户名
        # SETTINGS["datafeed.password"] = "your_token"      # 数据服务密码或token
        
        # 示例3：使用其他数据服务，请取消注释并填写相应的配置
        # SETTINGS["datafeed.name"] = "rqdata"  # 米筐RQData
        # SETTINGS["datafeed.username"] = "license"  # RQData的用户名统一为"license"
        # SETTINGS["datafeed.password"] = "your_license"  # RQData的license
        
        # SETTINGS["datafeed.name"] = "xt"  # 迅投研
        # SETTINGS["datafeed.username"] = "your_username"
        # SETTINGS["datafeed.password"] = "your_password"
        
        pass  # 如果不想在这里配置，可以在全局配置文件中配置
    
    qapp = create_qapp()

    event_engine = EventEngine()

    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(FutuGateway)

    #main_engine.add_gateway(CtpGateway)
    # main_engine.add_gateway(CtptestGateway)
    # main_engine.add_gateway(MiniGateway)
    # main_engine.add_gateway(FemasGateway)
    # main_engine.add_gateway(SoptGateway)
    # main_engine.add_gateway(UftGateway)
    # main_engine.add_gateway(EsunnyGateway)
    # main_engine.add_gateway(XtpGateway)
    # main_engine.add_gateway(ToraStockGateway)
    # main_engine.add_gateway(ToraOptionGateway)
    # main_engine.add_gateway(IbGateway)
    # main_engine.add_gateway(TapGateway)
    # main_engine.add_gateway(DaGateway)
    # main_engine.add_gateway(RohonGateway)
    # main_engine.add_gateway(TtsGateway)

    # main_engine.add_app(PaperAccountApp)
    main_engine.add_app(CtaStrategyApp)
    main_engine.add_app(CtaBacktesterApp)
    # main_engine.add_app(SpreadTradingApp)
    # main_engine.add_app(AlgoTradingApp)
    # main_engine.add_app(OptionMasterApp)
    # main_engine.add_app(PortfolioStrategyApp)
    # main_engine.add_app(ScriptTraderApp)
    # main_engine.add_app(ChartWizardApp)
    # main_engine.add_app(RpcServiceApp)
    # main_engine.add_app(ExcelRtdApp)
    main_engine.add_app(DataManagerApp)
    # main_engine.add_app(DataRecorderApp)
    # main_engine.add_app(RiskManagerApp)
    # main_engine.add_app(WebTraderApp)
    # main_engine.add_app(PortfolioManagerApp)

    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()

    qapp.exec()


if __name__ == "__main__":
    main()
