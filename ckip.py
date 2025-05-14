# from ckiptagger import data_utils, construct_dictionary, WS, POS, NER
import pandas as pd
import warnings
import re
import time
warnings.filterwarnings("ignore")

def name_list(data):
    data['author_name'] = data['author_name'].apply(lambda x: str(x).replace('@', ''))

    name_set = set()
    name_list = []
    for name in data['author_name']:
        name_str = str(name)
        if name_str in name_set:
            continue
        name_set.add(name_str)
        name_list.append(name_str)
    
    # print(">>> name_list:", name_list)

    return name_list

def clean_text(comment_data, name_list):
    print("-"*20)
    print(">>> 清理留言文字")
    comment_data['cleaned_text'] = None

    for i, c in enumerate(comment_data['comment_text']):
        print(f"{i+1} / {len(comment_data)}")

        # 移除 HTML 標籤、特殊符號、author_name
        c1 = re.sub(r'<br>|<a href=".*?">.*?</a>|<\/?b>', ' ', str(c))
        c2 = re.sub(r'[^\w\s,]', ' ', c1)
        c3 = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]', ' ', c2)

        #name pattern
        pattern = r'\b(?:' + '|'.join(re.escape(name) for name in name_list) + r')\b'
        c_cleaned = re.sub(pattern, '', c3)

        comment_data.at[i, 'cleaned_text'] = c_cleaned
        # print(f"{c} -> {c_cleaned}")
    
    cleaned_data = comment_data.to_csv('comments_data/cleaned_comments.csv', index=False)

    return drop_empty_comments_summary(cleaned_data)


def drop_empty_comments_summary(df):
    print("-"*20)
    print(">>> 資料清洗後去除空白留言")
    original = df.groupby('video_title').size()
    print(">>> 原始留言數量：", len(df))

    # 去除空留言
    df_cleaned = df.dropna(subset=['cleaned_text'])
    df_cleaned = df_cleaned[df_cleaned['cleaned_text'].str.strip() != '']

    # 留下來的留言數
    after_drop = df_cleaned.groupby('video_title').size()
    print("after_drop >> ",after_drop)
    
    # 計算差異值
    diff = original - after_drop
    
    # 整理成指定格式的資料表
    drop_summary = pd.DataFrame({
        'video_title': after_drop.index,
        'comment_count_after_cleaned': after_drop.values,
        'diff': diff.values
    })
    
    print("\n=== 整理後的留言統計表 ===")
    print(drop_summary)
    
    # 儲存整理後的摘要資料
    drop_summary.to_csv('comments_data/drop_summary.csv', index=False)

    # 原來的程式碼繼續執行...
    after_drop['diff'] = original - after_drop
    print(">>> 留言數量差異：", after_drop['diff'])

    # 對齊 index，沒有的補 0
    after_drop = after_drop.reindex(original.index, fill_value=0)
    print(">>> 清理後留言數量：", len(df_cleaned))
    print(">>> 被刪除的留言數量：", len(df) - len(df_cleaned))

    # save diff and dropped data to csv
    df_cleaned.to_csv('comments_data/dropped_ckip_comments.csv', index=False)

    return df_cleaned

# def process_ckip(cleaned_data):
#     # load ckiptagger files from google drive
#     # data_utils.download_data_gdown("./") 

#     # load ckiptagger model
#     ws = WS("./data")
#     pos = POS("./data")
#     ner = NER("./data")

#     print("-"*20)
#     print("開始分析 ckip")
    
#     ckip_data = cleaned_data.reset_index(drop=True)

#     ckip_data['ws'] = None
#     ckip_data['pos'] = None
#     ckip_data['ner'] = None

#     for i, text in enumerate(ckip_data['cleaned_text']):
#         print(f">>> Progressing: {i + 1} / {len(ckip_data)}")
#         try:
#             if not isinstance(text, str) or text.strip() == '':
#                 continue

#             # CKIP: WS
#             try:
#                 ws_result = ws([text])
#                 ws_tokens = ws_result[0]
#                 ckip_data.at[i, 'ws'] = ws_tokens
#             except Exception as e:
#                 print(f"[WS Error] 第{i}行: {e}")
#                 continue  # 若 WS 錯，無法進行 POS/NER，直接跳過

#             # CKIP: POS
#             try:
#                 pos_result = pos([ws_tokens])
#                 ckip_data.at[i, 'pos'] = pos_result[0]
#             except Exception as e:
#                 print(f"[POS Error] 第{i}行: {e}")

#             # CKIP: NER
#             try:
#                 ner_result = ner([ws_tokens], [pos_result[0]])
#                 ckip_data.at[i, 'ner'] = list(ner_result[0])
#             except Exception as e:
#                 print(f"[NER Error] 第{i}行: {e}")

#             time.sleep(0.5)

#         except Exception as e:
#             print(f"[General Error] 第{i}行發生錯誤: {e}")
#             continue

#     # 儲存結果
#     ckip_data.to_csv('comments_data/ckip_comments.csv', index=False)
#     print("=== CKIP Done, save to df1_ckip.csv")

#     return ckip_data


# def remove_stopwords(df):
#     # load stopword.txt
#     with open('stopwords.txt', 'r', encoding='utf-8') as f:
#         stopwords = f.read().splitlines()
#         stopwords = [word.strip() for word in stopwords]
#         print(stopwords)
#     # remove stopwords
#     for i, tokens in enumerate(df['ws']):
#         if isinstance(tokens, list):
#             df.at[i, 'ws_cleaned'] = [t for t in tokens if t.strip() not in stopwords]
#             ws_str = ' '.join(df.at[i, 'ws_cleaned'])
#             df.at[i, 'ws_str'] = ws_str
#         else:
#             df.at[i, 'ws_cleaned'] = tokens
#             df.at[i, 'ws_str'] = tokens

#     # save to csv
#     df.to_csv('comments_data/comments/ws_str_comments.csv', index=False)
#     print("=== Removed stopwords, save to ws_str_comments.csv")
    
#     return df



if __name__ == "__main__":
    # 讀取留言資料
    # df = pd.read_csv('comments_data/all_comments_cleaned.csv', encoding='utf-8')
    # print(df.head(2))

    # # 讀取作者名稱
    # name_data = name_list(df)
    # print(f"總共有 {len(name_data)} 個不重複的留言者")

    # # 清理留言文字、移除空白row
    # df_cleaned = clean_text(df, name_data)
    df_cleaned = pd.read_csv('comments_data/cleaned_comments.csv', encoding='utf-8')
    drop_empty_comments_summary(df_cleaned)

    # # ckip
    # ckip_data = process_ckip(df_cleaned)
    # print(ckip_data.head(2))

    # # remove stopwords
    # cleaned_str = remove_stopwords(ckip_data)
    # print(cleaned_str.head(2))