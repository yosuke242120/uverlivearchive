import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import streamlit as st
import re
import time

@st.cache_resource
def get_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    
    client = gspread.authorize(creds)
    for i in range(5): # リトライを5回に増加
        try:
            return client.open("UVERworld_Live_Archive")
        except Exception as e:
            if i == 4: raise e
            time.sleep(3) # 待ち時間を少し長く

@st.cache_data(ttl=3600)
def fetch_all_sheets():
    sh = get_spreadsheet()
    # ここでエラーが出やすいので、個別リトライ
    for i in range(3):
        try:
            return {
                "songs": pd.DataFrame(sh.worksheet("songs").get_all_records()),
                "lives": pd.DataFrame(sh.worksheet("lives").get_all_records()),
                "setlists": pd.DataFrame(sh.worksheet("setlists").get_all_records())
            }
        except:
            time.sleep(2)
    return {"songs": pd.DataFrame(), "lives": pd.DataFrame(), "setlists": pd.DataFrame()}

# 起動時のみ実行。一度成功したら二度と通信しない
@st.cache_data
def init_db(csv_path='UVERworld_Discography_V2.csv'):
    try:
        sh = get_spreadsheet()
        s_sheet = sh.worksheet("songs")
        if len(s_sheet.get_all_values()) <= 1:
            df = pd.read_csv(csv_path)
            data = [df.columns.values.tolist()] + df.values.tolist()
            s_sheet.update('A1', data)
    except:
        pass # 失敗してもアプリを止めない

def get_all_song_names():
    data = fetch_all_sheets()
    df = data["songs"]
    if df.empty: return []
    df['clean_name'] = df['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    return sorted(df['clean_name'].unique().tolist())

def get_albums():
    data = fetch_all_sheets()
    return data["songs"][['Disc_Title', 'Type']].drop_duplicates() if not data["songs"].empty else pd.DataFrame()

def get_songs_by_album(album_title):
    data = fetch_all_sheets()
    df = data["songs"]
    return df[df['Disc_Title'] == album_title][['Song_Name']] if not df.empty else pd.DataFrame()

def get_setlist_by_live(date, title):
    data = fetch_all_sheets()
    df = data["setlists"]
    if df.empty: return []
    target_songs = df[(df['date'].astype(str) == str(date)) & (df['title'] == title)]['Song_Name'].tolist()
    return target_songs

def get_lives():
    return fetch_all_sheets()["lives"]

def get_stats():
    data = fetch_all_sheets()
    setlists, all_songs = data["setlists"], data["songs"]
    if all_songs.empty: return pd.DataFrame(), pd.DataFrame()
    all_songs['clean_name'] = all_songs['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    if setlists.empty: return pd.DataFrame(columns=['song_name', 'count']), all_songs[['clean_name']].drop_duplicates()
    setlists['clean_name'] = setlists['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    counts = setlists['clean_name'].value_counts().reset_index()
    counts.columns = ['song_name', 'count']
    return counts, all_songs[['clean_name']].drop_duplicates()

def add_live(date, title, song_names):
    sh = get_spreadsheet()
    sh.worksheet("lives").append_row([str(date), title])
    sh.worksheet("setlists").append_rows([[str(date), title, sn] for sn in song_names])
    st.cache_data.clear()

def add_custom_song(album_title, song_name, disc_type='Album'):
    get_spreadsheet().worksheet("songs").append_row([disc_type, album_title, song_name])
    st.cache_data.clear()

def delete_live(date, title):
    sh = get_spreadsheet()
    l_sheet, set_sheet = sh.worksheet("lives"), sh.worksheet("setlists")
    l_rows = l_sheet.get_all_values()
    for i, r in enumerate(l_rows):
        if len(r) >= 2 and r[0] == str(date) and r[1] == title:
            l_sheet.delete_rows(i + 1)
            break
    s_rows = set_sheet.get_all_values()
    to_del = [i+1 for i, r in enumerate(s_rows) if len(r) >= 2 and r[0] == str(date) and r[1] == title]
    for idx in reversed(to_del): set_sheet.delete_rows(idx)
    st.cache_data.clear()