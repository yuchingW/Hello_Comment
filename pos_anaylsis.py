from ckiptagger import data_utils, construct_dictionary, WS, POS, NER
import pandas as pd
import warnings
import re
import time
import os
import glob
import ast
from collections import Counter

# ignore warning messages
warnings.filterwarnings("ignore")

# 計算top and reply -> 討論串 -> 技術性互動
def discussion_group(df: pd.DataFrame) -> pd.DataFrame:
    """
    top_comment: 留言串的第一則
    vX_gY: 留言串的回覆
    single: 沒有任何互動的單一留言
    reply: @@user_id的留言
    """
    print(">>> 計算討論串")
    # 建立 video_id（v）從 1 開始
    video_id_map = {title: idx + 1 for idx, title in enumerate(df['video_title'].unique())}
    df['video_id'] = df['video_title'].map(video_id_map)

    # 建立結果列表
    discussion_results = []
    
    # 針對每部影片獨立處理
    for vid in df['video_id'].unique():
        mask = df['video_id'] == vid  # mask是用來抓出特定影片資料
        print(f"=== 處理影片 {vid} ===")
        sub_df = df[mask].reset_index()
        thread_id = 0
        prev_code = ""

        for i in range(len(sub_df)):
            current_row = sub_df.iloc[i].copy()
            current_type = current_row['comment_type']
            next_type = sub_df.iloc[i + 1]['comment_type'] if i + 1 < len(sub_df) else None

            if current_type == 'top_comment' and next_type == 'reply':
                thread_id += 1
                current_row['comment_code'] = f"v{vid}_g{thread_id}"
                prev_code = current_row['comment_code']
            
            elif current_type == 'top_comment' and next_type == 'top_comment':
                current_row['comment_code'] = 'single'
                prev_code = ""
            
            elif current_type == 'reply':
                current_row['comment_code'] = prev_code

            discussion_results.append(current_row)
    
    # 將結果轉換為 DataFrame
    result_df = pd.DataFrame(discussion_results)
    
    # 儲存結果到 CSV
    result_df.to_csv('comments_data/comments/discussion_group.csv', index=False)
    
    return result_df

def count_dc_group(df: pd.DataFrame) -> pd.DataFrame:
    print("-"*20)
    print(">>> 計算互動性")
    result = []

    for vid in df['video_id'].unique():
        sub_df = df[df['video_id'] == vid]
        video_title = sub_df['video_title'].iloc[0]

        # 實質互動留言數：有參與討論串的留言
        interactive_comments = sub_df[sub_df['comment_code'] != 'single'].shape[0]

        # 總留言數
        total_comments = sub_df.shape[0]

        # 討論串數量（互動 group 數）
        num_threads = sub_df[sub_df['comment_code'] != 'single']['comment_code'].nunique()

        # 實質互動比例
        interaction_ratio = interactive_comments / total_comments

        result.append({
            'video_id': vid,
            'video_title': video_title,
            'num_threads': num_threads,
            'total_comments': total_comments,
            'interactive_comments': interactive_comments,
            'interaction_ratio': round(interaction_ratio, 4)
        })

    result_df = pd.DataFrame(result)
    result_df.to_csv('comments_data/comments/discussion_counts.csv', index=False)

    return result_df



def clean_text(comment_data):
    print("-"*20)
    print(">>> 清理留言文字")
    comment_data['cleaned_text'] = None

    for i, c in enumerate(comment_data['comment_text']):
        # print(f"{i+1} / {len(comment_data)}")

        # 移除 HTML 標籤與特殊符號
        c1 = re.sub(r'<br>|<a href=".*?">.*?</a>|<\/?b>', ' ', str(c))
        c2 = re.sub(r'[^\w\s,]', ' ', c1)
        c_cleaned = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5@]', ' ', c2)

        comment_data.at[i, 'cleaned_text'] = c_cleaned
        # print(f"{c} -> {c_cleaned}")
    
    cleaned_data = comment_data.to_csv('comments_data/comments/cleaned_comments.csv', index=False)

    return cleaned_data

