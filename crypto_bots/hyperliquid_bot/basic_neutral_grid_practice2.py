'''
https://chatgpt.com/c/693ee85a-1a2c-8333-b032-8d974a90786d


'''

from dataclasses import dataclass
import yfinance as yf
import pandas as pd

def load_ohlcv(symbol: str, start = None, 
               end = None, interval="1h") -> pd.DataFrame:
    """
    返回：index=DatetimeIndex, columns = Open High Low Close Volume
    """
    df = yf.download(
        symbol,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=False,
        progress=False
    )

    # yfinance 有时会给多层列（MultiIndex），先拍平
    if isinstance(df.columns, pd.MultiIndex):
        # 只取第一层常见字段
        df.columns = [c[0] for c in df.columns]

    # 只保留OHLCV，统一列名
    keep = ["Open", "High", "Low", "Close", "Volume"]
    df = df[keep].copy()

    # 清理缺失
    df = df.dropna()

    # 确保数值类型
    df[keep] = df[keep].astype(float)

    # index 只保留 DatetimeIndex
    df.index = pd.to_datetime(df.index)

    return df

# 示例：BTC-USD（yfinance是现货指数，不是永续；但用来做“价格型回测”OK）
df = load_ohlcv("BTC-USD", start="2024-01-01", end="2024-06-01" ,interval="1h")
# print(df.head())
# print(df.tail())

def build_levels(lower: float, upper: float, step: float):
    """
    生成对齐 step 的网格价位：[lower, lower+step, ..., <= upper]
    注意：upper 不一定包含（如果不对齐step）
    eg.
    lower = 2800, upper = 3400, step = 200
    3400 - 2800 = 600
    600 // 200 = 3
    2800 to 3000 (1), 3000 to 3200 (2), 3200 to 3400 (3)
    + 1, 把起点放进去, 走3次间隔, 得到4个点 (起点，+3个间隔终点)
    when n = 4, range(n) = 0, 1, 2, 3
    """
    n = int((upper-lower) // step) + 1
    return [lower + i * step for i in range(n)]

'''
定义 Order + pending_orders（核心）
我们用 dict 来保证“同一个价格格子最多一张单”（同格不重复）：
key = price（比如 42500）
value = Order(side, price, size)
'''
@dataclass
class Order:
    side: str # "buy" or "sell"
    price: float
    size: float

'''
初始化挂单（每边 N 张：上卖下买）
    p0 上方最近 N 个：sell
    p0 下方最近 N 个：buy
    返回 dict[price] = Order(...)
'''
def init_pending_orders(levels, p0, N=5, size=1.0):
    pending = {}
    sells = [lv for lv in levels if lv>p0][:N]
    buys = [lv for lv in levels if lv<p0][-N:]
    
    for lv in sells:
        pending[lv] = Order("Sell", lv, size)
    for lv in buys:
        pending[lv] = Order("Buy", lv, size)
    return pending



