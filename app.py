import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import datetime
from FinMind.data import DataLoader

st.set_page_config(page_title="ETF 損益分析系統", layout="wide")
st.title("📈 ETF 損益分析與預測系統")
st.markdown("---")

fm_api = DataLoader()

@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        rate_data = yf.Ticker("USDTWD=X").history(period="1d")
        if not rate_data.empty:
            last_close = rate_data['Close'].iloc[-1]
            if pd.notna(last_close) and last_close > 0:
                return float(last_close), False
        return 32.0, True
    except:
        return 32.0, True

current_usd_twd_rate, is_rate_default = get_exchange_rate()

# ==========================================
# 頂層三大分頁架構
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 個股歷史趨勢與技術分析", "💰 定期定額回測", "📺 市場趨勢即時掃描"])

# ------------------------------------------
# 🧠 第一分頁：單檔股票技術分析
# ------------------------------------------
with tab1:
    with st.container(border=True):
        st.subheader("🛠️ 查詢與條件設定")
        t1_c1, t1_c2, t1_c3 = st.columns([1.5, 1.5, 2])
        
        with t1_c1:
            preset_options = ["0050.TW (元大台灣50)", "0056.TW (元大高股息)", "2330.TW (台積電)", "AAPL (蘋果)", "🔍 自訂輸入代碼..."]
            selected_preset = st.selectbox("選擇查詢標的：", preset_options, key="t1_preset")
            if selected_preset == "🔍 自訂輸入代碼...":
                etf_option = st.text_input("請輸入代碼 (台股請加 .TW)：", "00940.TW", key="t1_custom")
            else:
                etf_option = selected_preset.split(" ")[0]
            data_source = st.radio("優先資料來源：", ("Yahoo Finance", "FinMind (僅限台股)"), horizontal=True, key="t1_source")
            
        with t1_c2:
            quick_time = st.radio("時間區間：", ["近 1 個月", "近 3 個月", "今年以來", "全部歷史", "進階自訂..."], horizontal=True, key="t1_time")
            is_custom_date = False
            
            if quick_time == "近 1 個月": days_to_fetch = 30
            elif quick_time == "近 3 個月": days_to_fetch = 90
            elif quick_time == "今年以來": 
                days_to_fetch = (datetime.date.today() - datetime.date(datetime.date.today().year, 1, 1)).days
            elif quick_time == "全部歷史": days_to_fetch = 365*20
            else:
                advanced_time = st.selectbox("進階區間選擇：", ["近一週", "近半年", "近兩年", "📅 自訂日曆區間"], key="t1_adv_time")
                if advanced_time == "近一週": days_to_fetch = 7
                elif advanced_time == "近半年": days_to_fetch = 180
                elif advanced_time == "近兩年": days_to_fetch = 365*2
                else:
                    date_range = st.date_input("選擇起訖日期", [datetime.date.today() - datetime.timedelta(days=30), datetime.date.today()], key="t1_date")
                    if len(date_range) == 2:
                        custom_start, custom_end = date_range
                        is_custom_date = True
                    else:
                        st.stop()
            
        with t1_c3:
            currency_label = st.radio("顯示計價幣別：", ("預設 (新台幣)", "美元 (USD)"), horizontal=True, key="t1_currency")
            st.markdown("**主圖表顯示控制：**")
            chart_type = st.radio("主圖表類型", ["📈 收盤價折線圖", "📊 專業 K 線與成交量圖"], horizontal=True, key="t1_chart_type")

        search_button = st.button("🚀 載入歷史數據並繪圖", use_container_width=True, key="t1_btn")

    if search_button:
        with st.spinner(f"系統正撈取 {etf_option} 歷史數據中..."):
            hist_data = pd.DataFrame()
            fetch_success = False
            actual_source = data_source
            
            if is_custom_date:
                end_date = custom_end
                display_start_date = custom_start
            else:
                end_date = datetime.date.today()
                display_start_date = end_date - datetime.timedelta(days=days_to_fetch)
            
            fetch_start_date = display_start_date - datetime.timedelta(days=90)

            try:
                if data_source == "Yahoo Finance":
                    temp_data = yf.Ticker(etf_option).history(start=fetch_start_date, end=end_date, auto_adjust=True)
                    # 👇 加上這行：無情刪除沒有收盤價的 NaN 幽靈數據
                    temp_data = temp_data.dropna(subset=['Close']) 
                    
                    if not temp_data.empty and len(temp_data) > 1:
                        hist_data = temp_data
                        fetch_success = True
                    else:
                        if etf_option.endswith(".TW"):
                            actual_source = "FinMind (備援)"
                            fm_id = etf_option.replace(".TW", "")
                            fm_df = fm_api.taiwan_stock_daily(stock_id=fm_id, start_date=fetch_start_date.strftime("%Y-%m-%d"), end_date=end_date.strftime("%Y-%m-%d"))
                            if not fm_df.empty:
                                fm_df = fm_df.rename(columns={'date': 'Date', 'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'Trading_Volume': 'Volume'})
                                fm_df['Date'] = pd.to_datetime(fm_df['Date'])
                                hist_data = fm_df.set_index('Date')
                                fetch_success = True
                else:
                    fm_id = etf_option.replace(".TW", "")
                    fm_df = fm_api.taiwan_stock_daily(stock_id=fm_id, start_date=fetch_start_date.strftime("%Y-%m-%d"), end_date=end_date.strftime("%Y-%m-%d"))
                    if not fm_df.empty:
                        fm_df = fm_df.rename(columns={'date': 'Date', 'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'Trading_Volume': 'Volume'})
                        fm_df['Date'] = pd.to_datetime(fm_df['Date'])
                        hist_data = fm_df.set_index('Date')
                        fetch_success = True
            except Exception:
                pass

            if fetch_success:
                if hist_data.index.tz is not None:
                    hist_data.index = hist_data.index.tz_localize(None)

                is_tw_stock = etf_option.endswith(".TW") or "FinMind" in actual_source
                if currency_label == "預設 (新台幣)":
                    if not is_tw_stock: 
                        for col in ['Open', 'High', 'Low', 'Close']:
                            if col in hist_data.columns: hist_data[col] = hist_data[col] * current_usd_twd_rate
                    currency_symbol = "NT$"
                else:
                    if is_tw_stock: 
                        for col in ['Open', 'High', 'Low', 'Close']:
                            if col in hist_data.columns: hist_data[col] = hist_data[col] / current_usd_twd_rate
                    currency_symbol = "US$"

                hist_data['MA20'] = hist_data['Close'].rolling(window=20).mean()
                hist_data['MA60'] = hist_data['Close'].rolling(window=60).mean()
                
                delta = hist_data['Close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.ewm(com=13, adjust=False).mean()
                avg_loss = loss.ewm(com=13, adjust=False).mean()
                rs = avg_gain / avg_loss
                hist_data['RSI'] = np.where(avg_loss == 0, 100, 100 - (100 / (1 + rs)))
                
                hist_data['Price_Diff'] = hist_data['Close'].diff()
                hist_data['Pct_Change'] = hist_data['Close'].pct_change() * 100
                hist_data['Hover_Text'] = (
                    "<b>價格差:</b> " + hist_data['Price_Diff'].apply(lambda x: f"{x:+.2f}" if pd.notnull(x) else "0") + "<br>" +
                    "<b>漲跌幅:</b> " + hist_data['Pct_Change'].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "0%")
                )

                if quick_time != "全部歷史":
                    hist_data = hist_data[hist_data.index >= pd.Timestamp(display_start_date)]

                st.session_state['t1_data'] = hist_data
                st.session_state['t1_meta'] = {'etf': etf_option, 'sym': currency_symbol, 'src': actual_source}
            else:
                st.error("❌ 無法獲取資料，請檢查代碼或網路。")

    if st.session_state.get('t1_data') is not None:
        data = st.session_state['t1_data']
        meta = st.session_state['t1_meta']
        latest = data.iloc[-1]
        
        st.success(f"✅ 成功自 {meta['src']} 載入 **{meta['etf']}**！")
        
        c1, c2, c3 = st.columns(3)
        price_diff = latest['Close'] - data['Close'].iloc[0]
        with c1: st.metric("期間最後結算價格", f"{meta['sym']}{latest['Close']:.2f}")
        with c2: st.metric("選定區間總漲跌幅", f"{price_diff:+.2f}", f"{(price_diff/data['Close'].iloc[0]*100):+.2f}%")
        with c3: st.metric("顯示歷史天數", f"{len(data)} 天")

        with st.expander("⚙️ 展開進階圖表與指標設定 (MA均線、RSI)"):
            exp_c1, exp_c2, exp_c3 = st.columns([1, 1, 1.5])
            with exp_c1:
                st.markdown("**均線設定**")
                t1_show_ma20 = st.toggle("顯示 MA20 (月線)", value=True, key="t1_tg_ma20")
                t1_show_ma60 = st.toggle("顯示 MA60 (季線)", value=True, key="t1_tg_ma60")
                if st.session_state.get('t1_chart_type') == "📈 收盤價折線圖":
                    show_markers = st.toggle("顯示折線圖資料點 (圓點)", value=False, key="t1_markers")
            with exp_c2:
                st.markdown("**副圖設定**")
                show_rsi = st.toggle("顯示 RSI 技術指標圖", value=False, key="t1_tg_rsi")
                if show_rsi:
                    show_rsi_markers = st.toggle("顯示 RSI 資料點", value=False, key="t1_tg_rsi_mk")
            with exp_c3:
                if show_rsi:
                    st.markdown("**🎨 RSI 顏色自訂**")
                    color_col1, color_col2, color_col3 = st.columns(3)
                    with color_col1: color_overbought = st.color_picker("超買區 (>70)", "#FF0000", key="t1_cp_ob")
                    with color_col2: color_normal = st.color_picker("RSI 主線", "#800080", key="t1_cp_nm")
                    with color_col3: color_oversold = st.color_picker("超賣區 (<30)", "#008000", key="t1_cp_os")
                else:
                    st.markdown("**🎨 RSI 顏色自訂**")
                    st.caption("開啟左側 RSI 副圖後即可設定")
        
        required_kline_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        has_full_kline_data = all(col in data.columns for col in required_kline_cols)

        actual_dates = data.index.strftime("%Y-%m-%d").tolist()
        dt_all = pd.date_range(start=data.index[0], end=data.index[-1], freq='D').strftime("%Y-%m-%d").tolist()
        dt_breaks = list(set(dt_all) - set(actual_dates))

        if st.session_state.get('t1_chart_type') == "📊 專業 K 線與成交量圖":
            if has_full_kline_data:
                with st.container(border=True):
                    fig_k = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3], row_titles=["價格", "成交量"])
                    fig_k.add_trace(go.Candlestick(
                        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
                        name='K線條', increasing_line_color='red', increasing_fillcolor='red', decreasing_line_color='green', decreasing_fillcolor='green'
                    ), row=1, col=1)
                    
                    if t1_show_ma20: fig_k.add_trace(go.Scatter(x=data.index, y=data['MA20'], mode='lines', name='MA20', line=dict(color='orange', width=1.5)), row=1, col=1)
                    if t1_show_ma60: fig_k.add_trace(go.Scatter(x=data.index, y=data['MA60'], mode='lines', name='MA60', line=dict(color='blue', width=1.5)), row=1, col=1)
                    
                    bar_colors = ['red' if row['Close'] >= row['Open'] else 'green' for index, row in data.iterrows()]
                    fig_k.add_trace(go.Bar(x=data.index, y=data['Volume'], name='成交量', marker_color=bar_colors, opacity=0.7), row=2, col=1)
                    
                    fig_k.update_layout(
                        title=f"{meta['etf']} 歷史 K 線與量能圖", 
                        xaxis_rangeslider_visible=False, 
                        height=600, 
                        template="plotly_white", 
                        hovermode="x unified",
                        xaxis=dict(rangebreaks=[dict(values=dt_breaks)])
                    )
                    st.plotly_chart(fig_k, use_container_width=True)
            else:
                st.warning(f"⚠️ {meta['etf']} 缺乏完整的開高低收或成交量資料，無法繪製 K 線，已自動降級顯示折線圖。")
                with st.container(border=True):
                    fig_line = go.Figure()
                    fig_line.add_trace(go.Scatter(
                        x=data.index, y=data['Close'], 
                        mode='lines+markers' if st.session_state.get('t1_markers') else 'lines',
                        name='收盤價', text=data['Hover_Text'], hovertemplate="<b>時間</b>: %{x}<br><b>價格</b>: %{y:.2f}<br>%{text}<extra></extra>"
                    ))
                    if t1_show_ma20: fig_line.add_trace(go.Scatter(x=data.index, y=data['MA20'], mode='lines', name='MA20', line=dict(dash='dot', color='orange')))
                    if t1_show_ma60: fig_line.add_trace(go.Scatter(x=data.index, y=data['MA60'], mode='lines', name='MA60', line=dict(dash='dot', color='green')))
                    fig_line.update_layout(
                        title=f"{meta['etf']} 歷史收盤價走勢 (降級顯示)", 
                        xaxis_title="日期", yaxis_title=f"價格 ({meta['sym']})", 
                        height=450, template="plotly_white", hovermode="x unified",
                        xaxis=dict(rangebreaks=[dict(values=dt_breaks)])
                    )
                    st.plotly_chart(fig_line, use_container_width=True)
        else:
            with st.container(border=True):
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(
                    x=data.index, y=data['Close'], 
                    mode='lines+markers' if st.session_state.get('t1_markers') else 'lines',
                    name='收盤價', text=data['Hover_Text'], hovertemplate="<b>時間</b>: %{x}<br><b>價格</b>: %{y:.2f}<br>%{text}<extra></extra>"
                ))
                if t1_show_ma20: fig_line.add_trace(go.Scatter(x=data.index, y=data['MA20'], mode='lines', name='MA20', line=dict(dash='dot', color='orange')))
                if t1_show_ma60: fig_line.add_trace(go.Scatter(x=data.index, y=data['MA60'], mode='lines', name='MA60', line=dict(dash='dot', color='green')))
                fig_line.update_layout(
                    title=f"{meta['etf']} 歷史收盤價走勢", 
                    xaxis_title="日期", yaxis_title=f"價格 ({meta['sym']})", 
                    height=450, template="plotly_white", hovermode="x unified",
                    xaxis=dict(rangebreaks=[dict(values=dt_breaks)])
                )
                st.plotly_chart(fig_line, use_container_width=True)

        if show_rsi:
            with st.container(border=True):
                fig_rsi = go.Figure()
                rsi_mode = 'lines+markers' if st.session_state.get('t1_tg_rsi_mk') else 'lines'

                def hex_to_rgba(hex_color, opacity=0.3):
                    hex_color = hex_color.lstrip('#')
                    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    return f'rgba({r}, {g}, {b}, {opacity})'

                valid_rsi = data.dropna(subset=['RSI'])
                if not valid_rsi.empty:
                    x_orig = valid_rsi.index
                    y_orig = valid_rsi['RSI'].values
                    x_fill, y_fill = [], []
                    
                    for i in range(len(x_orig) - 1):
                        x1, y1 = x_orig[i], y_orig[i]
                        x2, y2 = x_orig[i+1], y_orig[i+1]
                        x_fill.append(x1)
                        y_fill.append(y1)
                        
                        if (y1 < 70 and y2 > 70) or (y1 > 70 and y2 < 70):
                            frac = (70 - y1) / (y2 - y1)
                            x_fill.append(x1 + (x2 - x1) * frac)
                            y_fill.append(70.0)
                            
                        if (y1 < 30 and y2 > 30) or (y1 > 30 and y2 < 30):
                            frac = (30 - y1) / (y2 - y1)
                            x_fill.append(x1 + (x2 - x1) * frac)
                            y_fill.append(30.0)
                            
                    x_fill.append(x_orig[-1])
                    y_fill.append(y_orig[-1])
                    
                    x_fill, y_fill = np.array(x_fill), np.array(y_fill)
                    rsi_ob_clamped = np.where(y_fill >= 70, y_fill, 70)
                    rsi_os_clamped = np.where(y_fill <= 30, y_fill, 30)

                    fig_rsi.add_trace(go.Scatter(x=x_fill, y=[70]*len(x_fill), mode='lines', line=dict(width=0), hoverinfo='skip', showlegend=False))
                    fig_rsi.add_trace(go.Scatter(x=x_fill, y=rsi_ob_clamped, mode='lines', fill='tonexty', fillcolor=hex_to_rgba(color_overbought), line=dict(width=0), hoverinfo='skip', showlegend=False))
                    fig_rsi.add_trace(go.Scatter(x=x_fill, y=[30]*len(x_fill), mode='lines', line=dict(width=0), hoverinfo='skip', showlegend=False))
                    fig_rsi.add_trace(go.Scatter(x=x_fill, y=rsi_os_clamped, mode='lines', fill='tonexty', fillcolor=hex_to_rgba(color_oversold), line=dict(width=0), hoverinfo='skip', showlegend=False))
                    fig_rsi.add_trace(go.Scatter(x=data.index, y=data['RSI'], mode=rsi_mode, name='RSI', line=dict(color=color_normal, width=2)))

                fig_rsi.add_hline(y=70, line_dash="dash", line_color="gray", annotation_text="超買區 (70)", annotation_position="top left")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="gray", annotation_text="超賣區 (30)", annotation_position="bottom left")
                fig_rsi.update_layout(
                    title=f"{meta['etf']} RSI 相對強弱指標面板", 
                    height=350, template="plotly_white", yaxis_range=[0, 100], hovermode="x unified",
                    xaxis=dict(rangebreaks=[dict(values=dt_breaks)])
                )
                st.plotly_chart(fig_rsi, use_container_width=True)

