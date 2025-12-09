import pandas as pd

# 1. 这是我们在 Strategy 里用的那个 helper function
def SMA(array, n):
    """
    Input: array (list or pd.Series)
    Input: n (int, window size)
    Output: pd.Series
    """
    series = pd.Series(array)
    return series.rolling(n).mean()

# 2. 我们造一点假数据
prices = [10, 20, 30, 40, 50]
# Index:   0   1   2   3   4

# 3. 调用函数
sma_result = SMA(prices, n=3)

# 4. 看看 Output
# SMA 返回的是一个和原数组等长的 pandas.Series
print("Original Prices:", prices)
print("\nSMA (n=3) Output:")
print(sma_result)
print("\nType:", type(sma_result))