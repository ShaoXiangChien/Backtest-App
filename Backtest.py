import pandas as pd
import streamlit as st
import datetime as dt
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class Account:
    def __init__(self, starting_cash, lot_per_in, lot_per_out):
        self.cash = starting_cash
        self.equity = {'lot': 0, 'price': 0}
        self.lot_debt = {'lot': 0, 'price': 0}
        self.lot_per_in = lot_per_in
        self.lot_per_out = lot_per_out
        self.c_price = 0
        self.net_point = 0
        self.stop_loss = False

    def buy_long(self):
        self.cash -= self.lot_per_in * 46000
        self.equity['lot'] += self.lot_per_in
        self.equity['price'] = self.c_price

    def sell_short(self):
        self.cash += self.lot_per_in * 46000
        self.lot_debt['lot'] += self.lot_per_in
        self.lot_debt['price'] = self.c_price

    def sell_long(self):
        if self.stop_loss:
            self.net_point += (self.c_price -
                               self.equity['price']) * self.equity['lot']
            self.cash += self.equity['lot'] * \
                (46000 + (self.c_price - self.equity['price']) * 50)
            self.equity['lot'] = 0
            self.stop_loss = False
        else:
            self.net_point += (self.c_price -
                               self.equity['price']) * self.lot_per_out
            self.cash += self.lot_per_out * \
                (46000 + (self.c_price - self.equity['price']) * 50)
            self.equity['lot'] = self.equity['lot'] - \
                self.lot_per_out if self.equity['lot'] > self.lot_per_out else 0
        if self.equity['lot'] == 0:
            self.equity['price'] = 0

    def buy_short(self):
        if self.stop_loss:
            self.net_point += (self.lot_debt['price'] -
                               self.c_price) * self.lot_debt['lot']
            self.cash += self.lot_debt['lot'] * \
                ((self.lot_debt['price'] - self.c_price) * 50 - 46000)
            self.lot_debt['lot'] = 0
            self.stop_loss = True
        else:
            self.net_point += (self.lot_debt['price'] -
                               self.c_price) * self.lot_per_out
            self.cash += self.lot_per_out * \
                ((self.lot_debt['price'] - self.c_price) * 50 - 46000)
            self.lot_debt['lot'] = self.lot_debt['lot'] - \
                self.lot_per_out if self.lot_debt['lot'] > self.lot_per_out else 0
        if self.lot_debt['lot'] == 0:
            self.lot_debt['price'] = 0

    def run_sml(self):
        max_k = max(data.open.iloc[0:3].max(), data.close.iloc[0:3].max())
        min_k = min(data.open.iloc[0:3].min(), data.close.iloc[0:3].min())
        result = pd.DataFrame()
        record = pd.DataFrame()
        cur_date = data.timestamp.iloc[0].date()
        st.write('模擬開始')
        # st.write(f'max_price: {max_k}, min_price: {min_k}')
        for idx, row in data.iterrows():
            # 1. 進場操作
            last_SMA5 = data.SMA5.iloc[idx-1]
            if row.timestamp.date() != cur_date:
                max_k = max(data.open.iloc[idx:idx+3].max(),
                            data.close.iloc[idx:idx+3].max())
                min_k = min(data.open.iloc[idx:idx+3].min(),
                            data.close.iloc[idx:idx+3].min())
                cur_date = row.timestamp.date()
            # (a) 做多：股價大於max
            if (row.status == 'rise' and row.close > max_k) and self.equity['lot'] == 0:
                print(row.timestamp, row.close, 'buy long')
                record = record.append(
                    {'timestamp': row.timestamp, 'action': '做多', 'detail': f'收盤 {row.close} > Max {max_k}'}, ignore_index=True)
                self.c_price = row.close
                self.buy_long()

            # (b) 做空：股價小於min
            if (row.status == 'drop' and row.close < min_k) and self.lot_debt['lot'] == 0:
                print(row.timestamp, row.close, 'sell_short')
                record = record.append(
                    {'timestamp': row.timestamp, 'action': '做空', 'detail': f'收盤 {row.close} < Min {min_k}'}, ignore_index=True)
                self.c_price = row.close
                self.sell_short()

            # 2. 出場操作

            # (a) 做空：紅K且股價高於上斜SMA5
            if row.status == 'rise' and row.close > row.SMA5 and row.SMA5 > last_SMA5 and self.lot_debt['lot'] != 0:
                print(
                    f'{row.timestamp} buy short: sell at {self.lot_debt["price"]}, buy at {row.close}')
                self.c_price = row.close
                point_diff = (self.lot_debt['price'] -
                              self.c_price) * self.lot_debt['lot']
                self.buy_short()
                record = record.append(
                    {'timestamp': row.timestamp, 'action': '做空出場', 'detail': f"點數差 {point_diff} 淨點數 {self.net_point}"}, ignore_index=True)

            # (b) 做多：黑K且股價低於下斜SMA5
            if row.status == 'drop' and row.close < row.SMA5 and row.SMA5 < last_SMA5 and self.equity['lot'] != 0:
                print(
                    f'{row.timestamp} sell long: buy at {self.equity["price"]}, sell at {row.close}')
                self.c_price = row.close
                point_diff = (self.c_price -
                              self.equity["price"]) * self.equity["lot"]
                self.sell_long()
                record = record.append(
                    {'timestamp': row.timestamp, 'action': '做多出場', 'detail': f'點數差 {point_diff} 淨點數 {self.net_point}'}, ignore_index=True)

            # 3. 停損點

            # (a) 做空：收盤價 > min
            if row.close > min_k and self.lot_debt['lot'] != 0:
                print(row.timestamp, row.close, 'buy_short')
                self.c_price = row.close
                point_diff = (self.lot_debt["price"] -
                              self.c_price) * self.lot_debt["lot"]
                self.stop_loss = True
                self.buy_short()
                record = record.append(
                    {'timestamp': row.timestamp, 'action': '做空停損', 'detail': f'點數差 {point_diff} 淨點數 {self.net_point}'}, ignore_index=True)

            # (b) 做多：收盤價 < max
            if row.close < max_k and self.equity['lot'] != 0:
                print(row.timestamp, row.close, 'sell_long')
                self.c_price = row.close
                point_diff = (self.c_price -
                              self.equity["price"]) * self.equity["lot"]
                self.stop_loss = True
                self.sell_long()
                record = record.append(
                    {'timestamp': row.timestamp, 'action': '做多停損', 'detail': f'點數差 {point_diff} 淨點數 {self.net_point}'}, ignore_index=True)

            result = result.append({'timestamp': row.timestamp, 'cash': self.cash, 'equity': self.equity['lot'], 'lot_debt': self.lot_debt['lot'], 'net asset': self.cash + 46000 * (
                self.equity['lot'] - self.lot_debt['lot']), 'net_point': self.net_point, 'realized_income': self.net_point * 50}, ignore_index=True)
        st.write(f'模擬完成, 淨點數：{result.iloc[-1].net_point}')
        return result, record


