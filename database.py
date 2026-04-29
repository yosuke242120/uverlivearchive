import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import streamlit as st
import re
import time

# --- 接続のキャッシュ化 & リトライ機能 ---
@st.cache_resource
def get_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    
    client = gspread.authorize(creds)
    
    # API制限対策：エラー時に最大3回リトライ
    for i in range(3):
        try:
            return client.open("UVERworld_Live_Archive")
        except Exception as e:
            if i == 2: raise e
            time.sleep(2)  # 2秒待機して再試行

def init_db(csv_path='UVERworld_Discography_V2.csv'):
    sh = get_spreadsheet()
    s_sheet = sh.worksheet("songs")
    if len(s_sheet.get_all_values()) > 1:
        return
    df = pd.read_csv(csv_path)
    data = [df.columns.values.tolist()] + df.values.tolist()
    s_sheet.update('A1', data)

# --- 読み込み系（一括取得でAPI消費を節約） ---
def get_all_song_names():
    sh = get_spreadsheet()
    rows = sh.worksheet("songs").get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df['clean_name'] = df['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    return sorted(df['clean_name'].unique().tolist())

def get_albums():
    sh = get_spreadsheet()
    rows = sh.worksheet("songs").get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df[['Disc_Title', 'Type']].drop_duplicates()

def get_songs_by_album(album_title):
    sh = get_spreadsheet()
    rows = sh.worksheet("songs").get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df[df['Disc_Title'] == album_title][['Song_Name']]

# --- 書き込み系（append_rowsで通信を1回に集約） ---
def add_live(date, title, song_names):
    sh = get_spreadsheet()
    l_sheet = sh.worksheet("lives")
    set_sheet = sh.worksheet("setlists")
    
    # livesシートに1行追加
    l_sheet.append_row([str(date), title])
    
    # setlistsシートにまとめて追加（これがAPI節約に効く！）
    rows = [[str(date), title, sn] for sn in song_names]
    set_sheet.append_rows(rows)

def get_lives():
    sh = get_spreadsheet()
    sheet = sh.worksheet("lives")
    data = sheet.get_all_records()
    
    if not data:
        # データが1件もない場合は、空のDataFrameを返す（エラー防止）
        return pd.DataFrame(columns=['date', 'title'])
        
    return pd.DataFrame(data)

def get_stats():
    sh = get_spreadsheet()
    set_rows = sh.worksheet("setlists").get_all_values()
    song_rows = sh.worksheet("songs").get_all_values()
    
    setlists = pd.DataFrame(set_rows[1:], columns=set_rows[0]) if len(set_rows) > 1 else pd.DataFrame()
    all_songs = pd.DataFrame(song_rows[1:], columns=song_rows[0])
    
    all_songs['clean_name'] = all_songs['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    
    if setlists.empty:
        return pd.DataFrame(columns=['song_name', 'count']), all_songs[['clean_name']].drop_duplicates()
        
    setlists['clean_name'] = setlists['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    counts = setlists['clean_name'].value_counts().reset_index()
    counts.columns = ['song_name', 'count']
    return counts, all_songs[['clean_name']].drop_duplicates()

def add_custom_song(album_title, song_name, disc_type='Album'):
    sh = get_spreadsheet()
    sh.worksheet("songs").append_row([disc_type, album_title, song_name])

def delete_live(date, title):
    sh = get_spreadsheet()
    l_sheet = sh.worksheet("lives")
    set_sheet = sh.worksheet("setlists")
    
    # lives削除
    lives_rows = l_sheet.get_all_values()
    for i, row in enumerate(lives_rows):
        if len(row) >= 2 and row[0] == str(date) and row[1] == title:
            l_sheet.delete_rows(i + 1)
            break
            
    # setlists削除（逆順に消去）
    set_rows = set_sheet.get_all_values()
    rows_to_del = [i+1 for i, r in enumerate(set_rows) if len(r) >= 2 and r[0] == str(date) and r[1] == title]
    for idx in reversed(rows_to_del):
        set_sheet.delete_rows(idx)