import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import streamlit as st
import re

# スプシへの接続設定
def get_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # クラウド(Secrets)優先、なければローカルのJSON
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        
    client = gspread.authorize(creds)
    # スプレッドシート名（Google Sheetsのファイル名と一致させる）
    return client.open("UVERworld_Live_Archive")

def init_db(csv_path='UVERworld_Discography_V2.csv'):
    sh = get_spreadsheet()
    s_sheet = sh.worksheet("songs")
    
    # ヘッダーを含め2行以上あれば初期化済みとみなす
    if len(s_sheet.get_all_values()) > 1:
        return

    # 初回のCSV投入
    if hasattr(st, "spinner"): # main.py側でspinnerを使っている場合への配慮
        df = pd.read_csv(csv_path)
        # スプシに書き込む形式（リストのリスト）に変換
        data = [df.columns.values.tolist()] + df.values.tolist()
        s_sheet.update('A1', data)

def get_all_song_names():
    sh = get_spreadsheet()
    df = pd.DataFrame(sh.worksheet("songs").get_all_records())
    # 曲名から(SINGLE ver.)等を除去してユニークなリストを作る
    # 正規表現で (SINGLE ver.) や (Album ver.) を消す
    df['clean_name'] = df['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    return sorted(df['clean_name'].unique().tolist())

def get_albums():
    sh = get_spreadsheet()
    df = pd.DataFrame(sh.worksheet("songs").get_all_records())
    # 盤タイトルとタイプで重複排除
    return df[['Disc_Title', 'Type']].drop_duplicates()

def get_songs_by_album(album_title):
    sh = get_spreadsheet()
    df = pd.DataFrame(sh.worksheet("songs").get_all_records())
    # 選択されたアルバムに紐づく曲名を返す
    return df[df['Disc_Title'] == album_title][['Song_Name']]

def add_live(date, title, song_names):
    sh = get_spreadsheet()
    l_sheet = sh.worksheet("lives")
    set_sheet = sh.worksheet("setlists")
    
    # livesシートに基本情報を追加 (日付, ライブ名)
    l_sheet.append_row([str(date), title])
    
    # setlistsシートに1曲ずつ追加 (日付, ライブ名, 曲名)
    # ※後で分析しやすいように日付とタイトルもセットで入れる
    rows = [[str(date), title, sn] for sn in song_names]
    set_sheet.append_rows(rows)

def get_lives():
    sh = get_spreadsheet()
    data = sh.worksheet("lives").get_all_records()
    return pd.DataFrame(data)

def get_stats():
    sh = get_spreadsheet()
    # setlistsシートから履歴取得
    set_data = sh.worksheet("setlists").get_all_records()
    setlists = pd.DataFrame(set_data)
    
    # songsシートから全曲リスト取得
    song_data = sh.worksheet("songs").get_all_records()
    all_songs = pd.DataFrame(song_data)
    
    # 集計用に曲名をクリーンアップ
    all_songs['clean_name'] = all_songs['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    
    if setlists.empty:
        return pd.DataFrame(columns=['song_name', 'count']), all_songs[['clean_name']].drop_duplicates()
        
    # セットリスト内の曲名もクリーンアップして集計
    setlists['clean_name'] = setlists['Song_Name'].apply(lambda x: re.sub(r' \(SINGLE ver.\)| \(Album ver.\)', '', str(x)).strip())
    counts = setlists['clean_name'].value_counts().reset_index()
    counts.columns = ['song_name', 'count']
    
    return counts, all_songs[['clean_name']].drop_duplicates()

# --- これが追加分！新曲をスプシに書き込む関数 ---
def add_custom_song(album_title, song_name, disc_type='Album'):
    sh = get_spreadsheet()
    s_sheet = sh.worksheet("songs")
    
    # スプシの「songs」シートの末尾に1行追加
    # CSVの並びに合わせて [Type, Disc_Title, Song_Name]
    s_sheet.append_row([disc_type, album_title, song_name])