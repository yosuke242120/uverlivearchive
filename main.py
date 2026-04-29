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
    </style>
    """, unsafe_allow_html=True)

# 3. データキャッシュ
@st.cache_data(ttl=600)
def get_cached_all_song_names(): return db.get_all_song_names()
@st.cache_data(ttl=600)
def get_cached_albums(): return db.get_albums()
@st.cache_data(ttl=600)
def get_cached_stats(): return db.get_stats()
@st.cache_data(ttl=600)
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
    
    # 達成度表示
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
            lives = get_cached_lives()
            if not lives.empty:
                for _, row in lives.sort_values('date', ascending=False).iterrows():
                    with st.expander(f"📅 {row['date']} - {row['title']}"):
                        if st.button("🗑️ 削除", key=f"del_{row['date']}_{row['title']}"):
                            db.delete_live(row['date'], row['title'])
                            st.cache_data.clear()
                            st.rerun()

    with tab3:
        st.header("統計")
        if not counts.empty:
            fig = px.bar(counts.head(20), x='song_name', y='count', color='count', color_continuous_scale='Viridis')
            st.plotly_chart(fig, use_container_width=True)