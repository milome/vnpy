#!/usr/bin/env python3
"""
富途期货交易权限测试脚本
用于诊断和解决期货交易权限问题
"""

from futu import OpenQuoteContext, OpenFutureTradeContext, TrdEnv
from vnpy.trader.setting import SETTINGS

def test_futu_futures_permission():
    """测试富途期货交易权限"""
    
    # 配置参数
    host = SETTINGS.get("futu.host", "127.0.0.1")
    port = SETTINGS.get("futu.port", 11111)
    password = SETTINGS.get("futu.password", "")
    env = TrdEnv.SIMULATE  # 或 TrdEnv.REAL
    
    print("=" * 60)
    print("富途期货交易权限测试")
    print("=" * 60)
    
    # 1. 测试行情连接
    print("\n1. 测试行情连接...")
    try:
        quote_ctx = OpenQuoteContext(host=host, port=port)
        print("✅ 行情连接成功")
        
        # 查询期货合约
        ret, data = quote_ctx.get_stock_basicinfo("HK", "FUTURE")
        if ret == 0:
            mhi_contracts = data[data['code'].str.contains('MHI', na=False)]
            print(f"✅ 找到MHI期货合约: {len(mhi_contracts)}个")
            for _, row in mhi_contracts.head(5).iterrows():
                print(f"   - {row['code']}: {row['name']}")
        else:
            print(f"❌ 查询期货合约失败: {data}")
            
        quote_ctx.close()
        
    except Exception as e:
        print(f"❌ 行情连接失败: {str(e)}")
        return False
    
    # 2. 测试期货交易连接
    print("\n2. 测试期货交易连接...")
    try:
        trade_ctx = OpenFutureTradeContext(host=host, port=port)
        print("✅ 期货交易连接成功")
        
        # 解锁交易
        if password:
            ret, data = trade_ctx.unlock_trade(password)
            if ret == 0:
                print("✅ 交易解锁成功")
            else:
                print(f"❌ 交易解锁失败: {data}")
                return False
        else:
            print("⚠️  未配置交易密码，跳过解锁")
        
        # 查询账户信息
        ret, account_data = trade_ctx.accinfo_query(trd_env=env)
        if ret == 0:
            print("✅ 账户信息查询成功:")
            for _, row in account_data.iterrows():
                print(f"   账户ID: {row.get('acc_id', 'N/A')}")
                print(f"   账户类型: {row.get('trd_market', 'N/A')}")
                print(f"   可用资金: {row.get('avl_withdrawal_cash', 'N/A')}")
        else:
            print(f"❌ 账户信息查询失败: {account_data}")
            
        # 查询持仓
        ret, position_data = trade_ctx.position_list_query(trd_env=env)
        if ret == 0:
            print(f"✅ 持仓查询成功: {len(position_data)}个持仓")
            mhi_positions = position_data[position_data['code'].str.contains('MHI', na=False)]
            if not mhi_positions.empty:
                print("   MHI持仓:")
                for _, row in mhi_positions.iterrows():
                    print(f"   - {row['code']}: {row['qty']}手")
        else:
            print(f"❌ 持仓查询失败: {position_data}")
            
        trade_ctx.close()
        
    except Exception as e:
        print(f"❌ 期货交易连接失败: {str(e)}")
        return False
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    return True

def check_vnpy_settings():
    """检查VNPy配置"""
    print("\n3. 检查VNPy配置...")
    
    required_settings = [
        "futu.host",
        "futu.port", 
        "futu.password",
        "futu.market"
    ]
    
    for setting in required_settings:
        value = SETTINGS.get(setting, "未配置")
        print(f"   {setting}: {value}")
    
    # vt_setting.json 配置已移除

if __name__ == "__main__":
    check_vnpy_settings()
    test_futu_futures_permission()