st.subheader("上傳股價資訊")
uploaded_file = st.file_uploader("")
if uploaded_file is not None:
    data = pd.read_excel(uploaded_file)

    # data preprocessing
    data = data[['日期', '時間', '開盤價', '最高價', '最低價', '收盤價', 'SMA5']]
    data.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'SMA5']
    data = data.dropna()
    data['timestamp'] = [dt.datetime.strptime(str(row.date)[
        : 11] + str(row.time), '%Y-%m-%d %H:%M:%S') for idx, row in data.iterrows()]
    data = data[['timestamp', 'open', 'high', 'low', 'close', 'SMA5']]
    data['status'] = ['rise' if row.open <
                      row.close else 'drop' for idx, row in data.iterrows()]
    data.reset_index(inplace=True)
    data.drop('index', axis=1, inplace=True)
    st.subheader("股價資訊")
    st.write(data)
    start_sim_date = dt.datetime.combine(st.date_input(
        '模擬開始日期', data.timestamp.iloc[0].date()), dt.datetime.min.time())
    end_sim_date = dt.datetime.combine(st.date_input(
        '模擬結束日期', data.timestamp.iloc[-1].date()), dt.datetime.max.time())
    data = data[(start_sim_date <
                 data.timestamp) & (data.timestamp < end_sim_date)]
    cash = st.text_input('輸入起始本金')
    lot_in = st.slider('每次進場之口數', 0, 20)
    lot_out = st.slider('每次出場之百分比', 0, 100)

    if cash != "" and lot_in != 0 and lot_out != 0:
        Backtest = Account(starting_cash=int(
            cash), lot_per_in=lot_in, lot_per_out=round(lot_in * 0.01 * lot_out, 0))
        result, record = Backtest.run_sml()
        # record = record.set_index('timestamp')
        start_date = dt.datetime.combine(st.date_input(
            '起始日期', data.timestamp.iloc[0].date()), dt.datetime.min.time())
        end_date = dt.datetime.combine(st.date_input(
            '結束日期', data.timestamp.iloc[-1].date()), dt.datetime.max.time())
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Candlestick(x=data[(start_date <
                                             data.timestamp) & (data.timestamp < end_date)].timestamp,
                                     open=data[(start_date <
                                                data.timestamp) & (data.timestamp < end_date)]['open'],
                                     high=data[(start_date <
                                                data.timestamp) & (data.timestamp < end_date)]['high'],
                                     low=data[(start_date <
                                               data.timestamp) & (data.timestamp < end_date)]['low'],
                                     close=data[(start_date <
                                                 data.timestamp) & (data.timestamp < end_date)]['close'],
                                     name='Price'
                                     ))
        fig.add_trace(go.Scatter(x=result[(start_date < result.timestamp) & (result.timestamp < end_date)].timestamp, y=result[(start_date < result.timestamp) & (result.timestamp < end_date)]['realized_income'],
                                 name='Income', mode='lines+markers', line={'color': 'blue'}), secondary_y=True)
        st.subheader('回測模擬')
        st.plotly_chart(fig, use_container_width=True)
        st.subheader('操作記錄')
        st.write(
            record)
