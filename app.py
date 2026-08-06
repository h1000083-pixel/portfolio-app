import streamlit as st
import yfinance as yf
import pandas as pd
import json

# ==========================================
# 1. データ保存・読み込みの機能 (ローカルストレージ風)
# ==========================================
DATA_FILE = "portfolio_data.json"

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data:
                return pd.DataFrame(data)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return pd.DataFrame(columns=["銘柄コード", "企業名", "購入単価", "数量"]) 

def save_data(df):
    try:
        df.to_json(DATA_FILE, orient="records", force_ascii=False)
    except Exception as e:
        st.error(f"データの保存に失敗しました: {e}")

# ==========================================
# 2. アプリの初期設定
# ==========================================
st.set_page_config(page_title="ポートフォリオ管理", layout="wide")
st.title("📈 ポートフォリオ＆配当管理アプリ")

# セッションステートの初期化
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_data()
    # 古いデータに「企業名」カラムがない場合の互換性対応
    if '企業名' not in st.session_state.portfolio.columns:
        st.session_state.portfolio['企業名'] = ""

st.markdown("""
### 銘柄の登録
日本株の場合は4桁の数字（例: `7203`）を入力するだけで自動的に登録可能です。
""")

# ==========================================
# 3. 銘柄の登録フォーム
# ==========================================
with st.form("add_stock"):
    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("銘柄コード (例: 7203)", placeholder="7203").upper()
    with col2:
        buy_price = st.number_input("購入単価（円）", min_value=0.0, format="%.2f", step=10.0)
    with col3:
        quantity = st.number_input("数量（株）", min_value=1, value=100, step=100)
    
    submit = st.form_submit_button("登録")
    if submit and ticker:
        if ticker.isdigit():
            ticker += ".T"
        
        # 登録時に企業名を取得しておく
        company_name = ticker
        try:
            stock_info = yf.Ticker(ticker).info
            company_name = stock_info.get('longName', stock_info.get('shortName', ticker))
        except Exception:
            pass 
            
        new_data = pd.DataFrame([{"銘柄コード": ticker, "企業名": company_name, "購入単価": buy_price, "数量": quantity}])
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_data], ignore_index=True)
        save_data(st.session_state.portfolio)
        st.success(f"{company_name} ({ticker}) を登録・保存しました！")
        st.rerun()

st.divider()

