# src/ui/pages/1_Dashboard.py
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Arbitrage Dashboard")

# Real-time metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Profit", "12.45 ETH", delta="+2.1 ETH")

with col2:
    st.metric("24h Profit", "0.85 ETH", delta="-0.2 ETH")

with col3:
    st.metric("Success Rate", "94.2%", delta="+2.3%")

with col4:
    st.metric("Active Opportunities", "3", delta="+1")

# Price comparison chart
st.subheader("Price Comparison: Curve vs Balancer")

# Create comparison chart
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=list(range(100)),
    y=[1.02 + (i*0.0005) for i in range(100)],
    mode='lines',
    name='Curve Rate',
    line=dict(color='#00ff88', width=2)
))

fig.add_trace(go.Scatter(
    x=list(range(100)),
    y=[1.00 + (i*0.0003) for i in range(100)],
    mode='lines',
    name='Balancer Rate',
    line=dict(color='#ff00ff', width=2)
))

fig.update_layout(
    title="Exchange Rates (WETH → WBTC)",
    xaxis_title="Time",
    yaxis_title="Rate",
    hovermode='x unified',
    template='plotly_dark'
)

st.plotly_chart(fig, use_container_width=True)

# Arbitrage opportunities table
st.subheader("Current Arbitrage Opportunities")

opportunities_data = {
    "Pool Pair": ["Curve→Balancer", "Balancer→Curve", "Uniswap→Curve"],
    "Expected Profit": ["0.12 ETH", "0.08 ETH", "0.05 ETH"],
    "Flash Loan Size": ["1500 ETH", "1500 ETH", "1500 ETH"],
    "Gas Cost": ["0.02 ETH", "0.02 ETH", "0.03 ETH"],
    "Status": ["✅ Profitable", "⚠️ Low Profit", "❌ Not Profitable"]
}

df = pd.DataFrame(opportunities_data)
st.dataframe(df, use_container_width=True)
