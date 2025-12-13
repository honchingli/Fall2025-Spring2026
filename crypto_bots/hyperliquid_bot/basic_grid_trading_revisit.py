
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

