import pandas as pd
import streamlit as st
import datetime as dt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random


class Account:
    def __init__(self, starting_cash, lot_per_in, lot_per_out, fair_out, mode, early_stop, go_crazy):
        self.cash = starting_cash
        self.equity = {'lot': 0, 'price': 0}
        self.lot_debt = {'lot': 0, 'price': 0}
        self.lot_per_in = lot_per_in
        self.lot_per_out = lot_per_out
        self.c_price = 0
        self.net_point = 0
        self.long_just_out = False
        self.short_just_out = False
        self.fair_out = fair_out
        self.mode = mode
        self.early_stop = early_stop
        self.go_crazy = go_crazy

    def buy_long(self):
        self.cash -= self.lot_per_in * 46000
        self.equity['lot'] += self.lot_per_in
        self.equity['price'] = self.c_price

    def sell_short(self):
        self.cash += self.lot_per_in * 46000
        self.lot_debt['lot'] += self.lot_per_in
        self.lot_debt['price'] = self.c_price

    def sell_long(self):
        lot_out = self.lot_per_out if self.equity['lot'] > self.lot_per_out else self.equity['lot']
        self.net_point += (self.c_price -
                           self.equity['price']) * lot_out
        self.cash += lot_out * \
            (46000 + (self.c_price - self.equity['price']) * 50)
        self.equity['lot'] -= lot_out
        if self.equity['lot'] == 0:
            self.equity['price'] = 0

    def buy_short(self):
        lot_out = self.lot_per_out if self.lot_debt['lot'] > self.lot_per_out else self.lot_debt['lot']
        self.net_point += (self.lot_debt['price'] -
                           self.c_price) * lot_out
        self.cash += lot_out * \
            ((self.lot_debt['price'] - self.c_price) * 50 - 46000)
        self.lot_debt['lot'] -= lot_out
        if self.lot_debt['lot'] == 0:
            self.lot_debt['price'] = 0

    def long_stop_loss(self):
        self.net_point += (self.c_price -
                           self.equity['price']) * self.equity['lot']
        self.cash += self.equity['lot'] * \
            (46000 + (self.c_price - self.equity['price']) * 50)
        self.equity['lot'] = 0
        self.equity['price'] = 0

    def short_stop_loss(self):
        self.net_point += (self.lot_debt['price'] -
                           self.c_price) * self.lot_debt['lot']
        self.cash += self.lot_debt['lot'] * \
            ((self.lot_debt['price'] - self.c_price) * 50 - 46000)
        self.lot_debt['lot'] = 0
        self.lot_debt['price'] = 0

    @st.cache(suppress_st_warning=True)
    def run_sml(self):
        max_k = max(data.open.iloc[0:3].max(), data.close.iloc[0:3].max(
        )) if self.mode == '?????????????????????' else max(data.iloc[0].open, data.iloc[0].close)
        min_k = min(data.open.iloc[0:3].min(), data.close.iloc[0:3].min(
        )) if self.mode == '?????????????????????' else min(data.open.iloc[0], data.close.iloc[0])
        result = pd.DataFrame()
        record = pd.DataFrame()
        min_max_record = pd.DataFrame()
        min_max_record = min_max_record.append(
            {'timestamp': data.iloc[0].timestamp, 'min': min_k, 'max': max_k}, ignore_index=True)
        cur_date = data.timestamp.iloc[0].date()
        day_start_id = 0
        not_in_day = None
        st.write('????????????')
        # st.write(f'max_price: {max_k}, min_price: {min_k}')
        for idx, row in data.iterrows():
            if not(dt.time(8, 0) <= row.timestamp.time() <= dt.time(14, 0)):
                continue

            # {'cond1': row.close < max_k}

            last_SMA5 = data.SMA5.iloc[idx-1]
            if row.timestamp.date() != cur_date:
                if self.fair_out:
                    # ??????
                    self.c_price = data.iloc[idx-1].close
                    # print(data.iloc[idx-1].timestamp, self.c_price)
                    point_diff = (self.lot_debt['price'] -
                                  self.c_price) * self.lot_debt['lot'] + (self.c_price - self.equity['price']) * self.equity['lot']
                    self.short_stop_loss()
                    self.long_stop_loss()
                    record = record.append(
                        {'timestamp': data.iloc[idx-1].timestamp, 'action': '??????', 'price': data.iloc[idx-1].close, 'detail': f"????????? {point_diff} ????????? {self.net_point}"}, ignore_index=True)

                max_k = max(data.open.iloc[idx:idx+3].max(),
                            data.close.iloc[idx:idx+3].max()) if self.mode == '??????' else max(data.open.iloc[idx], data.close.iloc[idx])
                min_k = min(data.open.iloc[idx:idx+3].min(),
                            data.close.iloc[idx:idx+3].min()) if self.mode == '??????' else min(data.open.iloc[idx], data.close.iloc[idx])
                cur_date = row.timestamp.date()
                day_start_id = idx
                not_in_day = cur_date if row.open - \
                    data.close.iloc[idx-1] <= 50 else None

            if cur_date == not_in_day:
                continue

            if idx - day_start_id < (3 if self.mode == '?????????????????????' else 1):
                continue

            min_max_record = min_max_record.append(
                {'timestamp': row.timestamp, 'min': min_k, 'max': max_k}, ignore_index=True)
            if self.long_just_out and row.low < max_k:
                self.long_just_out = False

            if self.short_just_out and row.high > min_k:
                self.short_just_out = False

            # 1. ??????
            # (a) ?????????????????????max
            if (row.status == 'rise' and row.close > max_k) and self.equity['lot'] + self.lot_debt['lot'] == 0 and not self.long_just_out and (self.early_stop == '???' or (row.timestamp.time() <= dt.time(10, 30) and self.early_stop == '????????????') or (row.timestamp.time() <= dt.time(11, 0) and self.early_stop == '????????????')):
                # print(row.timestamp, row.close, 'buy long')
                self.c_price = row.close if not self.go_crazy else max_k + \
                    random.randint(1, 5)
                record = record.append(
                    {'timestamp': row.timestamp, 'action': '??????', 'price': self.c_price, 'detail': f'?????? {row.close} > Max {max_k}'}, ignore_index=True)
                self.buy_long()
                continue

            # (b) ????????????K?????????????????????SMA5
            if row.status == 'drop' and row.close < row.SMA5 and row.SMA5 < last_SMA5 and self.equity['lot'] != 0 and self.equity['price'] < row.close:
                # print(
                # f'{row.timestamp} sell long: buy at {self.equity["price"]}, sell at {row.close}')
                self.c_price = row.close
                lot_out = self.lot_per_out if self.equity['lot'] > self.lot_per_out else self.equity['lot']

                point_diff = (self.c_price -
                              self.equity["price"]) * lot_out
                self.sell_long()
                record = record.append(
                    {'timestamp': row.timestamp, 'action': '????????????', 'price': row.close, 'detail': f'????????? {point_diff} ????????? {self.net_point}'}, ignore_index=True)
                self.long_just_out = True
                continue

            # (c) ????????????????????????Max?????????SMA5
            if (row.close < max_k or (row.close < row.SMA5 and row.SMA5 < last_SMA5)) and self.equity['lot'] != 0:
                # print(row.timestamp, row.close, 'sell_long')
                self.c_price = row.close
                point_diff = (self.c_price -
                              self.equity["price"]) * self.equity["lot"]
                self.long_stop_loss()
                record = record.append(
                    {'timestamp': row.timestamp, 'action': '????????????', 'price': row.close, 'detail': f'????????? {point_diff} ????????? {self.net_point}'}, ignore_index=True)
                self.long_just_out = True
                continue

            # 2. ??????

            # (a) ?????????????????????min
            if (row.status == 'drop' and row.close < min_k) and self.lot_debt['lot'] + self.lot_debt['lot'] == 0 and not self.short_just_out and (self.early_stop == '???' or (row.timestamp.time() <= dt.time(10, 30) and self.early_stop == '????????????') or (row.timestamp.time() <= dt.time(11, 0) and self.early_stop == '????????????')):
                # print(row.timestamp, row.close, 'sell_short')
                self.c_price = row.close if not self.go_crazy else min_k - \
                    random.randint(1, 5)
                record = record.append(
                    {'timestamp': row.timestamp, 'action': '??????', 'price': self.c_price, 'detail': f'?????? {row.close} < Min {min_k}'}, ignore_index=True)
                self.sell_short()
                continue

            # (b) ????????????K?????????????????????SMA5
            if row.status == 'rise' and row.close > row.SMA5 and row.SMA5 > last_SMA5 and self.lot_debt['lot'] != 0 and self.lot_debt['price'] > row.close:
                # print(
                # f'{row.timestamp} buy short: sell at {self.lot_debt["price"]}, buy at {row.close}')
                self.c_price = row.close
                lot_out = self.lot_per_out if self.lot_debt['lot'] > self.lot_per_out else self.lot_debt['lot']
                point_diff = (self.lot_debt['price'] -
                              self.c_price) * lot_out
                self.buy_short()
                record = record.append(
                    {'timestamp': row.timestamp, 'action': '????????????', 'price': row.close, 'detail': f"????????? {point_diff} ????????? {self.net_point}"}, ignore_index=True)
                self.short_just_out = True
                continue

            # (c) ????????????????????????Min?????????SMA5
            if (row.close > min_k or (row.close > row.SMA5 and row.SMA5 > last_SMA5)) and self.lot_debt['lot'] != 0:
                # print(row.timestamp, row.close, 'buy_short')
                self.c_price = row.close
                point_diff = (self.lot_debt["price"] -
                              self.c_price) * self.lot_debt["lot"]
                self.short_stop_loss()
                record = record.append(
                    {'timestamp': row.timestamp, 'action': '????????????', 'price': row.close, 'detail': f'????????? {point_diff} ????????? {self.net_point}'}, ignore_index=True)
                self.short_just_out = True
                continue

            result = result.append({'timestamp': row.timestamp, 'cash': self.cash, 'equity': self.equity['lot'], 'lot_debt': self.lot_debt['lot'], 'net asset': self.cash + 46000 * (
                self.equity['lot'] - self.lot_debt['lot']), 'net_point': self.net_point, 'realized_income': self.net_point * 50}, ignore_index=True)
        st.write(f'????????????, ????????????{result.iloc[-1].net_point}')
        return result, record, min_max_record


