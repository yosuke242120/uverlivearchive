import streamlit as st
import pandas as pd
import plotly.express as px
import database as db

# 1. ページ設定
st.set_page_config(page_title="UVERworld Live Archive", layout="wide")

# 2. デザインカスタマイズ
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    h1 { text-shadow: 0 0 10px #00FF00, 0 0 20px #00FF00; color: #00FF00 !important; font-family: 'Courier New', Courier, monospace; }
    h2, h3 { color: #00FFFF !important; border-bottom: 1px solid #333; }
    .stButton>button { background-color: #00FF00; color: black; font-weight: bold; border-radius: 20px; box-shadow: 0 0 5px #00FF00; }
    .unplayed-card { background-color: #1E2127; border-radius: 10px; padding: 15px; border-left: 5px solid #FF4B4B; }
    </style>
    """, unsafe_allow_html=True)

# 3. データのキャッシュ
@st.cache_data(ttl=3600)
def get_cached_all_song_names(): return db.get_all_song_names()
@st.cache_data(ttl=3600)
def get_cached_albums(): return db.get_albums()
@st.cache_data(ttl=3600)
def get_cached_stats(): return db.get_stats()
@st.cache_data(ttl=3600)
def get_cached_lives(): return db.get_lives()

def check_password():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔐 Crew's Entry")
        pw = st.text_input("Crewの証（パスワード）", type="password")
        if pw == st.secrets.get("password", "crew"):
            st.session_state.authenticated = True
            st.rerun()
        return False
    return True

if check_password():
    with st.spinner("🎸 THIS IS ONLY THE BEGINNING..."):
        db.init_db()
        counts, all_songs_clean = get_cached_stats()

    st.title("🎸 UVERworld Live Archive")
    
    total = len(all_songs_clean)
    played = len(counts)
    rate = (played / total) * 100 if total > 0 else 0
    st.markdown(f"### 🔥 Crew Completion Rate: {rate:.1f}%")
    st.progress(rate / 100)
    
    tab1, tab2, tab3 = st.tabs(["💿 Discography", "📝 Live Records", "📊 Analytics"])

    with tab1:
        st.header("アルバム一覧")
        albums = get_cached_albums()
        selected = st.selectbox("盤を選択", albums['Disc_Title'].tolist())
        if selected:
            st.dataframe(db.get_songs_by_album(selected), use_container_width=True)
        
        with st.form("add_song"):
            st.subheader("🆕 新曲を追加")
            n_album = st.text_input("アルバム/シングル名")
            n_song = st.text_input("曲名")
            n_type = st.selectbox("種別", ["Album", "Single", "Other"])
            if st.form_submit_button("登録"):
                db.add_custom_song(n_album, n_song, n_type)
                st.cache_data.clear()
                st.rerun()

    with tab2:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("ライブ登録")
            l_date = st.date_input("日付")
            l_title = st.text_input("ライブ名")
            songs_list = get_cached_all_song_names()
            sel_songs = st.multiselect("セトリ選択", songs_list)
            if st.button("🔥 歴史を保存"):
                if l_title and sel_songs:
                    db.add_live(str(l_date), l_title, sel_songs)
                    st.cache_data.clear()
                    st.success("保存完了！")
                    st.rerun()

        with col2:
            st.subheader("参戦履歴")
            lives_df = get_cached_lives()
            if not lives_df.empty and 'date' in lives_df.columns:
                for _, row in lives_df.sort_values('date', ascending=False).iterrows():
                    with st.expander(f"📅 {row['date']} - {row['title']}"):
                        if st.button("🗑️ 削除", key=f"del_{row['date']}_{row['title']}"):
                            db.delete_live(row['date'], row['title'])
                            st.cache_data.clear()
                            st.rerun()
            else:
                st.info("まだ歴史が始まってないぜ。")

    with tab3:
        st.header("📈 統計レポート")
        if not counts.empty:
            # グラフ表示
            fig = px.bar(counts.head(20), x='song_name', y='count', color='count', 
                         color_continuous_scale='Viridis', labels={'song_name': '曲名', 'count': '参戦回数'})
            st.plotly_chart(fig, use_container_width=True)
            
            # --- 修正依頼1: 数字でのランキング表示 ---
            st.subheader("🔢 演奏回数ランキング (Top 30)")
            ranking_df = counts.copy().rename(columns={'song_name': '曲名', 'count': '回数'})
            st.dataframe(ranking_df.head(30), use_container_width=True, hide_index=True)
            
            st.divider()
            
            # --- 修正依頼2: 未履修曲の整理 ---
            st.subheader("😱 未履修曲")
            played_songs = counts['song_name'].tolist()
            unplayed = [s for s in all_songs_clean['clean_name'].tolist() if s not in played_songs]
            
            # 50音順にソート（大文字小文字無視）
            unplayed.sort(key=str.lower)
            
            st.warning(f"残り {len(unplayed)} 曲！")
            
            if unplayed:
                # 1行に5曲ずつ並べる
                cols_count = 5
                for i in range(0, len(unplayed), cols_count):
                    cols = st.columns(cols_count)
                    chunk = unplayed[i:i + cols_count]
                    for idx, song in enumerate(chunk):
                        cols[idx].markdown(f"▫️ {song}")