def drop_empty_comments_summary(df):
    print("-"*20)
    print(">>> 去除空白留言")
    original = df.groupby('video_title').size()
    # print(">>> 原始留言數量：", original)

    # 去除空留言
    df_cleaned = df.dropna(subset=['cleaned_text'])
    df_cleaned = df_cleaned[df_cleaned['cleaned_text'].str.strip() != '']

    # 留下來的留言數
    after_drop = df_cleaned.groupby('video_title').size()
    # print(">>> 去除空白留言數量：", after_drop)

    # 對齊 index，沒有的補 0
    after_drop = after_drop.reindex(original.index, fill_value=0)

    # 相減：被刪除的筆數
    drop_count = (original - after_drop).reset_index()
    drop_count.columns = ['video_title', 'count']

    # save diff and dropped data to csv
    df_cleaned.to_csv('comments_data/comments/dropped_ckip_comments.csv', index=False)
    drop_count.to_csv('comments_data/dropped_summary.csv', index=False)

    return df_cleaned


def process_ckip(cleaned_data):
    # load ckiptagger files from google drive
    # data_utils.download_data_gdown("./") 

    # load ckiptagger model
    ws = WS("./data")
    pos = POS("./data")
    ner = NER("./data")

    print("-"*20)
    print("開始分析 ckip")
    
    ckip_data = cleaned_data.reset_index(drop=True)

    ckip_data['ws'] = None
    ckip_data['pos'] = None
    ckip_data['ner'] = None

    for i, text in enumerate(ckip_data['cleaned_text']):
        print(f">>> Progressing: {i + 1} / {len(ckip_data)}")
        try:
            if not isinstance(text, str) or text.strip() == '':
                continue

            # CKIP: WS
            try:
                ws_result = ws([text])
                ws_tokens = ws_result[0]
                ckip_data.at[i, 'ws'] = ws_tokens
            except Exception as e:
                print(f"[WS Error] 第{i}行: {e}")
                continue  # 若 WS 錯，無法進行 POS/NER，直接跳過

            # CKIP: POS
            try:
                pos_result = pos([ws_tokens])
                ckip_data.at[i, 'pos'] = pos_result[0]
            except Exception as e:
                print(f"[POS Error] 第{i}行: {e}")

            # CKIP: NER
            try:
                ner_result = ner([ws_tokens], [pos_result[0]])
                ckip_data.at[i, 'ner'] = list(ner_result[0])
            except Exception as e:
                print(f"[NER Error] 第{i}行: {e}")

            time.sleep(0.5)

        except Exception as e:
            print(f"[General Error] 第{i}行發生錯誤: {e}")
            continue

    # 儲存結果
    # ckip_data.to_csv('comments_data/comments/ckip_comments.csv', index=False)
    ckip_data.to_csv('../comments_data/comments/df1_ckip.csv', index=False)
    print("=== CKIP Done, save to df1_ckip.csv")

    return ckip_data



# turn ws, pos, ner into list
def convert_str_columns(df, columns):
    for col in columns:
        df[col] = df[col].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
    return df

