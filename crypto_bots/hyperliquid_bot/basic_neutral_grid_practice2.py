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
        pending[lv] = Order("sell", lv, size)
    for lv in buys:
        pending[lv] = Order("buy", lv, size)
    return pending

'''
一根K线里 哪些单会被触发
只检查 开始时就存在的挂单limit order
不在pending里的 就不用担心，应该是不在N范围内

本K线新增的补单，不允许在同一根K线里再成交
这样避免出现：一根 K 线里补单又触发、无限循环（真实成交顺序也很难从 OHLC 推断）。
output: 这根K线触发的limit orders/events

个人想法
本K线新增的补单，不允许在同一根K线里再成交
虽然跟现实有一些偏差，但如果 不添加上面的限制的话，那么就会无限循环触发
并且现实"同一根K线" 触发2个limit order的概率还是挺低的，
除非要不是 有诱因(新闻)或者是什么别的signal
要不就是 每个格子的间距没调整好，导致太近，钱全给手续费了

pending_snapshot: List[Order] (本K线开始时的limit order快照)
'''
def events_in_candler_close_based(row, pending_snapshot):
    o = float(row["Open"])
    c = float(row["Close"])
    h = float(row["High"])
    l = float(row["Low"])
    # print(f"row: {row}, pending_snapshot: {pending_snapshot}")
    trig_sells = [od for od in pending_snapshot 
                  if od.side=="sell" and h>=od.price]
    trig_buys = [od for od in pending_snapshot 
                  if od.side=="buy" and l<=od.price]
    # 同K内多个格子：卖从低到高，买从高到低（更贴近“先吃近的格子”）
    # 这一步很关键，直接影响我们下面一个function补单的逻辑正确与否
    trig_sells.sort(key=lambda x: x.price)
    trig_buys.sort(key=lambda x: x.price, reverse=True)
    if c >= o:
        # 先下后上：先买后卖
        return trig_buys + trig_sells
    else:
        # 先上后下：先卖后买
        return trig_sells + trig_buys


'''
成交后补单（相邻格 补 反向单）
buy 成交（你在更低价买到）→ 下一步在更高一格挂 sell
sell 成交（你在更高价卖到）→ 下一步在更低一格挂 buy
filled 成交后，按相邻格补反向单

idx_map {price: index} of the levels
'''
def replenish_after_fill(filled: Order, levels, idx_map, pending, size=1.0):
    i = idx_map.get(filled.price)
    if i is None:
        return
    
    if filled.side == "buy":
        # buy 成交 -> 上一格(更高)挂 sell
        j = i+1
        if j<len(levels):
            p = levels[j]
            pending.setdefault(p, Order("sell", p, size))
    else:
        # sell 成交 -> 下一格(更低)挂 buy
        j = i-1
        if j>=0:
            p = levels[j]
            pending.setdefault(p, Order("buy", p, size))


'''
打印
'''
def run_grid_debug(df, lower, upper, step, N=5, size=1.0, max_rows=50):
    levels = build_levels(lower, upper, step)
    idx_map = {p: i for i, p in enumerate(levels)}

    p0 = float(df.iloc[0]["Close"])
    pending = init_pending_orders(levels, p0, N=N, size=size)
    # print(f"pending: {pending}")

    print(f"p0 = {p0}")
    print("initial pending:", sorted((p, o.side) for p, o in pending.items()))

    for t, row in df.head(1).iterrows():
        print(f"t: {t}, row: {row}")
        # 快照：只允许“本K线开始就存在”的单触发
        snapshot = list(pending.values())
        # print(f"snapshot: {snapshot}")
        events = events_in_candler_close_based(row, snapshot)
        print(f"events: {events}")
        if not events:
            continue
        print(f"\n[{t}] O={row['Open']:.2f} H={row['High']:.2f} L={row['Low']:.2f} C={row['Close']:.2f}")

    # for od in events:





run_grid_debug(df, 40000, 45000, 100)






