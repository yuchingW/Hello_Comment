import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel
from gpt_instructions import *
import pandas as pd
import asyncio
import time

load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')
# print(f"OpenAI API Key: {openai_api_key}")

# 非同步 client
client = AsyncOpenAI()

file_path = "gpt_tag/video_0_useless_tag.csv"

# 非同步處理單一 prompt
async def get_useless_response(text, instructions_num):

    class CommentAnalysis(BaseModel):
        tag: bool
        reason: str

    try:
        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": instructions_num},
                {"role": "user", "content": text}
            ],
            response_format= {
                "type": "json_object",
            }
        )
        result = CommentAnalysis.model_validate_json(response.choices[0].message.content)
        return {"tag": result.tag, "reason": result.reason}

    except Exception as e:
        return {"tag": False, "reason": f"分析失敗: {str(e)}"}

# 主處理函式：並行執行三組指令
async def process_comments(i, comment_df):
    async_test_df = comment_df.copy()

    for idx, row in comment_df.iterrows():
        comment_text = row['cleaned_text']
        print(f"==> 處理第{idx+1}則留言：{comment_text}")

        # 並行處理三組 instructions
        result1, result2, result3 = await asyncio.gather(
            get_useless_response(comment_text, instruction1),
            get_useless_response(comment_text, instruction2),
            get_useless_response(comment_text, instruction3),
        )

        # 更新DataFrame
        async_test_df.at[idx, 'tag1'] = result1['tag']
        async_test_df.at[idx, 'reason1'] = result1['reason']
        async_test_df.at[idx, 'tag2'] = result2['tag']
        async_test_df.at[idx, 'reason2'] = result2['reason']
        async_test_df.at[idx, 'tag3'] = result3['tag']
        async_test_df.at[idx, 'reason3'] = result3['reason']

    # 儲存結果
    async_test_df.to_csv(f"gpt_tag/video_{i}_async_tag.csv", index=False, encoding='utf-8-sig')
    print(async_test_df.head(5))
    

if __name__ == "__main__":
    for i in range(0, 1):
        # file_path = f"spam_tag/video_{i}_ckip_spam_tag.csv"
        file_path = f"spam_tag/comments_spam_tag.csv"
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        comment_df = df[df['spam_tag'] != 'spam'][['video_id', 'cleaned_text', 'spam_tag']]


        # 同步跑三個問題
        start_time = time.time()
        asyncio.run(process_comments(i, comment_df[:100]))
        end_time = time.time()
        print(f"影片{i}完成，總耗時: {end_time - start_time:.2f} 秒")