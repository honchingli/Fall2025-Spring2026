import pandas as pd
from backtesting import Backtest, Strategy

'''
json/dict
这边是在写 dict, 之后变成 pandas dataframe, pass in Backtest class里(黑盒), 
变成这个我们Strategy的subclass里的 self.data

backtesting dependency对我们pass in 的 pandas dataframe是有要求的
如下: 
data is a pd.DataFrame with columns: Open, High, Low, Close, and (optionally) Volume.
'''
data_dict = {
    'Open':  [100, 102, 103, 150, 200],
    'High':  [110, 112, 113, 160, 210],
    'Low':   [ 90,  92,  93, 140, 190],
    'Close': [100, 102, 153, 200, 180], # 注意看 Close 的变化
    'Volume':[1000,1002,1003,5000,1000]
}

print(type(data_dict))
print(data_dict)


dates = pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'])
print("=== Datetime ===")
print(type(dates))
print(dates)
print("============================\n")

'''
index was 0, 1, 2, ..
make it '2024-01-01', '2024-01-02', '2024-01-03', ..
'''
df = pd.DataFrame(data_dict, index=dates)


print("=== Input Data (DataFrame) ===")
print(type(df))
print(df)
print("============================\n")


# print("=== Input Data (Series) ===")
# print(type(df['High']))
# print(df['High'])
# print("============================\n")


'''
inherit from the backtesting's Strategy class
'''
class MyFirstStrategy(Strategy):
    def init(self):
        # self.data 在这里包含了整个 DataFrame 的引用
        print(f"[init] Strategy Initialized. Total data length: {len(self.data)}")
        print(type(self.data))
        print(self.data)
        print("[init] End")

    def next(self):

        # self.data.Close 是一个 Array (类似 List)
        # self.data.Close[-1] 是 "当前这一刻" 的价格 (Current Tick)
        # self.data.Close[-2] 是 "昨天" 的价格 (Previous Tick)
        print(self.data.Close)
        current_close = self.data.Close[-1]
        current_date = self.data.index[-1] # 获取当前时间
        print(f"[next] Date: {current_date} | Price: {current_close} | Position: {self.position.size}")

        prev_close = self.data.Close[-2]

        # == 简单的 trading logic ==
        if not self.position:
            if current_close >= prev_close:
                print(f"    >>> SIGNAL: BUY at {current_close}")
                self.buy() # 发送买单
        
        elif self.position:
            if current_close ==180:
                print(f"    >>> SIGNAL: SELL at {current_close}")
                self.position.close() # 平掉所有仓位

        return

# trade_on_close=True: 为了方便演示，我们在收盘价成交 (默认是在下一根K线的开盘价成交)
bt = Backtest(df, MyFirstStrategy, cash=10000, trade_on_close=True)
print("=== Starting Simulation Loop ===\n")
stats = bt.run()
print("\n=== Simulation Finished ===")

print("\n=== Final Stats (部分) ===")
print(type(stats))
print(stats)