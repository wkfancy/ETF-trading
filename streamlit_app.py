import streamlit as st
import pandas as pd
import akshare as ak
import requests
import re

# 设置页面配置
st.set_page_config(page_title="ETF量化决策站", layout="wide")

st.title("📈 ETF 高抛低吸量化决策站")
st.markdown("---")

# --- 侧边栏：历史记录 ---
if 'history' not in st.session_state:
    st.session_state['history'] = []

st.sidebar.header("🕒 历史查询")
for h_code in st.session_state['history']:
    if st.sidebar.button(f"查看 {h_code}", key=h_code):
        st.session_state['current_code'] = h_code

# --- 主界面：输入区 ---
default_code = st.session_state.get('current_code', "510300")
col1, col2 = st.columns([2, 1])

with col1:
    target_code = st.text_input("请输入 ETF 代码 (如 510300, 159915):", value=default_code)

# --- 核心数据获取与计算 ---
def get_data(symbol):
    # 1. 实时价 (新浪)
    prefix = "sh" if symbol.startswith('5') else "sz"
    headers = {'Referer': 'http://finance.sina.com.cn'}
    resp = requests.get(f"http://hq.sinajs.cn/list={prefix}{symbol}", headers=headers, timeout=5)
    raw = re.search(r'"(.*)"', resp.content.decode('gbk')).group(1).split(',')
    name, now_price = raw[0], float(raw[3])
    
    # 2. 历史指标 (EM)
    df = ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date="20241201", adjust="")
    df.columns = ['date','open','close','high','low','vol','amt','pct','chg','turn']
    
    ma20 = df['close'].rolling(window=20).mean().iloc[-1]
    std20 = df['close'].rolling(window=20).std().iloc[-1]
    upper = ma20 + 2 * std20
    lower = ma20 - 2 * std20
    
    return name, now_price, upper, lower, ma20

if st.button("开始分析"):
    if target_code not in st.session_state['history']:
        st.session_state['history'].append(target_code)
    
    try:
        name, now, upper, lower, ma20 = get_data(target_code)
        
        # --- 策略点位计算 ---
        # 卖点分档
        sell_1 = upper * 0.995  # 保守
        sell_2 = upper          # 标准
        sell_3 = upper * 1.015  # 激进（冲高）
        
        # 买点分档
        buy_1 = lower * 1.005   # 试探
        buy_2 = lower           # 标准
        
        # --- 页面渲染 ---
        st.subheader(f"🔍 分析标的：{name} ({target_code})")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("当前实时价", f"{now:.3f}")
        m2.metric("布林上轨 (强压力)", f"{upper:.3f}")
        m3.metric("布林下轨 (强支撑)", f"{lower:.3f}")

        st.markdown("### 🎯 阶梯卖出点位建议 (高抛)")
        c1, c2, c3 = st.columns(3)
        c1.error(f"第一档(30%仓): {sell_1:.3f}")
        c2.error(f"第二档(50%仓): {sell_2:.3f}")
        c3.error(f"第三档(清仓位): {sell_3:.3f}")

        st.markdown("### 🛒 阶梯买入点位建议 (低吸)")
        b1, b2 = st.columns(2)
        b1.success(f"第一档(试探): {buy_1:.3f}")
        b2.success(f"第二档(重仓): {buy_2:.3f}")

        # 核心决策提示
        if now >= sell_1:
            st.warning("⚠️ 提示：价格进入卖出区间，建议执行分批止盈策略。")
        elif now <= buy_1:
            st.success("✅ 提示：价格进入买入区间，安全边际较高。")
        else:
            st.info("⌛ 提示：目前价格处于震荡区间中轴，建议持仓耐心等待。")

    except Exception as e:
        st.error(f"分析出错：{e}。可能是请求频繁，请稍后再试。")