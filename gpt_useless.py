import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from gpt_instructions import *
import pandas as pd
import time


load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')
# print(f"OpenAI API Key: {openai_api_key}")

client = OpenAI()

def gpt_useless_tag(instructions: str, comment_text: str) -> str:

    start = time.time()
    class CommentAnalysis(BaseModel):
        tag: bool  # 是否為無意義留言
        reason: str  # 無意義留言的原因

    try:
        response = client.responses.parse(
            model="gpt-4.1-nano-2025-04-14",
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": comment_text}
            ],
            text_format=CommentAnalysis,
        )

        result = response.output_parsed

        result_dict = {
            "tag": result.tag,
            "reason": result.reason
        }
        print(result_dict)
        end = time.time()
        elapsed_time = end - start
        print(f"===> 執行時間：{elapsed_time:.2f}秒")
        return result_dict
    
    except Exception as e:
        print(f"Error: {e}")
        return {"tag": False, "reason": f"分析失敗: {str(e)}"}
    

if __name__ == "__main__":
    for i in range(0, 1):
        comment_path = f"gpt_tag/video_{i}_ckip_cleaned.csv"

        comment_list = pd.read_csv(comment_path, encoding='utf-8')['cleaned_text'].tolist()
        test_list = []
        for comment in comment_list:
            print(f"Comment: {comment}")
            level_one = gpt_useless_tag(instructoin1, comment)
            level_two = gpt_useless_tag(instruction2, comment)
            level_three = gpt_useless_tag(instruction3, comment)

            temp_dict = {
                "comment_text" : comment,
                "tag1": level_one['tag'],
                "reason1": level_one['reason'], 
                "tag2": level_two['tag'], 
                "reason2": level_two['reason'],
                "tag3": level_three['tag'],
                "reason3": level_three['reason']
            }

            test_list.append(temp_dict)
        
        test_df = pd.DataFrame(test_list)
        test_df.to_csv(f"gpt_tag/video_{i}_useless_tag.csv", index=False, encoding='utf-8-sig')