# ------------------------------------------
# 🧠 第二分頁：獨立的定期定額回測 (升級雙軌數據分流)
# ------------------------------------------
with tab2:
    with st.container(border=True):
        st.subheader("💵 定期定額投資試算 (獨立設定)")
        t2_c1, t2_c2, t2_c3, t2_c4 = st.columns([1.2, 1.2, 1.2, 1.4])
        with t2_c1:
            t2_target = st.text_input("輸入回測標的代碼：", "0050.TW", key="t2_target")
        with t2_c2:
            t2_amount = st.number_input("每月固定投入金額 (NT$)", min_value=1000, value=10000, step=1000, key="t2_amt")
        with t2_c3:
            t2_start_date = st.date_input("選擇回測起始日期", datetime.date(2020, 1, 1), key="t2_date")
        with t2_c4:
            # 🌟 核心增強：加入資料來源選擇，預設為具備股價還原功能的 Yahoo Finance
            t2_source = st.radio("優先資料來源設定：", ("Yahoo Finance", "FinMind (僅限台股)"), horizontal=True, key="t2_source")
            
        if t2_source == "FinMind (僅限台股)":
            st.caption("⚠️ 提示：FinMind 提供未經除權息調整之歷史原價。長期回測建議切換為 **Yahoo Finance**（具備自動還原股價功能），計算總報酬率與真實 ROI 才會精準。")
            
        t2_button = st.button("🚀 執行定期定額回測", use_container_width=True, key="t2_btn")

    if t2_button:
        with st.spinner(f"正在抓取 {t2_target} 歷史數據進行回測..."):
            try:
                start_date_str = t2_start_date.strftime("%Y-%m-%d")
                end_date_str = datetime.date.today().strftime("%Y-%m-%d")
                
                actual_t2_source = t2_source
                bt_data = pd.DataFrame()
                
                # 🌟 核心增強：根據使用者選取的來源進行智慧路由與備援
                if t2_source == "Yahoo Finance":
                    bt_data = yf.Ticker(t2_target).history(start=start_date_str, end=end_date_str, auto_adjust=True)
                    bt_data = bt_data.dropna(subset=['Close']) 
                    if (bt_data.empty or len(bt_data) <= 1) and t2_target.endswith(".TW"):
                        actual_t2_source = "FinMind (備援)"
                        fm_id = t2_target.replace(".TW", "")
                        bt_df = fm_api.taiwan_stock_daily(stock_id=fm_id, start_date=start_date_str, end_date=end_date_str)
                        if not bt_df.empty:
                            bt_df = bt_df.rename(columns={'date': 'Date', 'close': 'Close'})
                            bt_df['Date'] = pd.to_datetime(bt_df['Date'])
                            bt_data = bt_df.set_index('Date')
                else:
                    fm_id = t2_target.replace(".TW", "")
                    bt_df = fm_api.taiwan_stock_daily(stock_id=fm_id, start_date=start_date_str, end_date=end_date_str)
                    if not bt_df.empty:
                        bt_df = bt_df.rename(columns={'date': 'Date', 'close': 'Close'})
                        bt_df['Date'] = pd.to_datetime(bt_df['Date'])
                        bt_data = bt_df.set_index('Date')
                
                if not bt_data.empty and len(bt_data) > 1:
                    # 🌟 核心防呆：抹除時區資訊避免 to_period 時異常
                    if bt_data.index.tz is not None:
                        bt_data.index = bt_data.index.tz_localize(None)
                        
                    bt_data['YearMonth'] = bt_data.index.to_period('M')
                    monthly_first_days = bt_data.groupby('YearMonth').first()
                    
                    total_months = len(monthly_first_days)
                    total_cost = total_months * t2_amount
                    total_shares = (t2_amount / monthly_first_days['Close']).sum()
                    final_value = total_shares * bt_data['Close'].iloc[-1]
                    
                    st.success(f"✅ 回測完成！ (數據來源: {actual_t2_source}) | 期間：{monthly_first_days.index[0]} 至 {monthly_first_days.index[-1]} (共 {total_months} 個月)")
                    res_c1, res_c2, res_c3 = st.columns(3)
                    with res_c1: st.metric("總投入成本", f"NT$ {total_cost:,.0f}")
                    with res_c2: st.metric("期末總價值", f"NT$ {final_value:,.0f}", f"{final_value - total_cost:+,.0f}")
                    with res_c3: st.metric("總報酬率 (ROI)", f"{((final_value - total_cost) / total_cost * 100):.2f}%")
                else:
                    st.error("❌ 獲取資料失敗，請確認該標的在指定日期已上市。")
            except Exception:
                st.error("資料處理發生錯誤。")