# ==========================================
# 4. ポートフォリオの評価と計算
# ==========================================
if not st.session_state.portfolio.empty:
    st.subheader("現在のポートフォリオ状況")
    
    results = []
    total_investment = 0
    total_current_value = 0
    total_annual_dividend = 0
    
    progress_text = "最新の株価・配当データを取得中..."
    my_bar = st.progress(0, text=progress_text)
    
    total_stocks = len(st.session_state.portfolio)
    
    for index, row in st.session_state.portfolio.iterrows():
        t = row["銘柄コード"]
        buy_p = row["購入単価"]
        qty = row["数量"]
        # 企業名が空の場合はティッカーを使用
        c_name = row.get("企業名", t) 
        if pd.isna(c_name) or c_name == "":
            c_name = t
            
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="1d")
            
            if not hist.empty:
                current_p = hist['Close'].iloc[-1]
                
                info = stock.info
                dividend_per_share = info.get('dividendRate', 0)
                if dividend_per_share is None:
                    dividend_per_share = 0
                
                if c_name == t:
                    c_name = info.get('longName', info.get('shortName', t))
                
                annual_dividend = dividend_per_share * qty
                total_annual_dividend += annual_dividend
                yield_on_cost = (dividend_per_share / buy_p) * 100 if buy_p > 0 else 0
                
                investment_val = buy_p * qty
                current_val = current_p * qty
                profit_loss = current_val - investment_val
                price_change = current_p - buy_p
                
                total_investment += investment_val
                total_current_value += current_val
                
                results.append({
                    "企業名 (銘柄)": f"{c_name} ({t})",
                    "数量": qty,
                    "購入単価": buy_p,
                    "現在株価": current_p,
                    "株価変化": price_change,
                    "1株配当金": dividend_per_share,
                    "年間配当金": annual_dividend,
                    "購入利回り": f"{yield_on_cost:.2f}%",
                    "投資額": investment_val,
                    "評価額": current_val,
                    "損益額": profit_loss
                })
            else:
                st.warning(f"{t} のデータが取得できませんでした。")
        except Exception as e:
             st.warning(f"{t} のデータ取得中にエラーが発生しました。")
             
        my_bar.progress((index + 1) / total_stocks, text=progress_text)
        
    my_bar.empty()

    if results:
        # ==========================================
        # 5. テーブルの表示と色付け
        # ==========================================
        df_results = pd.DataFrame(results)
        
        def color_profit_loss(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return 'color: blue;'
                elif val < 0:
                    return 'color: red;'
            return 'color: black;'

        if hasattr(df_results.style, 'map'):
            styled_df = df_results.style.map(color_profit_loss, subset=['損益額', '株価変化'])
        else:
            styled_df = df_results.style.applymap(color_profit_loss, subset=['損益額', '株価変化'])
            
        styled_df = styled_df.format({
            "購入単価": "{:,.2f}",
            "現在株価": "{:,.2f}",
            "株価変化": "{:,.2f}",
            "1株配当金": "{:,.2f}",
            "年間配当金": "{:,.0f}",
            "投資額": "{:,.0f}",
            "評価額": "{:,.0f}",
            "損益額": "{:,.0f}"
        })
        
        st.dataframe(styled_df, use_container_width=True)
        
        st.divider()
        
        # ==========================================
        # 6. 全体のサマリーを表示
        # ==========================================
        st.subheader("ポートフォリオ合計")
        total_profit_loss = total_current_value - total_investment
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("購入時点の合計金額", f"{total_investment:,.0f} 円")
        col2.metric("現在の合計評価額", f"{total_current_value:,.0f} 円")
        
        total_yield_on_cost = (total_annual_dividend / total_investment) * 100 if total_investment > 0 else 0
        col3.metric("年間配当金予想 (合計)", f"{total_annual_dividend:,.0f} 円", f"利回り {total_yield_on_cost:.2f}%")
        
        pl_color = "blue" if total_profit_loss > 0 else "red" if total_profit_loss < 0 else "black"
        pl_sign = "+" if total_profit_loss > 0 else ""
        pl_percent = (total_profit_loss / total_investment) * 100 if total_investment > 0 else 0
        
        col4.markdown(f"""
        <div style="font-size: 14px; color: #555;">合計損益額</div>
        <div style="font-size: 32px; font-weight: bold; color: {pl_color};">
            {pl_sign}{total_profit_loss:,.0f} 円 <span style="font-size: 18px;">({pl_sign}{pl_percent:.2f}%)</span>
        </div>
        """, unsafe_allow_html=True)
        
    st.divider()
    
    # ==========================================
    # 7. 登録データの直接編集 (企業名・単価・数量)
    # ==========================================
    st.subheader("📝 登録データの直接編集")
    st.markdown("以下の表のセルをクリックすると、**企業名**や**購入単価**、**数量**を手入力で直接修正できます。（※修正内容は自動的に保存されます）")
    
    edited_portfolio = st.data_editor(
        st.session_state.portfolio,
        column_config={
            "銘柄コード": st.column_config.TextColumn("銘柄コード", disabled=True),
            "企業名": st.column_config.TextColumn("企業名 (自由に編集可能)"),
            "購入単価": st.column_config.NumberColumn("購入単価（円）", min_value=0.0, format="%.2f"),
            "数量": st.column_config.NumberColumn("数量（株）", min_value=1, step=1)
        },
        hide_index=True,
        use_container_width=True,
        key="portfolio_editor"
    )
    
    # 変更を検知して保存・再実行
    if not edited_portfolio.equals(st.session_state.portfolio):
        st.session_state.portfolio = edited_portfolio
        save_data(st.session_state.portfolio)
        st.rerun()

    st.divider()
    
    # ==========================================
    # 8. データの削除機能
    # ==========================================
    st.subheader("🗑️ データの削除")
    
    del_col1, del_col2 = st.columns([2, 1])
    
    with del_col1:
        options = []
        for i, row in st.session_state.portfolio.iterrows():
            c_name = row.get("企業名", row["銘柄コード"])
            if pd.isna(c_name) or c_name == "":
                c_name = row["銘柄コード"]
            options.append(f"{i}: {c_name} (単価: {row['購入単価']}円)")
            
        selected_to_delete = st.multiselect(
            "削除する銘柄を選択してください（複数選択可）", 
            options,
            placeholder="ここをクリックして選択"
        )
        
        if st.button("選択した銘柄を削除"):
            if selected_to_delete:
                indices_to_drop = [int(item.split(":")[0]) for item in selected_to_delete]
                st.session_state.portfolio = st.session_state.portfolio.drop(indices_to_drop).reset_index(drop=True)
                save_data(st.session_state.portfolio)
                st.success("選択した銘柄を削除しました。")
                st.rerun()
            else:
                st.warning("削除する銘柄が選択されていません。")

    with del_col2:
        st.write("") 
        st.write("")
        if st.button("全データをクリア（リセット）"):
            st.session_state.portfolio = pd.DataFrame(columns=["銘柄コード", "企業名", "購入単価", "数量"])
            save_data(st.session_state.portfolio)
            st.rerun()

else:
    st.info("銘柄を登録すると、ここにポートフォリオの状況が表示されます。")
