import pandas as pd
import numpy as np
import yfinance as yf

# ==========================================
# 1. 定义核心对象：网格单 (GridOrder)
# ==========================================
class GridOrder:
    def __init__(self, buy_price, sell_price, quantity):
        self.buy_price = buy_price    # 这一格的买入价 (地板)
        self.sell_price = sell_price  # 这一格的卖出价 (天花板)
        self.quantity = quantity
        self.status = "OPEN"          # 状态: OPEN(等待买入) -> HOLDING(持仓中) -> CLOSED(已卖出)
        self.entry_time = None        # 什么时候买的
    
    def __repr__(self):
        return f"Grid({self.status}: Buy@{self.buy_price} -> Sell@{self.sell_price}) -> Quantity@{self.quantity}"

# ==========================================
# 2. 定义回测引擎：模拟交易所
# ==========================================
class GridBacktester:
    def __init__(self, df, lower_price, upper_price, grid_num, initial_balance):
        self.df = df
        self.lower_price = lower_price
        self.upper_price = upper_price
        self.grid_num = grid_num
        
        # 资金账户
        self.balance = initial_balance  # USDT 余额
        self.holdings = 0               # ETH 持仓数量
        self.total_profit = 0           # 累计网格套利利润
        self.trades_history = []        # 记录每一笔交易
        
        # 初始化网格
        self.grids = []
        self._init_grids()

    def _init_grids(self):
        """生成网格线，并创建订单对象"""
        prices = np.linspace(self.lower_price, self.upper_price, self.grid_num + 1)
        # print(prices)
        
        # 假设每个格子买 100 USDT 的货 (简化逻辑)
        # 实际上你应该根据总资金分配
        per_grid_usdt = self.balance / self.grid_num 
        # print(per_grid_usdt)
        
        # 创建 N 个格子
        for i in range(len(prices) - 1):
            buy_price = prices[i]
            sell_price = prices[i+1]
            
            # 计算这一格能买多少币 (Quantity)
            quantity = per_grid_usdt / buy_price
            # print("buy_price: ", buy_price, ", sell_price: ", sell_price, ", per_grid_usdt: ", per_grid_usdt, ", quantity: ", quantity)
            
            # 创建订单对象/object 放入列表/list
            grid = GridOrder(buy_price, sell_price, quantity)
            self.grids.append(grid)
            # print(grid)
            # print(self.grids)
            
        print(f"网格初始化完成: {self.grid_num} 个格子, 范围 {self.lower_price}-{self.upper_price}")

    def run(self):
        """开始回测循环"""
        print("开始回测...")
        
        # 遍历每一行数据 (每一分钟/每一小时)
        for index, row in self.df.iterrows():
            # print(f"index: {index}, row: {row}")
            current_price = row['Close'] # 假设列名叫 close
            timestamp = index # 假设有时间戳
            # print(f"current_price: {current_price}, Date: {timestamp}")
            
            # 核心逻辑：遍历每一个格子，看是否触发
            # *真实实盘中不需要遍历所有，只需看最近的，但回测为了准确遍历所有*
            
            for grid in self.grids:
                
                # --- 逻辑 A: 还没有买入 (OPEN)，看价格是否跌破买入价 ---
                '''
                grid是object
                这边用low比较好，因为在真实玩的时候，虽然价格还没close, 只要碰到 limit order就fulfill了
                '''
                if grid.status == "OPEN":
                    # 如果价格跌破了买入价 (这里用 low 还是 close 取决于激进程度，通常用 low 容易成交)
                    # 这里为了严谨，假设 High > Buy_Price > Low 哪怕是穿针也能成交
                    if row['Low'] <= grid.buy_price:
                        # 【买入动作】
                        cost = grid.buy_price * grid.quantity
                        print(f"买入: ${cost}")
                        
                        # 检查资金够不够
                        if self.balance >= cost:
                            self.balance -= cost
                            self.holdings += grid.quantity
                            grid.status = "HOLDING" # 状态变了！
                            grid.entry_time = timestamp
                            
                            # 记录日志
                            # print(f"[{timestamp}] 买入成交: {grid.buy_price}")

                # --- 逻辑 B: 已经持仓 (HOLDING)，看价格是否涨破卖出价 ---
                elif grid.status == "HOLDING":
                    # 如果价格涨破了卖出价
                    if row['High'] >= grid.sell_price:
                        # 【卖出动作】
                        revenue = grid.sell_price * grid.quantity
                        profit = revenue - (grid.buy_price * grid.quantity)
                        
                        self.balance += revenue
                        self.holdings -= grid.quantity
                        self.total_profit += profit
                        
                        # 记录交易历史
                        self.trades_history.append({
                            'time': timestamp,
                            'type': 'SELL',
                            'buy_at': grid.buy_price,
                            'sell_at': grid.sell_price,
                            'profit': profit
                        })
                        
                        # 状态重置！为了下次还能买
                        grid.status = "OPEN"
                        # print(f"[{timestamp}] 卖出止盈! 赚了 {profit:.2f} U")

    def report(self):
        """输出最终结果"""
        # 计算最后剩下的持仓市值 (浮动盈亏)
        final_price = self.df.iloc[-1]['Close']
        floating_value = self.holdings * final_price
        total_equity = self.balance + floating_value
        
        print("-" * 30)
        print(f"回测结束")
        print(f"总网格利润 (已落袋): {self.total_profit:.2f} U")
        print(f"最终持仓市值 (浮动): {floating_value:.2f} U")
        print(f"账户总资产: {total_equity:.2f} U")
        print(f"交易总次数: {len(self.trades_history)}")
        print("-" * 30)

