import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import streamlit as st
import re

# --- 接続のキャッシュ化（最重要！） ---
@st.cache_resource
def get_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    
    client = gspread.authorize(creds)
    # 一度開いたら、そのセッション中は使い回す
    return client.open("UVERworld_Live_Archive")

def init_db(csv_path='UVERworld_Discography_V2.csv'):
    sh = get_spreadsheet()
    s_sheet = sh.worksheet("songs")
    if len(s_sheet.get_all_values()) > 1:
        return
    df = pd.read_csv(csv_path)
    data = [df.columns.values.tolist()] + df.values.tolist()
    s_sheet.update('A1', data)

def get_all_song_names():
    sh = get_spreadsheet()
    df = pd.DataFrame(sh.worksheet("songs").get_all_records())
    df['clean_name'] = df['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    return sorted(df['clean_name'].unique().tolist())

def get_albums():
    sh = get_spreadsheet()
    df = pd.DataFrame(sh.worksheet("songs").get_all_records())
    return df[['Disc_Title', 'Type']].drop_duplicates()

def get_songs_by_album(album_title):
    sh = get_spreadsheet()
    df = pd.DataFrame(sh.worksheet("songs").get_all_records())
    return df[df['Disc_Title'] == album_title][['Song_Name']]

def add_live(date, title, song_names):
    sh = get_spreadsheet()
    l_sheet = sh.worksheet("lives")
    set_sheet = sh.worksheet("setlists")
    l_sheet.append_row([str(date), title])
    rows = [[str(date), title, sn] for sn in song_names]
    set_sheet.append_rows(rows)

def get_lives():
    sh = get_spreadsheet()
    data = sh.worksheet("lives").get_all_records()
    return pd.DataFrame(data)

def get_stats():
    sh = get_spreadsheet()
    set_data = sh.worksheet("setlists").get_all_records()
    setlists = pd.DataFrame(set_data)
    song_data = sh.worksheet("songs").get_all_records()
    all_songs = pd.DataFrame(song_data)
    all_songs['clean_name'] = all_songs['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    if setlists.empty:
        return pd.DataFrame(columns=['song_name', 'count']), all_songs[['clean_name']].drop_duplicates()
    setlists['clean_name'] = setlists['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    counts = setlists['clean_name'].value_counts().reset_index()
    counts.columns = ['song_name', 'count']
    return counts, all_songs[['clean_name']].drop_duplicates()

def add_custom_song(album_title, song_name, disc_type='Album'):
    sh = get_spreadsheet()
    s_sheet = sh.worksheet("songs")
    s_sheet.append_row([disc_type, album_title, song_name])

def delete_live(date, title):
    sh = get_spreadsheet()
    l_sheet = sh.worksheet("lives")
    set_sheet = sh.worksheet("setlists")
    lives_data = l_sheet.get_all_values()
    for i, row in enumerate(lives_data):
        if len(row) >= 2 and row[0] == str(date) and row[1] == title:
            l_sheet.delete_rows(i + 1)
            break
    set_data = set_sheet.get_all_values()
    rows_to_delete = [i + 1 for i, row in enumerate(set_data) if len(row) >= 2 and row[0] == str(date) and row[1] == title]
    for row_idx in reversed(rows_to_delete):
        set_sheet.delete_rows(row_idx)