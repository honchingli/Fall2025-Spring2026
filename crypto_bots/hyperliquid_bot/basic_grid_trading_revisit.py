
import pandas as pd
import numpy as np
import yfinance as yf

'''
这边只是把basic_grid_trading_backtest algo重新写一遍熟悉一下
这个algo的缺点，只是个做多的网格策略，无止损，无做空的sell limit order
meaning:
波动不够多的时候，赚得也不多，更不要说我们并无做空

在下跌趋势里，亏损大，因为我们一直hold着 正在亏损的positions/holdings 无止损
如果开杠杆，那么亏损就很大了，很容易爆仓
floating/浮仓为负数

在上升趋势里，我们永远有止盈 (最上面的那条线就是我们的最后止盈点)
所以在上升趋势里，到最后全部candles都backtest完之后 是不会有holding的，因为止盈了

而且有个bug，网格不应该追涨，这边价格上升超过那条线也会买入
'''

'''
网格单 Grid order
state machine, 每个网格/线，只能有一个状态
either Open/Sell limit/Buy limit
这边为了好理解，理解成网格 不是线

eg.

当current价格来到2400到2600的区间的时候
做一个判断
当前格子的状态是不是0pen
是Open的话
cur_price是不是低于buy_price, 是: 买入，不是: pass (只能碰到下面线的时候才买入)

是Holding的话 (这个格子已经有一个position)
cur_price是不是高于sell_price/上面那条线，是: 卖出，不是: 继续Hold

3600--------------------------------------------

3400--------------------------------------------

3200--------------------------------------------

3000--------------------------------------------

2800--------------------------------------------
sell_price = 2800
buy_price = 2600
2600--------------------------------------------
sell_price = 2600
buy_price = 2400
2400--------------------------------------------

'''
class GridOrder:
    def __init__(self, buy_price, sell_price, quantity):
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.quantity = quantity
        self.status = "OPEN"
        self.entry_time = None
    
    def __repr__(self):
        return f"Grid({self.status}: Buy@{self.buy_price} -> Sell@{self.sell_price}) -> Quantity@{self.quantity}"
        

'''
backtesting, mimic like trading platform
we having upper bound and lower bound
'''
class GridBacktester:
    def __init__(self, df, lower_price, upper_price, grid_num, init_balance):
        self.df = df
        self.lower_price = lower_price
        self.upper_price = upper_price
        self.grid_num = grid_num

        ''' user's account'''
        self.balance = init_balance #账号余额
        self.holding = 0    # 持仓数量,  positions
        self.total_profit = 0 #累积利润
        self.trades_history = []

        # initialize our grid
        self.grids = []
        self._init_grids()
    
    def _init_grids(self):
        '''生成网格线，initiate/create GridOrder objects'''
        prices = np.linspace(self.lower_price, self.upper_price, self.grid_num+1)
        '''这边简化逻辑了, 每个格子买的数量base on the account balance'''
        per_grid_value = self.balance / self.grid_num

        '''
        create N grids
        格子的数量会比线的数量少1
        从这边开始发现了个 Big BUG of this algo
        在run function里面
        for cur_price within all prices
            for grid of grids
                if cur_price[low] <= grid.buy_price
                    # 买入
                    cost = grid.buy_price * grid.quantity
        那么
        eg.
        当前价格在2000
        那一下子上面 (2200, 2400, 2600, .., 4000) 的买单会全部一次性触发
        并且到我们的cost里面
        是不对的
        '''
        for i in range(len(prices - 1)):
            grid = GridOrder(prices[0])