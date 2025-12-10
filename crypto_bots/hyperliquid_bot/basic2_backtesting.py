import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.test import GOOG

'''
这是我们在Strategy 里用的那个 helper function
input parameters: arr (array/list/pd.Series), n(int)
n - window size
Output: pd.Series 返回这快线/慢线 的 均值 (代表线本身)
'''
def SMA(arr,n):
    series = pd.Series(arr)
    return series.rolling(n).mean()

# 2. 我们造一点假数据
# prices = [10, 20, 30, 40, 50]
# Index:   0   1   2   3   4

# # 3. 调用函数
# sma_result = SMA(prices, n=3)

# # 4. 看看 Output
# # SMA 返回的是一个和原数组等长的 pandas.Series
# print("Original Prices:", prices)
# print("\nSMA (n=3) Output:")
# print(sma_result)
# print("\nType:", type(sma_result))


'''
parent class us Strategy


self.I 的作用 伪代码相当于 (如下)
def I(self, func, *args, **kwargs):
    # 1. Execution (执行回调函数)
    # 相当于调用: result = SMA(self.data.Close, 10)
    result = func(*args, **kwargs)
    
    # 2. Registration (注册以便画图)
    # 告诉框架："嘿，这是一个指标，名字叫 SMA，颜色是黄色，把它存起来"
    self._register_indicator_for_plotting(result, name=func.__name__)
    
    # 3. Return (返回结果给 Strategy 使用)
    return result
'''
class ManualStrategy(Strategy):
    # 快线
    n1 = 10
    n2 = 20
    def init(self):
        '''
        即使这里只是 "注册", SMA函数 也是在这里立刻被执行完毕的。
        self.sma1 和 self.sma2 现在是全长的 Array (包含了 NaN) = 整条快线，慢线 
        self.data.Close 是全部的Close price
        '''
        self.sma1 = self.I(SMA, self.data.Close, self.n1)
        self.sma2 = self.I(SMA, self.data.Close, self.n2)
        return
    

    '''
    从 index i=1 row/entry/item 开始的，跳过了index 0, end iteration is end at the last one yea
    '''
    def next(self):
        print("-------------self.data---------------")
        print(self.data)

        # edge case, the number of closed price is not enough to have mean value
        if len(self.data) < self.n2:
            return
        # extract the main variable
        # fast sma
        ma1_now = self.sma1[-1] # today closed price
        ma1_prev = self.sma1[-2] # yesterday

        # slow ma
        ma2_now = self.sma2[-1] # today
        ma2_prev = self.sma2[-2] # yesterday

        '''
        main logic
        case1: 昨天快线在下，今天快线在上 => 金叉 (上穿)
        case2: 昨天快线在上，今天快线在下 => 死叉 (下穿)
        '''
        is_golden_cross = (ma1_prev<ma2_prev) and (ma1_now>ma2_now)
        is_death_cross = (ma1_prev>ma2_prev) and (ma1_now<ma2_now)

        # execution
        # === Execution ===
        if not self.position:
            if is_golden_cross:
                print(f"Buy Signal! MA1: {ma1_prev:.2f}->{ma1_now:.2f}, MA2: {ma2_prev:.2f}->{ma2_now:.2f}")
                self.buy()
        
        elif self.position:
            if is_death_cross:
                print(f"Sell Signal! MA1: {ma1_prev:.2f}->{ma1_now:.2f}, MA2: {ma2_prev:.2f}->{ma2_now:.2f}")
                self.position.close()

        return


'''小dataset用于好理解'''
data_dict = {
    'Open':  [100, 102, 103, 150, 200],
    'High':  [110, 112, 113, 160, 210],
    'Low':   [ 90,  92,  93, 140, 190],
    'Close': [100, 102, 153, 200, 180], # 注意看 Close 的变化
    'Volume':[1000,1002,1003,5000,1000]
}

# print(type(data_dict))
# print(data_dict)

# dates = pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'])
# df = pd.DataFrame(data_dict, index=dates)

# print(df)

'''
GOOG 是我们 pass in 的 OHLCV (Open, High, Low, Close, Volume)
'''
# print(GOOG)
bt = Backtest(GOOG, ManualStrategy, cash=10000)
stats = bt.run()

print("----------------conclude----------------------")
# print(stats['_trades'].head()) # 打印前几笔交易看看

print(stats)

