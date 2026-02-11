import streamlit as st
import pandas as pd
import akshare as ak
import requests
import re
import datetime

# 页面基础设置
st.set_page_config(page_title="ETF量化决策终端", layout="wide")

st.title("📊 ETF 高抛低吸量化辅助系统")
st.caption("基于布林带与阶梯止盈策略 | 数据源：新浪/东财")

# --- 侧边栏记录 ---
if 'history' not in st.session_state:
    st.session_state['history'] = []

with st.sidebar:
    st.header("🕒 最近查询")
    if not st.session_state['history']:
        st.write("暂无记录")
    for h_code in reversed(st.session_state['history']):
        if st.button(f"📌 {h_code}", key=f"btn_{h_code}"):
            st.session_state['target_code'] = h_code

# --- 主界面布局 ---
default_code = st.session_state.get('target_code', "510300")
target_code = st.text_input("输入 6 位 ETF 代码:", value=default_code, max_chars=6)

@st.cache_data(ttl=60) # 缓存数据 60 秒，防止频繁请求被封
def fetch_etf_data(symbol):
    # 1. 获取实时价 (新浪备用链路)
    prefix = "sh" if symbol.startswith('5') else "sz"
    headers = {'Referer': 'http://finance.sina.com.cn'}
    r = requests.get(f"http://hq.sinajs.cn/list={prefix}{symbol}", headers=headers, timeout=10)
    # 解决编码问题
    content = r.content.decode('gbk')
    raw = re.search(r'"(.*)"', content).group(1).split(',')
    name, now_price = raw[0], float(raw[3])
    
    # 2. 获取历史数据
    df = ak.fund_etf_hist_em(symbol=symbol, period="daily", 
                             start_date=(datetime.datetime.now() - datetime.timedelta(days=60)).strftime('%Y%m%d'),
                             adjust="")
    df.columns = ['日期','开盘','收盘','最高','最低','成交量','成交额','振幅','涨跌幅','涨跌额','换手率']
    
    # 3. 计算指标
    df['MA20'] = df['收盘'].rolling(window=20).mean()
    df['STD'] = df['收盘'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + 2 * df['STD']
    df['Lower'] = df['MA20'] - 2 * df['STD']
    
    return name, now_price, df

if st.button("开始分析", type="primary"):
    if target_code not in st.session_state['history']:
        st.session_state['history'].append(target_code)
        if len(st.session_state['history']) > 10: # 最多存10个
            st.session_state['history'].pop(0)

    try:
        with st.spinner('正在调取量化接口...'):
            name, now, df = fetch_etf_data(target_code)
            
            upper = df['Upper'].iloc[-1]
            lower = df['Lower'].iloc[-1]
            ma20 = df['MA20'].iloc[-1]

            # 策略计算
            sell_1 = upper * 0.995
            sell_2 = upper
            sell_3 = upper * 1.01
            
            buy_1 = lower * 1.005
            buy_2 = lower

            # --- 渲染面板 ---
            st.success(f"### {name} ({target_code})")
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("当前成交价", f"{now:.3f}")
            col_b.metric("布林上轨 (压力)", f"{upper:.3f}")
            col_c.metric("布林下轨 (支撑)", f"{lower:.3f}")

            st.markdown("---")
            
            # 止盈止损建议区
            left, right = st.columns(2)
            
            with left:
                st.error("🔴 阶梯止盈点位 (高抛)")
                st.write(f"1档 (保守): **{sell_1:.3f}**")
                st.write(f"2档 (标准): **{sell_2:.3f}**")
                st.write(f"3档 (激进): **{sell_3:.3f}**")
                
            with right:
                st.success("🟢 阶梯建仓点位 (低吸)")
                st.write(f"1档 (试探): **{buy_1:.3f}**")
                st.write(f"2档 (强撑): **{buy_2:.3f}**")
                st.write(f"趋势中轴线: **{ma20:.3f}**")

            # 可视化图表
            st.line_chart(df.set_index('日期')[['收盘', 'Upper', 'Lower']])

    except Exception as e:
        st.error(f"分析失败: {str(e)}")
        st.info("排查建议: 1. 确认代码正确 2. 稍等5秒再点 3. 检查 GitHub 上的 requirements.txt 是否已修正。")