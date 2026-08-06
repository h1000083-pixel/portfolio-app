import streamlit as st
import yfinance as yf
import pandas as pd

# ページ設定
st.set_page_config(page_title="ポートフォリオ管理", layout="wide")
st.title("📈 ポートフォリオ管理アプリ")

# セッションステート（メモリ）にデータフレームを初期化
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["銘柄コード", "購入単価", "数量"])

st.markdown("""
### 銘柄の登録
日本株の場合は4桁の数字（例: `7203`）を入力するだけで自動的に登録可能です。
""")

# 1. 銘柄の登録フォーム
with st.form("add_stock"):
    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("銘柄コード (例: 7203)", placeholder="7203").upper()
    with col2:
        buy_price = st.number_input("購入単価（円）", min_value=0.0, format="%.2f", step=10.0)
    with col3:
        # デフォルト数量を100に設定し、100株単位で調整できるように変更
        quantity = st.number_input("数量（株）", min_value=1, value=100, step=100)
    
    submit = st.form_submit_button("登録")
    if submit and ticker:
        # 数字のみ（例: 7203）が入力された場合、自動的に .T を付与する
        if ticker.isdigit():
            ticker += ".T"
            
        new_data = pd.DataFrame([{"銘柄コード": ticker, "購入単価": buy_price, "数量": quantity}])
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_data], ignore_index=True)
        st.success(f"{ticker} を登録しました！")

st.divider()

# 2. ポートフォリオの評価と計算
if not st.session_state.portfolio.empty:
    st.subheader("現在のポートフォリオ状況")
    
    results = []
    total_investment = 0
    total_current_value = 0
    
    # プログレスバー
    progress_text = "最新の株価データを取得中..."
    my_bar = st.progress(0, text=progress_text)
    
    total_stocks = len(st.session_state.portfolio)
    
    for index, row in st.session_state.portfolio.iterrows():
        t = row["銘柄コード"]
        buy_p = row["購入単価"]
        qty = row["数量"]
        
        try:
            # Yahoo Financeから最新データを取得
            stock = yf.Ticker(t)
            hist = stock.history(period="1d")
            
            if not hist.empty:
                current_p = hist['Close'].iloc[-1]
                
                investment_val = buy_p * qty
                current_val = current_p * qty
                profit_loss = current_val - investment_val
                price_change = current_p - buy_p
                
                total_investment += investment_val
                total_current_value += current_val
                
                results.append({
                    "銘柄": t,
                    "数量": qty,
                    "購入単価": buy_p,
                    "現在株価": current_p,
                    "株価変化": price_change,
                    "投資額": investment_val,
                    "評価額": current_val,
                    "損益額": profit_loss
                })
            else:
                st.warning(f"{t} のデータが取得できませんでした。コードが間違っている可能性があります。")
        except Exception as e:
             st.warning(f"{t} のデータ取得中にエラーが発生しました。")
             
        # プログレスバーの更新
        my_bar.progress((index + 1) / total_stocks, text=progress_text)
        
    my_bar.empty() # データ取得完了後にプログレスバーを消す

    if results:
        # 3. 銘柄ごとの詳細をテーブル表示
        df_results = pd.DataFrame(results)
        
        # プラスなら青、マイナスなら赤にする関数の定義
        def color_profit_loss(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return 'color: blue;'
                elif val < 0:
                    return 'color: red;'
            return 'color: black;'

        # テーブルの書式と色を適用
        if hasattr(df_results.style, 'map'):
            styled_df = df_results.style.map(color_profit_loss, subset=['損益額', '株価変化'])
        else:
            styled_df = df_results.style.applymap(color_profit_loss, subset=['損益額', '株価変化'])
            
        styled_df = styled_df.format({
            "購入単価": "{:,.2f}",
            "現在株価": "{:,.2f}",
            "株価変化": "{:,.2f}",
            "投資額": "{:,.0f}",
            "評価額": "{:,.0f}",
            "損益額": "{:,.0f}"
        })
        
        st.dataframe(styled_df, use_container_width=True)
        
        st.divider()
        
        # 4. 全体のサマリーを表示
        st.subheader("ポートフォリオ合計")
        total_profit_loss = total_current_value - total_investment
        
        col1, col2, col3 = st.columns(3)
        col1.metric("購入時点の合計金額", f"{total_investment:,.0f} 円")
        col2.metric("現在の合計評価額", f"{total_current_value:,.0f} 円")
        
        # 合計の損益もプラスなら青、マイナスなら赤で表示
        pl_color = "blue" if total_profit_loss > 0 else "red" if total_profit_loss < 0 else "black"
        pl_sign = "+" if total_profit_loss > 0 else ""
        pl_percent = (total_profit_loss / total_investment) * 100 if total_investment > 0 else 0
        
        col3.markdown(f"""
        <div style="font-size: 14px; color: #555;">合計損益額</div>
        <div style="font-size: 32px; font-weight: bold; color: {pl_color};">
            {pl_sign}{total_profit_loss:,.0f} 円 <span style="font-size: 18px;">({pl_sign}{pl_percent:.2f}%)</span>
        </div>
        """, unsafe_allow_html=True)
        
    # リセットボタン
    if st.button("全データをクリア"):
        st.session_state.portfolio = pd.DataFrame(columns=["銘柄コード", "購入単価", "数量"])
        st.rerun()

else:
    st.info("銘柄を登録すると、ここにポートフォリオの状況が表示されます。")
