from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
import numpy as np
import pandas as pd

## 一集一集做
video_id = 0

tag_data = pd.read_csv(f'hello_comments/psudeo_labaling/v{video_id}_tagged.csv')
print(f"tag_data: {len(tag_data)}")

df0 = pd.read_csv(f'hello_comments/spam_tag/video_{video_id}_ckip_spam_tag.csv')
print(f"df0: {len(df0)}")

# 如果comment_text, published_at, author_name都一樣的話，把tag_data的spam_tag欄位合併到df中
df = df0.merge(
    tag_data[['comment_text', 'published_at', 'author_name', 'spam_tag']],
    on=['comment_text', 'published_at', 'author_name'],
    how='left'
)
df['spam_tag'] = df['spam_tag_y'].combine_first(df['spam_tag_x'])
df = df.drop(columns=['spam_tag_x', 'spam_tag_y'])

print(f"df: {len(df)}")
df.to_csv(f"hello_comments/psudeo_labaling/v{video_id}_merged_tagged.csv", index=False)

# 準備標籤和留言
label_list = []
comments = df['cleaned_text'].tolist()

for idx, row in df.iterrows():
    if row['spam_tag'] == "spam":
        label_list.append(1)
    elif row['spam_tag'] == "non-spam":
        label_list.append(0)
    else:
        label_list.append(-1)

# 對應標記：1 = spam，0 = non-spam，-1 = 無標記
labels = np.array(label_list)
comments = np.array(comments)

print(f"總留言數: {len(comments)}")
print(f"有標記的spam數量: {np.sum(labels == 1)}")
print(f"有標記的non-spam數量: {np.sum(labels == 0)}")
print(f"無標記數量: {np.sum(labels == -1)}")

# 拆分成有標籤與無標籤
labeled_mask = labels != -1
unlabeled_mask = labels == -1

# 載入 BERT 編碼器
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(comments)

X_labeled = embeddings[labeled_mask]
y_labeled = labels[labeled_mask]

X_unlabeled = embeddings[unlabeled_mask]
unlabeled_comments = comments[unlabeled_mask]

# 切分 train/test
X_train, X_test, y_train, y_test = train_test_split(X_labeled, y_labeled, test_size=0.3, random_state=42)

# 初始模型訓練&評估
clf = LogisticRegression(class_weight='balanced', random_state=42)
clf.fit(X_train, y_train)

y_pred = clf.predict(X_test)
print("\n=== 初始模型在測試集的表現 ===")
print(classification_report(y_test, y_pred, digits=3))
print("混淆矩陣：")
print(confusion_matrix(y_test, y_pred))


# 對無標籤資料做預測
probs = clf.predict_proba(X_unlabeled)
confidence = np.max(probs, axis=1)
pseudo_labels = clf.predict(X_unlabeled)

## threshold的設定會影響到pseudo label的品質！
threshold = 0.85
selected = confidence >= threshold

print(f"\n=== 加入偽標籤的留言 (信心度 >= {threshold}) ===")
print(f"高信心度預測數量: {np.sum(selected)}")
for i, (cmt, conf, pred) in enumerate(zip(unlabeled_comments[selected], confidence[selected], pseudo_labels[selected])):
    if i < 10:  # 只顯示前10個例子
        print(f"{cmt[:50]}... → {'Spam' if pred==1 else 'Not Spam'} ({conf:.3f})")

# 建立新訓練集（加上偽標籤）
X_new_train = np.concatenate([X_labeled, X_unlabeled[selected]])
y_new_train = np.concatenate([y_labeled, pseudo_labels[selected]])

print(f"\n原始訓練集大小: {len(X_labeled)}")
print(f"加入偽標籤後訓練集大小: {len(X_new_train)}")

# 重新訓練模型
print(f"\n=== 重新訓練模型 ===")
clf_final = LogisticRegression(random_state=42)
clf_final.fit(X_new_train, y_new_train)

y_pred_final = clf_final.predict(X_test)
print("\n=== 偽標註後的模型在測試集的表現 ===")
print(classification_report(y_test, y_pred_final, digits=3))
print("混淆矩陣：")
print(confusion_matrix(y_test, y_pred_final))

# 對所有留言重新預測
final_preds = clf_final.predict(embeddings)

print(f"\n=== 最終預測統計 ===")
print(f"預測為spam的數量: {np.sum(final_preds == 1)}")
print(f"預測為not spam的數量: {np.sum(final_preds == 0)}")

# 將結果加回DataFrame
df['predicted_spam'] = final_preds
df['predicted_label'] = ['Spam' if label == 1 else 'Not Spam' for label in final_preds]

# save to spam_result
df.to_csv(f'hello_comments/spam_result/v{video_id}_self_training_results.csv', index=False)
print(f"\n結果已儲存到 hello_comments/spam_result/v{video_id}_self_training_results.csv")

print(f"\n=== 預測結果範例 ===")
for i in range(min(10, len(df))):
    original_tag = df.iloc[i]['spam_tag'] if pd.notna(df.iloc[i]['spam_tag']) else '無標記'
    predicted_tag = df.iloc[i]['predicted_label']
    comment = df.iloc[i]['cleaned_text'][:50]
    print(f"{comment}... | 原始: {original_tag} | 預測: {predicted_tag}")

# add evaluation result to .txt
with open(f'hello_comments/spam_result/v{video_id}_evaluation_results.txt', 'w') as f:
    f.write("=== 初始模型在測試集的表現 ===\n")
    f.write(classification_report(y_test, y_pred, digits=3))
    f.write("\n混淆矩陣：\n")
    f.write(str(confusion_matrix(y_test, y_pred)))
    f.write("\n=== 偽標註後的模型在測試集的表現 ===\n")
    f.write(classification_report(y_test, y_pred_final, digits=3))
    f.write("\n混淆矩陣：\n")
    f.write(str(confusion_matrix(y_test, y_pred_final)))
