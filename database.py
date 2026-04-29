import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import streamlit as st
import re
import time

# --- 接続のキャッシュ化 ---
@st.cache_resource
def get_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    
    client = gspread.authorize(creds)
    # ここでリトライを入れる
    for i in range(3):
        try:
            return client.open("UVERworld_Live_Archive")
        except Exception as e:
            if i == 2: raise e
            time.sleep(2)

# --- ★全データを一度にキャッシュする関数を追加 ---
@st.cache_data(ttl=3600)
def fetch_all_sheets():
    sh = get_spreadsheet()
    # 全シートを一度に読み込んで辞書に入れる（これが一番通信を減らせる）
    return {
        "songs": pd.DataFrame(sh.worksheet("songs").get_all_records()),
        "lives": pd.DataFrame(sh.worksheet("lives").get_all_records()),
        "setlists": pd.DataFrame(sh.worksheet("setlists").get_all_records())
    }

def init_db(csv_path='UVERworld_Discography_V2.csv'):
    # 初回起動時のみ実行される
    sh = get_spreadsheet()
    s_sheet = sh.worksheet("songs")
    if len(s_sheet.get_all_values()) <= 1:
        df = pd.read_csv(csv_path)
        data = [df.columns.values.tolist()] + df.values.tolist()
        s_sheet.update('A1', data)

# --- 読み込み系（キャッシュを利用するように変更） ---
def get_all_song_names():
    data = fetch_all_sheets()
    df = data["songs"]
    df['clean_name'] = df['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    return sorted(df['clean_name'].unique().tolist())

def get_albums():
    data = fetch_all_sheets()
    df = data["songs"]
    return df[['Disc_Title', 'Type']].drop_duplicates()

def get_songs_by_album(album_title):
    data = fetch_all_sheets()
    df = data["songs"]
    return df[df['Disc_Title'] == album_title][['Song_Name']]

def get_setlist_by_live(date, title):
    data = fetch_all_sheets()
    df = data["setlists"]
    if df.empty: return []
    target_songs = df[(df['date'].astype(str) == str(date)) & (df['title'] == title)]['Song_Name'].tolist()
    return target_songs

def get_lives():
    data = fetch_all_sheets()
    df = data["lives"]
    if df.empty: return pd.DataFrame(columns=['date', 'title'])
    return df

def get_stats():
    data = fetch_all_sheets()
    setlists = data["setlists"]
    all_songs = data["songs"]
    all_songs['clean_name'] = all_songs['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    
    if setlists.empty:
        return pd.DataFrame(columns=['song_name', 'count']), all_songs[['clean_name']].drop_duplicates()
        
    setlists['clean_name'] = setlists['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    counts = setlists['clean_name'].value_counts().reset_index()
    counts.columns = ['song_name', 'count']
    return counts, all_songs[['clean_name']].drop_duplicates()

# --- 書き込み系（書き込み後はキャッシュをクリアする必要がある） ---
def add_live(date, title, song_names):
    sh = get_spreadsheet()
    l_sheet = sh.worksheet("lives")
    set_sheet = sh.worksheet("setlists")
    l_sheet.append_row([str(date), title])
    rows = [[str(date), title, sn] for sn in song_names]
    set_sheet.append_rows(rows)
    st.cache_data.clear() # 書き込んだらキャッシュを消して最新にする

def add_custom_song(album_title, song_name, disc_type='Album'):
    sh = get_spreadsheet()
    sh.worksheet("songs").append_row([disc_type, album_title, song_name])
    st.cache_data.clear()

def delete_live(date, title):
    sh = get_spreadsheet()
    l_sheet = sh.worksheet("lives")
    set_sheet = sh.worksheet("setlists")
    
    lives_rows = l_sheet.get_all_values()
    for i, row in enumerate(lives_rows):
        if len(row) >= 2 and row[0] == str(date) and row[1] == title:
            l_sheet.delete_rows(i + 1)
            break
            
    set_rows = set_sheet.get_all_values()
    rows_to_del = [i+1 for i, r in enumerate(set_rows) if len(r) >= 2 and r[0] == str(date) and r[1] == title]
    for idx in reversed(rows_to_del):
        set_sheet.delete_rows(idx)
    st.cache_data.clear()