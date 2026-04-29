import streamlit as st
import pandas as pd
import plotly.express as px
import database as db

st.set_page_config(page_title="UVERworld Live Archive", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    h1 { text-shadow: 0 0 10px #00FF00, 0 0 20px #00FF00; color: #00FF00 !important; font-family: 'Courier New', Courier, monospace; }
    h2, h3 { color: #00FFFF !important; border-bottom: 1px solid #333; }
    .stButton>button { background-color: #00FF00; color: black; font-weight: bold; border-radius: 20px; box-shadow: 0 0 5px #00FF00; }
    .unplayed-item { font-size: 0.9rem; color: #CCCCCC; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_cached_all_song_names(): return db.get_all_song_names()
@st.cache_data(ttl=3600)
def get_cached_albums(): return db.get_albums()
@st.cache_data(ttl=3600)
def get_cached_stats(): return db.get_stats()
@st.cache_data(ttl=3600)
def get_cached_lives(): return db.get_lives()

if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 Crew's Entry")
    pw = st.text_input("Crewの証", type="password")
    if pw == st.secrets.get("password", "crew"):
        st.session_state.authenticated = True
        st.rerun()
else:
    # 起動時のチェックをキャッシュ化して負荷軽減
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
        selected = st.selectbox("盤を選択", albums['Disc_Title'].tolist() if not albums.empty else [])
        if selected: st.dataframe(db.get_songs_by_album(selected), use_container_width=True)
        
        with st.form("add_song"):
            st.subheader("🆕 新曲を追加")
            n_album, n_song = st.text_input("アルバム名"), st.text_input("曲名")
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
            
            # 並び替えの状態保持
            if "sort_list" not in st.session_state or set(st.session_state.sort_list) != set(sel_songs):
                st.session_state.sort_list = list(sel_songs)

            if len(sel_songs) >= 2:
                with st.expander("🔄 曲順を入れ替える"):
                    for i in range(len(st.session_state.sort_list)):
                        song = st.session_state.sort_list[i]
                        new_pos = st.number_input(f"{song}", 1, len(sel_songs), i+1, key=f"s_{song}_{i}")
                        if new_pos != i + 1:
                            st.session_state.sort_list.pop(i)
                            st.session_state.sort_list.insert(new_pos - 1, song)
                            st.rerun()

            if st.session_state.sort_list:
                st.markdown("---")
                for i, s in enumerate(st.session_state.sort_list): st.text(f"{i+1}. {s}")

            if st.button("🔥 歴史を保存"):
                if l_title and st.session_state.sort_list:
                    db.add_live(str(l_date), l_title, st.session_state.sort_list)
                    st.cache_data.clear()
                    st.success("保存完了！")
                    st.rerun()

        with col2:
            st.subheader("参戦履歴")
            lives_df = get_cached_lives()
            if not lives_df.empty:
                for _, row in lives_df.sort_values('date', ascending=False).iterrows():
                    with st.expander(f"📅 {row['date']} - {row['title']}"):
                        current_setlist = db.get_setlist_by_live(row['date'], row['title'])
                        for i, s in enumerate(current_setlist): st.write(f"{i+1}. {s}")
                        st.divider()
                        if st.button("🗑️ 削除", key=f"del_{row['date']}_{row['title']}"):
                            db.delete_live(row['date'], row['title'])
                            st.cache_data.clear()
                            st.rerun()

    with tab3:
        st.header("📈 統計レポート")
        if not counts.empty:
            st.plotly_chart(px.bar(counts.head(20), x='song_name', y='count', color='count', color_continuous_scale='Viridis'), use_container_width=True)
            st.dataframe(counts.head(30).rename(columns={'song_name': '曲名', 'count': '回数'}), use_container_width=True, hide_index=True)
            st.divider()
            played_songs = counts['song_name'].tolist()
            unplayed = sorted([s for s in all_songs_clean['clean_name'].tolist() if s not in played_songs], key=str.lower)
            st.warning(f"残り {len(unplayed)} 曲！")
            if unplayed:
                cols = st.columns(5)
                for i, song in enumerate(unplayed): cols[i % 5].markdown(f"<div class='unplayed-item'>▫️ {song}</div>", unsafe_allow_html=True)