# ------------------------------------------
# 🧠 第三分頁：市場趨勢即時掃描
# ------------------------------------------
with tab3:
    with st.container(border=True):
        st.subheader("📺 市場趨勢即時掃描 (無限自訂 + 智能分流)")
        
        active_etf_list = [f"00{970+i}A.TW" for i in range(28)]
        pools = {
            "🇹🇼 0050 前十大權值股": ["2330.TW", "2454.TW", "2308.TW", "2317.TW", "3711.TW", "2383.TW", "2303.TW", "3037.TW", "2345.TW", "2891.TW"],
            "🇹🇼 熱門高股息 ETF": ["0056.TW", "00878.TW", "00713.TW", "00919.TW", "00929.TW", "00939.TW", "00940.TW"],
            "🇹🇼 半導體與科技主題 ETF": ["00891.TW", "00892.TW", "00881.TW", "00904.TW", "00927.TW", "0052.TW"],
            "🇹🇼 2026 全市場主動式 ETF (28檔)": active_etf_list,
            "🇺🇸 美股科技巨頭與半導體": ["AAPL", "MSFT", "NVDA", "GOOGL", "TSLA", "AMD", "AMZN", "META", "AVGO"],
            "🌍 全球宏觀指標 (金/油/大盤)": ["GC=F", "CL=F", "^TWII", "^GSPC", "^TNX"],
            "✏️ 自訂掃描清單 (無限制)": [] 
        }
        
        name_dict = {
            "2330.TW": "台積電", "2454.TW": "聯發科", "2308.TW": "台達電", "2317.TW": "鴻海", 
            "3711.TW": "日月光投控", "2383.TW": "台光電", "2303.TW": "聯電", "3037.TW": "欣興", 
            "2345.TW": "智邦", "2891.TW": "中信金",
            "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", "00713.TW": "元大台灣高息低波", 
            "00919.TW": "群益台灣精選高息", "00929.TW": "復華台灣科技優息", "00939.TW": "統一台灣高息動能", "00940.TW": "元大台灣價值高息",
            "00891.TW": "中信關鍵半導體", "00892.TW": "富邦台灣半導體", "00881.TW": "國泰台灣5G+", 
            "00904.TW": "新光臺灣半導體30", "00927.TW": "群益半導體收益", "0052.TW": "富邦科技",
            "AAPL": "蘋果", "MSFT": "微軟", "NVDA": "輝達", "GOOGL": "Google", "TSLA": "特斯拉",
            "AMD": "超微", "AMZN": "亞馬遜", "META": "Meta", "AVGO": "博通",
            "GC=F": "黃金期貨 (美元/盎司)", "CL=F": "原油期貨 (WTI)", "^TWII": "台灣加權指數", "^GSPC": "標普500指數", "^TNX": "美國10年期公債殖利率"
        }

        holdings_dict = {
            "2330.TW": "無 (個股)", "2454.TW": "無 (個股)", "2308.TW": "無 (個股)", "2317.TW": "鴻海",
            "3711.TW": "無 (個股)", "2383.TW": "無 (個股)", "2303.TW": "無 (個股)", "3037.TW": "無 (個股)",
            "2345.TW": "無 (個股)", "2891.TW": "無 (個股)",
            "0056.TW": "聯發科, 鴻海, 廣達", "00878.TW": "華碩, 大聯大, 聯發科", "00713.TW": "統一, 台灣大, 遠傳", 
            "00919.TW": "長榮, 聯發科, 瑞昱", "00929.TW": "聯發科, 瑞昱, 聯詠", "00939.TW": "聯發科, 緯創, 大聯大", "00940.TW": "長榮, 聯電, 中美晶",
            "00891.TW": "聯發科, 台積電, 日月光", "00892.TW": "台積電, 聯發科, 聯電", "00881.TW": "台積電, 鴻海, 聯發科", 
            "00904.TW": "台積電, 聯發科, 聯詠", "00927.TW": "聯發科, 台積電, 瑞昱", "0052.TW": "台積電, 聯發科, 鴻海",
            "AAPL": "無 (個股)", "MSFT": "無 (個股)", "NVDA": "無 (個股)", "GOOGL": "無 (個股)", "TSLA": "無 (個股)",
            "AMD": "無 (個股)", "AMZN": "無 (個股)", "META": "無 (個股)", "AVGO": "博通",
            "GC=F": "無 (大宗商品)", "CL=F": "無 (大宗商品)", "^TWII": "無 (大盤指數)", "^GSPC": "無 (大盤指數)", "^TNX": "無 (債券殖利率)"
        }

        for t in active_etf_list:
            name_dict[t] = f"主動型 {t[:6]}"
            holdings_dict[t] = "機密 (經理人動態選股)"

        scan_c1, scan_c2, scan_c3 = st.columns([1.5, 1, 1.5])
        with scan_c1:
            scan_pool_name = st.selectbox("選擇實時運算模組", list(pools.keys()), key="t3_pool")
            
            if scan_pool_name == "✏️ 自訂掃描清單 (無限制)":
                custom_tickers_input = st.text_input("輸入標的代碼 (逗號分隔，台股建議加 .TW)", "2330.TW, GC=F, AAPL, NVDA", key="t3_custom")
                tickers_to_fetch = [t.strip().upper() for t in custom_tickers_input.split(",") if t.strip()]
            else:
                tickers_to_fetch = pools[scan_pool_name]
                
        with scan_c2:
            scan_source = st.radio("底層 API 路由策略", ["自動 (台股FinMind/其他Yahoo)", "強制 Yahoo", "強制 FinMind"], key="t3_src")
            
            total_tickers = len(tickers_to_fetch)
            if total_tickers <= 5:
                count_options = ["顯示全部 (1~5檔)", 3]
            elif total_tickers <= 10:
                count_options = [f"顯示全部 ({total_tickers}檔)", 3, 5]
            else:
                count_options = [f"顯示全部 ({total_tickers}檔)", 3, 5, 10, 20]
                
            scan_count = st.selectbox("顯示結果數量", count_options, key="t3_cnt")
            
        with scan_c3:
            scan_strategy = st.selectbox("即時排序策略", ["依 今年來漲幅(%) 由高到低", "依 當前 RSI 由高到低 (動能強)", "依 當前 RSI 由低到高 (超跌區)"], key="t3_strat")
            
        t3_button = st.button("🚀 啟動全網大掃描", use_container_width=True, key="t3_btn")

    if t3_button:
        if not tickers_to_fetch:
            st.warning("請輸入至少一檔股票或指標代碼。")
            st.stop()
            
        progress_bar = st.progress(0, text="準備連線抓取資料...")
        scan_results = []
        
        current_year = datetime.date.today().year
        end_date_str = datetime.date.today().strftime("%Y-%m-%d")
        fetch_start_date = (datetime.date(current_year, 1, 1) - datetime.timedelta(days=45)).strftime("%Y-%m-%d")

        for i, ticker in enumerate(tickers_to_fetch):
            progress_bar.progress((i + 1) / len(tickers_to_fetch), text=f"正在分析 {name_dict.get(ticker, ticker)}...")
            
            is_tw_stock = ticker.endswith(".TW") or ticker.endswith(".TWO") or (ticker.isdigit() and len(ticker) >= 4)
            use_fm = False
            
            if scan_source == "自動 (台股FinMind/其他Yahoo)": use_fm = is_tw_stock
            elif scan_source == "強制 FinMind": use_fm = True
                
            try:
                stock_data = pd.DataFrame()
                
                if use_fm:
                    fm_id = ticker.replace(".TW", "").replace(".TWO", "")
                    fm_df = fm_api.taiwan_stock_daily(stock_id=fm_id, start_date=fetch_start_date, end_date=end_date_str)
                    if not fm_df.empty and len(fm_df) > 15:
                        fm_df = fm_df.rename(columns={'date': 'Date', 'close': 'Close'})
                        fm_df['Date'] = pd.to_datetime(fm_df['Date'])
                        stock_data = fm_df.set_index('Date')
                else:
                    stock_data = yf.Ticker(ticker).history(start=fetch_start_date, end=end_date_str, auto_adjust=True)
                
                if not stock_data.empty and len(stock_data) > 15:
                    if stock_data.index.tz is not None: stock_data.index = stock_data.index.tz_localize(None)
                        
                    current_price = stock_data['Close'].iloc[-1]
                    ytd_data = stock_data[stock_data.index.year == current_year]
                    ytd_return = ((current_price - ytd_data['Close'].iloc[0]) / ytd_data['Close'].iloc[0]) * 100 if not ytd_data.empty else 0.0

                    delta = stock_data['Close'].diff()
                    gain = delta.where(delta > 0, 0)
                    loss = -delta.where(delta < 0, 0)
                    avg_gain = gain.ewm(com=13, adjust=False).mean()
                    avg_loss = loss.ewm(com=13, adjust=False).mean()
                    rs = avg_gain / avg_loss
                    current_rsi = (np.where(avg_loss == 0, 100, 100 - (100 / (1 + rs))))[-1]
                    
                    if is_tw_stock: flag = "🇹🇼 "
                    elif ticker in ["GC=F", "CL=F", "^GSPC", "^TNX"]: flag = "🌍 "
                    else: flag = "🇺🇸 "
                    
                    scan_results.append({
                        "代號": ticker, "標的名稱": flag + name_dict.get(ticker, ticker), 
                        "前三大持股 (透視)": holdings_dict.get(ticker, "無資料"),
                        "最新收盤價": round(current_price, 2), "今年來漲幅(%)": round(ytd_return, 2),
                        "當前 RSI": round(current_rsi, 1), "來源": "FinMind" if use_fm else "Yahoo"
                    })
            except Exception:
                pass 
        
        progress_bar.empty()
        
        if len(scan_results) > 0:
            df_results = pd.DataFrame(scan_results)
            
            if "今年來漲幅" in scan_strategy: df_results = df_results.sort_values(by="今年來漲幅(%)", ascending=False)
            elif "RSI 由高到低" in scan_strategy: df_results = df_results.sort_values(by="當前 RSI", ascending=False)
            elif "RSI 由低到高" in scan_strategy: df_results = df_results.sort_values(by="當前 RSI", ascending=True)
                
            if not scan_count.startswith("顯示全部"): 
                df_results = df_results.head(int(scan_count))
                
            display_df = df_results.reset_index(drop=True)
            display_df.index = display_df.index + 1
            
            st.success(f"✅ 掃描完成！共成功抓取 {len(scan_results)} 筆即時市場數據。")
            st.dataframe(display_df, use_container_width=True, column_config={
                "最新收盤價": st.column_config.NumberColumn("收盤報價", format="%.2f"),
                "今年來漲幅(%)": st.column_config.NumberColumn("今年漲幅(%)", format="%.2f %%"),
                "當前 RSI": st.column_config.ProgressColumn("短期動能 (RSI)", format="%.1f", min_value=0, max_value=100)
            })
        else:
            st.error("❌ 獲取資料失敗。可能是 API 連線限制或輸入的代碼無效。")
