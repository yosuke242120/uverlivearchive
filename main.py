import streamlit as st
import pandas as pd
import plotly.express as px
import database as db

# 1. ページ設定
st.set_page_config(page_title="UVERworld Live Archive", layout="wide")

# 2. デザインカスタマイズ (ネオン・ダークモード)
st.markdown("""
    <style>
    /* 全体の背景 */
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    /* タイトルのネオン効果 */
    h1 {
        text-shadow: 0 0 10px #00FF00, 0 0 20px #00FF00;
        color: #00FF00 !important;
        font-family: 'Courier New', Courier, monospace;
    }
    /* サブヘッダー */
    h2, h3 {
        color: #00FFFF !important;
        border-bottom: 1px solid #333;
    }
    /* タブのスタイル調整 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #888;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #00FF00;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #00FF00;
    }
    /* ボタンをUVERっぽく */
    .stButton>button {
        background-color: #00FF00;
        color: black;
        font-weight: bold;
        border-radius: 20px;
        border: none;
        box-shadow: 0 0 5px #00FF00;
    }
    .stButton>button:hover {
        background-color: #00CC00;
        box-shadow: 0 0 15px #00FF00;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 認証機能 ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔐 Crew's Entry")
        pw = st.text_input("Crewの証（パスワード）を入力せよ", type="password")
        
        try:
            target_password = st.secrets["password"]
        except:
            target_password = "crew"

        if pw == target_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            if pw: st.error("まだ核心を突けていない（パスワードが違うよ）")
            return False
    return True

if check_password():
    # データ読み込み
    with st.spinner("🎸 THIS IS ONLY THE BEGINNING..."):
        db.init_db()
        counts, all_songs_clean = db.get_stats()

    st.title("🎸 UVERworld Live Archive")

    # --- ダッシュボード（Ø choir 達成度ゲージ） ---
    total_songs = len(all_songs_clean)
    played_count = len(counts)
    completion_rate = (played_count / total_songs) * 100 if total_songs > 0 else 0

    st.markdown(f"### 🔥 Crew Completion Rate: {completion_rate:.1f}%")
    st.progress(completion_rate / 100)
    st.write(f"全 {total_songs} 曲中 {played_count} 曲を回収。真のCrewまであと {total_songs - played_count} 曲。")
    
    if completion_rate >= 100:
        st.balloons()
        st.success("Congratulations! You are the Real Crew!")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["💿 Discography", "📝 Live Records", "📊 Analytics"])

    # --- Tab 1: 楽曲一覧 ---
    with tab1:
        st.header("アルバム・シングル一覧")
        albums_df = db.get_albums()
        selected_album = st.selectbox("盤を選択", albums_df['Disc_Title'].tolist())
        
        if selected_album:
            songs = db.get_songs_by_album(selected_album)
            st.dataframe(songs, use_container_width=True)
        
        st.divider()
        st.subheader("🆕 新曲・未発表曲を追加")
        with st.form("add_song_form"):
            new_album = st.text_input("アルバム名/シングル名")
            new_song = st.text_input("曲名")
            new_type = st.selectbox("種別", ["Album", "Single", "Other"])
            if st.form_submit_button("スプシに登録"):
                if new_album and new_song:
                    db.add_custom_song(new_album, new_song, new_type)
                    st.success(f"🔥 『{new_song}』をスプシに刻んだぜ！")
                    st.rerun()

    # --- Tab 2: ライブ記録 ---
    with tab2:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("ライブ登録")
            l_date = st.date_input("ライブの日付")
            l_title = st.text_input("ライブ名 (例: Premium Live at Zepp)")
            
            all_song_names = db.get_all_song_names()
            selected_songs = st.multiselect("セットリストを選択", all_song_names)
            
            st.caption("テキスト一括入力（1行1曲）")
            text_songs = st.text_area("コピペエリア")
            
            if st.button("🔥 IT'S GONNA BE ALL RIGHT! (保存)"):
                final_list = selected_songs
                if text_songs:
                    final_list = [s.strip() for s in text_songs.split('\n') if s.strip()]
                
                if l_title and final_list:
                    db.add_live(str(l_date), l_title, final_list)
                    st.success("歴史がまた1ページ更新された。")
                    st.rerun()

        with col2:
            st.subheader("参戦履歴")
            lives = db.get_lives()
            if not lives.empty:
                lives = lives.sort_values('date', ascending=False)
                for _, row in lives.iterrows():
                    with st.expander(f"📅 {row['date']} - {row['title']}"):
                        # 簡易的にセトリを表示
                        st.write("このライブの情熱はスプシに保存されている！")
            else:
                st.info("まだ歴史が始まってないぜ。")

    # --- Tab 3: 分析（アルバムカラー連動） ---
    with tab3:
        st.header("📈 参戦統計レポート")
        
        if not counts.empty:
            # グラフ作成
            fig = px.bar(counts.head(20), 
                         x='song_name', y='count', 
                         title="ライブ演奏回数 TOP 20",
                         color='count', 
                         color_continuous_scale='Viridis') # ネオンっぽい色

            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color="white"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 未履修リスト
            st.subheader("😱 まだ生で聴けていない未履修曲")
            played_songs = counts['song_name'].tolist()
            unplayed = [s for s in all_songs_clean['clean_name'].tolist() if s not in played_songs]
            
            if unplayed:
                st.warning(f"残り {len(unplayed)} 曲！")
                st.write(", ".join(unplayed))
            else:
                st.balloons()
                st.success("全曲コンプリート！お前が真のCrewだ！！")
        else:
            st.info("記録を増やして、自分だけのグラフを完成させよう！")