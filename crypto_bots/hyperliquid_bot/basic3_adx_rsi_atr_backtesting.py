import pandas as pd
import pandas_ta_classic as ta
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import numpy as np
# from backtesting.test import GOOG

# ==========================================
# 1. CS 实验台：造数据 (Mock Data Generation)
# ==========================================
# def create_mock_data(n=1000): # 增加数据量到 1000 条
#     # 使用 linspace 生成 x 轴
#     # 这里的 20 * pi 意味着我们会生成 10 个完整的正弦波周期 (2pi 一个周期)
#     # 频率变高了，RSI 反应会更剧烈
#     x = np.linspace(0, 20 * np.pi, n) 
    
#     # 1. 基础震荡: 幅度放大到 15 (从 85 震荡到 115)
#     cycle = 15 * np.sin(x)
    
#     # 2. 噪音: 增加一点随机性，让它不那么像完美的数学公式
#     noise = np.random.normal(0, 3, n)
    
#     # 3. 核心修复: 移除向上的 Trend，改为水平震荡 (Flat Market)
#     base_price = 100
#     close = base_price + cycle + noise
    
#     df = pd.DataFrame({
#         'Open': close + np.random.normal(0, 1, n),
#         'Close': close,
#         'High': close + abs(np.random.normal(0, 2, n)), # High 必须比 Close 高
#         'Low': close - abs(np.random.normal(0, 2, n)),  # Low 必须比 Close 低
#         'Volume': np.random.randint(100, 1000, n)
#     })
#     df.index = pd.date_range("2023-01-01", periods=n, freq="H")
#     return df

# # 生成数据
# df = create_mock_data()

# ==========================================
# 1. 构造“剧本”数据 (Scripted Data)
# ==========================================
# 我们需要至少 50-60 行数据，因为 ADX/RSI 需要前 14 天作为计算预热
data = {
    'Open': [], 'High': [], 'Low': [], 'Close': [], 'Volume': []
}

# 阶段 A: 横盘震荡 (40天) -> 让 ADX 降下来，RSI 回到 50
for i in range(40):
    price = 100 + (i % 3) - 1  # 在 99, 100, 101 之间跳动
    data['Open'].append(price)
    data['High'].append(price + 1)
    data['Low'].append(price - 1)
    data['Close'].append(price)
    data['Volume'].append(1000)

# 阶段 B: 急跌 (5天) -> 触发 RSI < 30，同时 ADX 还没来得及飙升
drops = [98, 96, 94, 91, 88] 
for p in drops:
    data['Open'].append(p + 1)
    data['High'].append(p + 1)
    data['Low'].append(p - 1)
    data['Close'].append(p)     # 收盘价持续下跌
    data['Volume'].append(2000) # 放量下跌

# 阶段 C: 反弹 (15天) -> 获利了结
rebounds = [90, 92, 95, 97, 100, 102, 103, 102, 101, 100, 100, 100, 100, 100, 100]
for p in rebounds:
    data['Open'].append(p - 1)
    data['High'].append(p + 1)
    data['Low'].append(p - 1)
    data['Close'].append(p)
    data['Volume'].append(1500)

df = pd.DataFrame(data)
df.index = pd.date_range("2023-01-01", periods=len(df), freq="D")

# print(df)

# ==========================================
# 2. Feature Engineering (特征工程)
# ==========================================
# 在把数据喂给策略前，先用 Pandas-TA 算出所有指标
# 这种 "Pre-calculation" 模式比在策略里算更高效

# A. 计算 ADX (用来识别震荡)
# adx() 返回三列: ADX, DMP, DMN。我们只需要 ADX 列
df.ta.adx(length=14, append=True)


# B. 计算 RSI (用来识别入场点)
df.ta.rsi(length=14, append=True)

# # C. 计算 ATR (用来算动态止损)
df.ta.atr(length=14, append=True)

# 为了方便 backtesting 调用，我们把列名重命名得简单点
df.rename(columns={'ADX_14': 'ADX', 'RSI_14': 'RSI', 'ATRr_14': 'ATR'}, inplace=True)
# 注意：ADX 计算前14行会是 NaN，我们需要填充或去除，否则 backtesting 会报错
df.dropna(inplace=True)


print(type(df))
print(df)


# ==========================================
# 3. 策略逻辑 (The Algorithm)
# ==========================================
class RangeSniper(Strategy):
    adx_threshold = 25
    rsi_buy = 30 #超卖阈值
    rsi_sell = 70 #超买阈值
    atr_multiplier = 2.0 #止损宽度

    def init(self):
        '''
        declare class fields/properties 声明我们要用到的指标列
        self.I 只是为了让指标画在图表上
        '''
        self.adx = self.I(lambda x: x, self.data.ADX, name='ADX')
        self.rsi = self.I(lambda x: x, self.data.RSI, name='RSI')
        self.atr = self.I(lambda x: x, self.data.ATR, name='ATR')

    def next(self):
        '''获取当前/cur指标的数值'''
        current_adx = self.adx[-1]
        current_rsi = self.rsi[-1]
        current_atr = self.atr[-1]
        price = self.data.Close[-1]

        '''
        Exit logic
        '''
        if self.position:
            if current_rsi>self.rsi_sell:
                self.position.close()
            # 场景 B: 止损 (Stop Loss)
            # 在 backtesting.py 里，我们在买入时设置 sl 参数会自动执行
            # 所以这里不需要手动写止损逻辑，除非你想做移动止损 (Trailing Stop)
        else:
            # 核心逻辑门 (Logic Gates)：
            # 1. 必须是震荡市 (ADX < 25)
            # 2. 必须是超卖 (RSI < 30)
            if current_adx<self.adx_threshold and current_rsi<self.rsi_buy:
                print("TESTT")
                # 计算动态止损价格
                # Stop Loss = 当前价格 - (2 * ATR)
                # 波动大，止损远；波动小，止损近。
                sl_price = price - (self.atr_multiplier * current_atr)
                self.buy(sl=sl_price)

            
bt = Backtest(df, RangeSniper, cash=10000, commission=.002)
stats = bt.run()

print("\n=== 回测结果 ===")
print(stats)