def count_Nh(ckip_data):
    print("-"*20)
    print("開始計算 Nh")
    # 初始化欄位
    ckip_data['nh_count'] = None
    ckip_data['first_nh'] = None
    ckip_data['second_nh'] = None
    ckip_data['third_nh'] = None
    ckip_data['other_nh'] = None

    FIRST_PRONOUNS = ['我', '我們']
    SECOND_PRONOUNS = ['你', '妳', '你們', '妳們']
    THIRD_PRONOUNS = ['他', '她', '它', '他們', '她們', '牠們']

    for idx, row in ckip_data.iterrows():
        print(f"\n>>> {idx + 1} / {len(ckip_data)}")
        print("text:", row['cleaned_text'])

        if pd.isna(row['cleaned_text']):
            print(f">>> 第 {idx + 1} 筆資料是 NaN，跳過")
            continue

        pos = row['pos']
        ws = row['ws']

        # initialize count list
        first_list = []
        second_list = []
        third_list = []
        other_list = []

        if not isinstance(pos, list) or not isinstance(ws, list):
            print(f">>> 第 {idx + 1} 筆 pos/ws 不是 list，跳過")
            continue

        if 'Nh' not in pos:
            print(">>> 沒有 Nh，跳過")
            ckip_data.at[idx, 'nh_count'] = 0
            ckip_data.at[idx, 'first_nh'] = []
            ckip_data.at[idx, 'second_nh'] = []
            ckip_data.at[idx, 'third_nh'] = []
            ckip_data.at[idx, 'other_nh'] = []
            continue

        nh_indices = [i for i, p in enumerate(pos) if p == 'Nh']
        nh_words = [ws[i] for i in nh_indices]

        # 統計每個 Nh 詞的出現次數
        nh_counts = Counter(nh_words)

        for i in nh_indices:
            word = ws[i]
            pair = (word, 'Nh', nh_counts[word])  # 加入 count

            if word in FIRST_PRONOUNS:
                first_list.append(pair)
                print(">>> 第一人稱:", pair)
            elif word in SECOND_PRONOUNS:
                second_list.append(pair)
                print(">>> 第二人稱:", pair)
            elif word in THIRD_PRONOUNS:
                third_list.append(pair)
                print(">>> 第三人稱:", pair)
            else:
                other_list.append(pair)
                print(">>> Nh 但不是人稱代名詞:", pair)

        # 寫入欄位
        ckip_data.at[idx, 'nh_count'] = len(nh_indices)
        ckip_data.at[idx, 'first_nh'] = first_list
        ckip_data.at[idx, 'second_nh'] = second_list
        ckip_data.at[idx, 'third_nh'] = third_list
        ckip_data.at[idx, 'other_nh'] = other_list

    ckip_data.to_csv('comments_data/comments/nh_comments_count.csv', index=False)

    return ckip_data

def count_adj(ckip_data):
    print("-" *100)
    print(">>> 計算形容詞")

    ckip_data['adj_tag'] = None
    ckip_data['adj_count'] = None

    for idx, row in ckip_data.iterrows():
        print(f"\n>>> {idx + 1} / {len(ckip_data)}")
        print("text:", row['cleaned_text'])

        if pd.isna(row['cleaned_text']):
            print(f">>> 第 {idx + 1} 筆資料是 NaN，跳過")
            continue

        pos = row['pos']
        ws = row['ws']

        if 'Nh' not in pos:
            print(">>> 沒有 Nh，跳過")
            ckip_data.at[idx,'adj_count'] = 0
            ckip_data.at[idx, 'adj_tag'] = []
            continue

        adj_indices = [i for i, p in enumerate(pos) if p == 'A']
        adj_words = [ws[i] for i in adj_indices]

        # 統計每個 Nh 詞的出現次數
        adj_count = Counter(adj_words)
        adj_list = []

        for i in adj_indices:
            word = ws[i]
            pair = (word, 'A', adj_count[word]) 
            print(f">>> pair: {pair}")
            adj_list.append(pair)

        # 寫入欄位
        ckip_data.at[idx, 'adj_count'] = f"{len(adj_count)}/{len(row['pos'])}"
        ckip_data.at[idx, 'adj_tag']=adj_list

    ckip_data.to_csv('comments_data/comments/adj_count.csv', index=False)





# 主程式
if __name__ == "__main__":
    # # step 1 count discussion group
    # comment_data = pd.read_csv('comments_data/comments/all_comments.csv')
    # dc_group = discussion_group(comment_data)
    # count_dc_group(dc_group)

    # # step 2 clean text
    # comment_data = clean_text(dc_group)
    # comment_drop = drop_empty_comments_summary(comment_data)
    

    # # step 3 process ckip
    comment_drop = pd.read_csv('../comments_data/comments/df1_cleaned.csv')
    ckip_data = process_ckip(comment_drop)
    print(ckip_data.head(10))


    

