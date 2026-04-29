import streamlit as st
import pandas as pd
import plotly.express as px
import database as db

# 1. ページ設定
st.set_page_config(page_title="UVERworld Live Archive", layout="wide")

# 2. デザインカスタマイズ (ネオン・ダークモード)
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    h1 { text-shadow: 0 0 10px #00FF00, 0 0 20px #00FF00; color: #00FF00 !important; font-family: 'Courier New', Courier, monospace; }
    h2, h3 { color: #00FFFF !important; border-bottom: 1px solid #333; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #00FF00; }
    .stButton>button { background-color: #00FF00; color: black; font-weight: bold; border-radius: 20px; box-shadow: 0 0 5px #00FF00; }
    </style>
    """, unsafe_allow_html=True)

# 3. データのキャッシュ強化 (ttlを長めに設定)
@st.cache_data(ttl=3600)
def get_cached_all_song_names(): return db.get_all_song_names()

@st.cache_data(ttl=3600)
def get_cached_albums(): return db.get_albums()

@st.cache_data(ttl=3600)
def get_cached_stats(): return db.get_stats()

@st.cache_data(ttl=3600)
def get_cached_lives(): return db.get_lives()

# 認証機能
def check_password():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔐 Crew's Entry")
        pw = st.text_input("Crewの証（パスワード）を入力せよ", type="password")
        target_password = st.secrets.get("password", "crew")
        if pw == target_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            if pw: st.error("まだ核心を突けていない（パスワードが違うよ）")
            return False
    return True

if check_password():
    with st.spinner("🎸 THIS IS ONLY THE BEGINNING..."):
        db.init_db()
        counts, all_songs_clean = get_cached_stats()

    st.title("🎸 UVERworld Live Archive")

    # --- ダッシュボード（達成度ゲージ） ---
    total_songs = len(all_songs_clean)
    played_count = len(counts)
    rate = (played_count / total_songs) * 100 if total_songs > 0 else 0

    st.markdown(f"### 🔥 Crew Completion Rate: {rate:.1f}%")
    st.progress(rate / 100)
    st.write(f"全 {total_songs} 曲中 {played_count} 曲を回収。あと {total_songs - played_count} 曲。")
    
    st.divider()

    tab1, tab2, tab3 = st.tabs(["💿 Discography", "📝 Live Records", "📊 Analytics"])

    # --- Tab 1: 楽曲一覧 ---
    with tab1:
        st.header("アルバム一覧")
        albums_df = get_cached_albums()
        selected_album = st.selectbox("盤を選択", albums_df['Disc_Title'].tolist())
        
        if selected_album:
            songs = db.get_songs_by_album(selected_album)
            st.dataframe(songs, use_container_width=True)
        
        st.divider()
        with st.form("add_song_form"):
            st.subheader("🆕 新曲を追加")
            new_album = st.text_input("アルバム/シングル名")
            new_song = st.text_input("曲名")
            new_type = st.selectbox("種別", ["Album", "Single", "Other"])
            if st.form_submit_button("スプシに登録"):
                if new_album and new_song:
                    db.add_custom_song(new_album, new_song, new_type)
                    st.cache_data.clear() # キャッシュクリア
                    st.success(f"🔥 『{new_song}』を登録したぜ！")
                    st.rerun()

    # --- Tab 2: ライブ記録 ---
    with tab2:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("ライブ登録")
            l_date = st.date_input("日付")
            l_title = st.text_input("ライブ名")
            
            all_song_names = get_cached_all_song_names()
            selected_songs = st.multiselect("セトリを選択", all_song_names)
            
            if st.button("🔥 IT'S GONNA BE ALL RIGHT! (保存)"):
                if l_title and selected_songs:
                    db.add_live(str(l_date), l_title, selected_songs)
                    st.cache_data.clear()
                    st.success("歴史が更新された。")
                    st.rerun()

        with col2:
            st.subheader("参戦履歴")
            lives_df = get_cached_lives()
            if not lives_df.empty:
                for _, row in lives_df.sort_values('date', ascending=False).iterrows():
                    with st.expander(f"📅 {row['date']} - {row['title']}"):
                        if st.button("🗑️ 削除", key=f"del_{row['date']}_{row['title']}"):
                            db.delete_live(row['date'], row['title'])
                            st.cache_data.clear()
                            st.rerun()
            else:
                st.info("まだ歴史が始まってないぜ。")

    # --- Tab 3: 分析 ---
    with tab3:
        st.header("📈 統計レポート")
        if not counts.empty:
            fig = px.bar(counts.head(20), x='song_name', y='count', color='count', color_continuous_scale='Viridis')
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("😱 未履修曲")
            played_songs = counts['song_name'].tolist()
            unplayed = [s for s in all_songs_clean['clean_name'].tolist() if s not in played_songs]
            st.warning(f"残り {len(unplayed)} 曲！")
            st.write(", ".join(unplayed))