# ==========================================
# 3. 造一些假数据来测试 (或者读取 CSV)
# ==========================================

# 我们造一个先跌后涨再震荡的数据
# dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
# # 模拟价格：从 3000 -> 2500 -> 2800 -> 2600 -> 2900
# prices = [3000]
# for _ in range(99):
#     change = np.random.uniform(-50, 50) # 随机波动
#     prices.append(prices[-1] + change)

# df_mock = pd.DataFrame({
#     'timestamp': dates,
#     'close': prices,
#     'high': [p + 10 for p in prices], # 简单模拟 High/Low
#     'low': [p - 10 for p in prices]
# })


# 3 真实数据从yahoo拿的
# 1. 设置下载参数
ticker = "AAPL"  # 股票代码，比如 Apple (AAPL), 比特币 (BTC-USD)
start_date = "2023-01-01"
end_date = "2023-12-31"

print(f"正在从 yfinance 下载 {ticker} 的真实数据...")

# 2. 获取数据 (这就是你要的 Dataset)
# yfinance 下载的数据自动包含了 Open, High, Low, Close, Volume
df = yf.download(ticker, start=start_date, end=end_date)

# --- 数据清洗小技巧 ---
# 某些版本的 yfinance 可能会返回多层索引，为了保险，我们把列名展平
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# 确保列名都是小写 (pandas_ta 并不强制，但这样最稳妥)
# df.columns = [x.lower() for x in df.columns]

# 2. (可选) 有时候 yfinance 会把列名搞成 "Price" 之类的名字，保险起见，重命名一下
# 这一步不是必须的，但能防止奇怪的 Bug
df.columns.name = None

# 3. 检查数据是否符合 pandas_ta 要求
print("\n数据前5行:")
print(df.head())
print("\n列名:", df.columns.tolist()) 
# 你会看到 ['Open', 'High', 'Low', 'Close', 'Volume']，这就是完美格式



# ==========================================
# 4. 运行
# ==========================================

# 10000 U, 区间 2000-4000, 20个格子
bot = GridBacktester(df, lower_price=2000, upper_price=4000, grid_num=20, initial_balance=10000)
bot.run()
bot.report()