import streamlit as st
import yfinance as yf
import pandas as pd

# ページ設定
st.set_page_config(page_title="ポートフォリオ＆配当利回り管理", layout="wide")
st.title("📈 ポートフォリオ＆配当利回り（YoC）管理アプリ")

# セッションステート（メモリ）にデータフレームを初期化
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["銘柄コード", "購入単価", "数量"])

st.markdown("""
### 銘柄の登録
日本株の場合は、4桁の証券コードの末尾に `.T` をつけてください。（例：トヨタ自動車 → `7203.T`）
""")

# 1. 銘柄の登録フォーム
with st.form("add_stock"):
    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("銘柄コード (例: 7203.T)", placeholder="7203.T").upper()
    with col2:
        buy_price = st.number_input("購入単価（円/ドル）", min_value=0.0, format="%.2f", step=10.0)
    with col3:
        quantity = st.number_input("数量（株）", min_value=1, step=1)
    
    submit = st.form_submit_button("登録")
    if submit and ticker:
        # 重複チェック（すでに同じ銘柄があれば追加しない、あるいは更新するなどの処理も可能ですが、今回は単純追加）
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
    
    # プログレスバー（データ取得中）
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
            # 過去1日分のデータを取得して最新の終値を参照
            hist = stock.history(period="1d")
            
            if not hist.empty:
                current_p = hist['Close'].iloc[-1]
                
                # 配当利回りの取得（infoから取得できない場合は0）
                info = stock.info
                dividend_yield = info.get('dividendYield', 0)
                if dividend_yield is None: 
                    dividend_yield = 0
                
                # 1株あたりの年間配当金を推計（現在株価 × 現在の配当利回り）
                annual_dividend_per_share = current_p * dividend_yield
                
                # 購入基準の配当利回り (Yield on Cost) を計算
                yield_on_cost = (annual_dividend_per_share / buy_p) * 100 if buy_p > 0 else 0
                
                # 損益と合計金額の計算
                investment_val = buy_p * qty
                current_val = current_p * qty
                
                total_investment += investment_val
                total_current_value += current_val
                
                results.append({
                    "銘柄": t,
                    "数量": qty,
                    "購入単価": f"{buy_p:,.2f}",
                    "現在株価": f"{current_p:,.2f}",
                    "株価変化": f"{(current_p - buy_p):,.2f}",
                    "YoC (購入利回り)": f"{yield_on_cost:.2f}%",
                    "投資額": f"{investment_val:,.2f}",
                    "評価額": f"{current_val:,.2f}",
                    "損益額": f"{(current_val - investment_val):,.2f}"
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
        st.dataframe(df_results, use_container_width=True)
        
        st.divider()
        
        # 4. 全体のサマリーを表示
        st.subheader("ポートフォリオ合計")
        total_profit_loss = total_current_value - total_investment
        
        # 損益がプラスなら赤（または緑）、マイナスなら青にするなどの見せ方も可能
        delta_color = "normal" 
        
        col1, col2, col3 = st.columns(3)
        col1.metric("購入時点の合計金額", f"{total_investment:,.0f} 円")
        col2.metric("現在の合計評価額", f"{total_current_value:,.0f} 円")
        col3.metric("合計損益額", f"{total_profit_loss:,.0f} 円", delta=f"{(total_profit_loss/total_investment)*100:.2f}%" if total_investment > 0 else None)
        
    # リセットボタン
    if st.button("全データをクリア"):
        st.session_state.portfolio = pd.DataFrame(columns=["銘柄コード", "購入単価", "数量"])
        st.rerun()

else:
    st.info("銘柄を登録すると、ここにポートフォリオの状況が表示されます。")
