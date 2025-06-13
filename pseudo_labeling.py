import os
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

# ==== 參數區 ====
pseudo_label_threshold_spam = 0.85
pseudo_label_threshold_nonspam = 0.80
min_confidence = 0.65        # 門檻最低值
max_pseudo_each = 50         # 每類每輪最多補多少筆
active_learning_num = 20     # 每輪人工標註數量上限
max_rounds = 10              # 最多循環輪數
f1_improvement_tol = 0.01    # f1-score提升<此數值時，建議人工標註
video_id = 0

# ==== 載入資料 ====
tagged_df = pd.read_csv(f'hello_comments/pseudo_labeling/v{video_id}_retagged.csv')
# print(">>> keys in tagged_df:", tagged_df.keys())
df0 = pd.read_csv(f'hello_comments/spam_tag/video_{video_id}_ckip_spam_tag.csv')
# print(">>> keys in df0:", df0.keys())
print(f"df0 行數: {len(df0)}")
# exit()
# 使用 cleaned_text 作為索引，將 tagged_df 的 spam_tag 結果合併到 df0
df = df0.set_index('cleaned_text').combine_first(
    tagged_df.set_index('cleaned_text')
).reset_index()
print(f"合併後的資料行數: {len(df)}")
# exit()

# ==== 初始標註與資料切分 ====
def get_label(row):
    if row['spam_tag'] == "spam":
        return 1
    elif row['spam_tag'] == "non-spam":
        return 0
    else:
        return -1

df['label'] = df.apply(get_label, axis=1)
comments = df['cleaned_text'].fillna("").values
labels = df['label'].values

labeled_mask = labels != -1
unlabeled_mask = labels == -1

# ==== 編碼 ====
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(comments, show_progress_bar=True)

# ==== 初始訓練集 ====
X_labeled = embeddings[labeled_mask]
y_labeled = labels[labeled_mask]
X_unlabeled = embeddings[unlabeled_mask]
unlabeled_comments = comments[unlabeled_mask]

# ==== 切分測試集 ====
X_train, X_test, y_train, y_test = train_test_split(
    X_labeled, y_labeled, test_size=0.3, random_state=42)

# ==== 主循環 ====
previous_f1 = 0
for round_num in range(1, max_rounds+1):
    print(f"\n=== [Round {round_num}] 訓練與pseudo labeling ===")

    # 訓練模型
    clf = LogisticRegression(class_weight='balanced', random_state=42, max_iter=500)
    clf.fit(X_train, y_train)

    # 評估
    y_pred = clf.predict(X_test)
    report = classification_report(y_test, y_pred, digits=3)
    print("\n[測試集評估]")
    print(report)
    f1 = f1_score(y_test, y_pred, average='macro')
    print(f"Macro F1: {f1:.4f}")
    print("[混淆矩陣]")
    print(confusion_matrix(y_test, y_pred))

    # ---- Pseudo Labeling with Dynamic Threshold ----
    probs = clf.predict_proba(X_unlabeled)
    confidence = np.max(probs, axis=1)
    pseudo_labels = clf.predict(X_unlabeled)

    spam_thres = pseudo_label_threshold_spam
    nonspam_thres = pseudo_label_threshold_nonspam
    while True:
        spam_mask = (pseudo_labels == 1) & (confidence >= spam_thres)
        nonspam_mask = (pseudo_labels == 0) & (confidence >= nonspam_thres)
        n_select = min(np.sum(spam_mask), np.sum(nonspam_mask), max_pseudo_each)
        if n_select > 0 or (spam_thres <= min_confidence and nonspam_thres <= min_confidence):
            break
        spam_thres = max(spam_thres - 0.05, min_confidence)
        nonspam_thres = max(nonspam_thres - 0.05, min_confidence)
        print(f"自動降門檻 -> spam: {spam_thres:.2f}, nonspam: {nonspam_thres:.2f}")

    if n_select > 0:
        spam_idx = np.where(spam_mask)[0][:n_select]
        nonspam_idx = np.where(nonspam_mask)[0][:n_select]
        selected_idx = np.concatenate([spam_idx, nonspam_idx])
        print(f"\n[本輪pseudo label] 加入spam: {len(spam_idx)} nonspam: {len(nonspam_idx)} 共{len(selected_idx)}筆")
    else:
        selected_idx = np.array([], dtype=int)
        print("\n[本輪pseudo label] 無可加入的資料，即使降至最小門檻也不夠平衡")

    # 範例展示
    for i, idx in enumerate(selected_idx[:5]):
        print(f"  {unlabeled_comments[idx][:40]}... → {'Spam' if pseudo_labels[idx]==1 else 'Not Spam'} ({confidence[idx]:.3f})")

    # 合併新的 pseudo label
    if len(selected_idx) > 0:
        X_train = np.concatenate([X_train, X_unlabeled[selected_idx]])
        y_train = np.concatenate([y_train, pseudo_labels[selected_idx]])
        X_unlabeled = np.delete(X_unlabeled, selected_idx, axis=0)
        unlabeled_comments = np.delete(unlabeled_comments, selected_idx, axis=0)
        confidence = np.delete(confidence, selected_idx, axis=0)
        pseudo_labels = np.delete(pseudo_labels, selected_idx, axis=0)

    # ---- Active Learning ----
    if len(unlabeled_comments) > 0:
        uncertain_idx = np.argsort(np.abs(confidence - 0.5))[:active_learning_num]
        to_label = pd.DataFrame({
            'comment': unlabeled_comments[uncertain_idx],
            'model_confidence': confidence[uncertain_idx],
            'pseudo_label': pseudo_labels[uncertain_idx]
        })
        to_label_path = f'hello_comments/spam_tag/v{video_id}_to_be_labeled_round{round_num}.csv'
        to_label.to_csv(to_label_path, index=False)
        print(f"\n[主動學習] 請人工標註: {to_label_path}")
    else:
        print("\n[主動學習] 無新的unlabeled留言")
        to_label_path = None

    # ---- 停止條件 ----
    pseudo_label_growth = len(selected_idx) > 0
    f1_improve = f1 - previous_f1
    need_human = (not pseudo_label_growth) or (abs(f1_improve) < f1_improvement_tol)
    if need_human:
        print("\n[!!!] 建議人工標註後再繼續，自動流程暫停")
        break
    previous_f1 = f1

# ==== 最終應用 ====
clf.fit(X_train, y_train)
final_preds = clf.predict(embeddings)
df['predicted_spam'] = final_preds
df['predicted_label'] = ['Spam' if l==1 else 'Not Spam' for l in final_preds]
output_path = f'hello_comments/spam_result/v{video_id}_self_training_results.csv'
df.to_csv(output_path, index=False)
print(f"\n[完成] 結果存至: {output_path}")