st.subheader("??????????????????")
uploaded_file = st.file_uploader("")
if uploaded_file is not None:
    try:
        data = pd.read_excel(uploaded_file)

        # data preprocessing
        data = data[['??????', '??????', '?????????', '?????????', '?????????', '?????????', 'SMA5']]
        data.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'SMA5']
        data = data.dropna()
        data['timestamp'] = [dt.datetime.strptime(str(row.date)[
            : 11] + str(row.time), '%Y-%m-%d %H:%M:%S') for idx, row in data.iterrows()]
        data = data[['timestamp', 'open', 'high', 'low', 'close', 'SMA5']]
        data['status'] = ['rise' if row.open <
                          row.close else 'drop' for idx, row in data.iterrows()]
        data.reset_index(inplace=True)
        data.drop('index', axis=1, inplace=True)
    except:
        data = pd.read_feather(uploaded_file)
        # data['status'] = ['rise' if row.open <
        #                   row.close else 'drop' for idx, row in data.iterrows()]
    sim_year_start = dt.datetime(st.selectbox(
        '????????????', [year for year in range(data.iloc[0].timestamp.year, data.iloc[-1].timestamp.year+1)]), 1, 1)
    end_year_ls = [year for year in range(
        data.iloc[0].timestamp.year, data.iloc[-1].timestamp.year+1)]
    sim_year_end = dt.datetime(st.selectbox(
        '????????????', end_year_ls, len(end_year_ls) - 1), 12, 31, 23, 59, 59)
    data = data[(sim_year_start < data.timestamp) & (
        data.timestamp < sim_year_end)].reset_index().drop('index', axis=1)
    st.header("????????????")
    st.write(data)
    start_sim_date = dt.datetime.combine(st.date_input(
        '??????????????????', data.timestamp.iloc[0].date()), dt.datetime.min.time())
    end_sim_date = dt.datetime.combine(st.date_input(
        '??????????????????', data.timestamp.iloc[-1].date()), dt.datetime.max.time())
    data = data[(start_sim_date <
                 data.timestamp) & (data.timestamp < end_sim_date)].reset_index()
    cash = st.text_input('??????????????????')
    mode = st.radio('??????????????????', ['?????????????????????', '?????????????????????'])
    if_early_stop = st.selectbox('??????????????????', ['???', '????????????', '????????????'])
    if_go_crazy = st.checkbox('??????????????????????????????????????????????????????')
    if_fair_out = st.checkbox('????????????????????????')
    # if_stop_early = st.
    lot_in = st.slider('?????????????????????', 0, 20)
    lot_out = st.slider('?????????????????????', 0, 20)

    if cash != "" and lot_in != 0 and lot_out != 0:
        Backtest = Account(starting_cash=int(
            cash), lot_per_in=lot_in, lot_per_out=lot_out, fair_out=if_fair_out, mode=mode, early_stop=if_early_stop, go_crazy=if_go_crazy)
        result, record, min_max_record = Backtest.run_sml()
        # record = record.set_index('timestamp')
        daily_result = pd.DataFrame()
        for idx, row in result.iterrows():
            if idx == result.shape[0] - 1:
                daily_result = daily_result.append(
                    {'date': row.timestamp.date(), 'income': row.realized_income}, ignore_index=True)
            elif row.timestamp.date() != result.iloc[idx+1].timestamp.date():
                daily_result = daily_result.append(
                    {'date': row.timestamp.date(), 'income': row.realized_income}, ignore_index=True)
        # day_range = (end_sim_date - start_sim_date).days
        # last_date_income = daily_result.iloc[0].income
        # for i in range(day_range):
        #     date = start_sim_date.date() + dt.timedelta(days=i)
        #     if date not in list(daily_result.date):
        #         daily_result = daily_result.append(
        #             {'date': date, 'income': last_date_income}, ignore_index=True)
        #     else:
        #         last_date_income = daily_result[daily_result.date ==
        #                                         date].income.iloc[0]
        daily_result.sort_values(by=['date'], inplace=True)
        daily_result['lag1'] = daily_result['income'].shift(-1)
        daily_result['lag1'].fillna(
            daily_result['income'].iloc[daily_result.shape[0]-1], inplace=True)
        daily_result['income_delta'] = daily_result['lag1'] - \
            daily_result['income']
        st.write(
            f"?????????????????????{round(daily_result['income_delta'].mean() / 50, 2)}???")
        bar = go.Scatter(x=daily_result['date'],
                         y=daily_result['income'], fill='tozeroy')
        fig = go.Figure(data=bar)
        st.header('???????????????')
        st.subheader('??????????????????')
        st.plotly_chart(fig)
        st.subheader('??????????????????')
        plot_mode = st.radio("??????????????????", ['??????', '??????'])
        if plot_mode == '??????':
            selected_date = data.timestamp.iloc[0].date()
            selected_date = st.date_input(
                '????????????', selected_date)
            start_date = dt.datetime.combine(
                selected_date, dt.datetime.min.time())
            end_date = dt.datetime.combine(
                selected_date, dt.datetime.max.time())
            col1, col2 = st.columns([.1, 1])
        #     if col1.button('Prev'):
        #         start_date -= dt.timedelta(days=1)
        #         end_date -= dt.timedelta(days=1)
        #     if col2.button('Next'):
        #         selected_date += dt.timedelta(days=1)
        #         start_date += dt.timedelta(days=1)
        #         end_date += dt.timedelta(days=1)
        else:
            start_date = dt.datetime.combine(st.date_input(
                '????????????', data.timestamp.iloc[0].date()), dt.datetime.min.time())
            end_date = dt.datetime.combine(st.date_input(
                '????????????', data.timestamp.iloc[-1].date()), dt.datetime.max.time())

        chart_data = data[(start_date < data.timestamp)
                          & (data.timestamp < end_date)]
        fig2 = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig2.add_trace(go.Candlestick(x=chart_data.timestamp,
                                      open=chart_data['open'],
                                      high=chart_data['high'],
                                      low=chart_data['low'],
                                      close=chart_data['close'],
                                      name='Price'
                                      ), row=1, col=1)
        fig2.add_trace(go.Scatter(x=chart_data.timestamp,
                                  y=chart_data['SMA5'],
                                  opacity=0.3,
                                  line=dict(color='blue', width=1),
                                  name='SMA 5'))
        fig2.add_trace(go.Scatter(x=min_max_record[(start_date <
                                                    min_max_record.timestamp) & (min_max_record.timestamp < end_date)].timestamp, y=min_max_record[(start_date <
                                                                                                                                                    min_max_record.timestamp) & (min_max_record.timestamp < end_date)]['min'], line=dict(color='purple', width=1), opacity=0.5, name='min'))
        fig2.add_trace(go.Scatter(x=min_max_record[(start_date <
                                                    min_max_record.timestamp) & (min_max_record.timestamp < end_date)].timestamp, y=min_max_record[(start_date <
                                                                                                                                                    min_max_record.timestamp) & (min_max_record.timestamp < end_date)]['max'], line=dict(color='purple', width=1), opacity=0.5, name='max'))
        fig2.add_trace(go.Scatter(x=record[(start_date < record.timestamp) & (record.timestamp < end_date)].timestamp, y=record[(
            start_date < record.timestamp) & (record.timestamp < end_date)].price, name='Action', mode='markers', marker={'color': 'yellow'}), row=1, col=1)

        fig2.add_trace(go.Scatter(x=result[(start_date < result.timestamp) & (result.timestamp < end_date)].timestamp, y=result[(
            start_date < result.timestamp) & (result.timestamp < end_date)]['realized_income'], name='Income', marker={'color': 'purple'}, fill='tozeroy'), row=3, col=1)
        st.plotly_chart(fig2, use_container_width=True)
        st.subheader('????????????')
        st.write(
            record[(
                start_date < record.timestamp) & (record.timestamp < end_date)])
