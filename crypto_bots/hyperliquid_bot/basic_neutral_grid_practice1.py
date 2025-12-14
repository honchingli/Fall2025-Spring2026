'''
https://chatgpt.com/c/693ee85a-1a2c-8333-b032-8d974a90786d


'''

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

lower, upper, step = 40000, 45000, 100
levels = build_levels(lower, upper, step)
print(levels)

p0 = float(df.iloc[0]["Close"])
print(f"df.iloc[0]: {df.iloc[0]}, f.iloc[0]['Close']: {p0}")


def init_grid_orders(levels, p0, N=None):
    """
    返回两个列表：
      sell_levels: 价格 > p0 的网格（挂 sell limit）
      buy_levels:  价格 < p0 的网格（挂 buy limit）
    N=None 表示全铺满；N=5 表示每边只取5个（推荐起步）
    """
    sell_levels = [lv for lv in levels if lv > p0]
    buy_levels = [lv for lv in levels if lv < p0]

    if N is not None:
        sell_levels = sell_levels[:N] # 离p0最近的上方N个
        buy_levels = buy_levels[-N:] # 离p0最近的下方N个
    return sell_levels, buy_levels

sell_levels, buy_levels = init_grid_orders(levels, p0, 5)
print(f"sell_levels: {sell_levels}, buy_levels: {buy_levels}")


'''被fill_sequence_close_based替代'''
def triggered_in_candle(row, sell_levels, buy_levels):
    """
    输入一根K线 row（有High/Low）
    返回：这根K线里哪些 sell/buy 价位“被触达”
    """
    high = float(row["High"])
    low  = float(row["Low"])

    trig_sells = [lv for lv in sell_levels if high>=lv]
    trig_buys = [lv for lv in buy_levels if low<=lv]

    return trig_sells, trig_buys

# trig_sells, trig_buys = triggered_in_candle(df.iloc[0], 
#                                             sell_levels, buy_levels)
# print(f"trig_sells: {trig_sells}, trig_buys: {trig_buys}")

# 看前20根K线里 触发情况
# for t, row in df.head(5).iterrows():
#     print(f"t: {t}, row: {row}")
#     s, b = triggered_in_candle(row, sell_levels, buy_levels)
#     print(f"triggered sells: {s}, triggered buys:{b}")

def fill_sequence_close_based(row, sell_levels, buy_levels):
    """
    用 Open->Close 方向猜测同K内顺序：
      - 若 Close >= Open：先处理 buys（先下探），再处理 sells（再上冲）
      - 若 Close <  Open：先处理 sells（先上冲），再处理 buys（再下探）
    返回一个 list[("buy"/"sell", price)]，按执行顺序排列
    """
    o = float(row["Open"])
    c = float(row["Close"])
    h = float(row["High"])
    l = float(row["Low"])

    trig_sells = sorted([lv for lv in sell_levels if h>=lv]) # 从低到高
    trig_buys = sorted([lv for lv in buy_levels if l<=lv], reverse=True)  # 从高到低（更贴近“先吃近的格子”）

    events = []

    if c >= o:
        # 先下后上：先买后卖
        events += [("buy", p) for p in trig_buys]
        events += [("sell", p) for p in trig_sells]
    else:
        # 先上后下：先卖后买
        events += [("sell", p) for p in trig_sells]
        events += [("buy", p) for p in trig_buys]
    return events

# events = fill_sequence_close_based(df.iloc[0], sell_levels, buy_levels)
# print(events)

# for t, row in df.head(5).iterrows():
#     events = fill_sequence_close_based(row, sell_levels, buy_levels)
#     if events:
#         print(t, events, "O/C:", row["Open"], row["Close"], "H/L:", row["High"], row["Low"])







