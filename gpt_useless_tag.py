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
        tag1: bool
        reason1: str
        tag2: bool
        reason2: str
        tag3: bool
        reason3: str

    try:
        response = client.responses.parse(
            # model="gpt-4.1-nano-2025-04-14",
            model = "gpt-4.1-mini-2025-04-14",
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": comment_text}
            ],
            text_format=CommentAnalysis,
        )

        result = response.output_parsed
        result_dict = {
            "tag1": result.tag1,
            "reason1": result.reason1,
            "tag2": result.tag2,
            "reason2": result.reason2,
            "tag3": result.tag3,
            "reason3": result.reason3
        }
        print(f">>> tag 結果:\n {result_dict}")
        end = time.time()
        elapsed_time = end - start
        print(f"===> 執行時間：{elapsed_time:.2f}秒")
        return result_dict
    
    except Exception as e:
        print(f"Error: {e}")
        return {"tag": False, "reason": f"分析失敗: {str(e)}"}
    

if __name__ == "__main__":
    for i in range(0, 1):
        comment_path = f"hello_comments/for_bert/video_{i}_ckip_cleaned.csv"
        comment_list = pd.read_csv(comment_path, encoding='utf-8')['cleaned_text'].tolist()[:100]

        test_list = []
        for idx, comment in enumerate(comment_list, 1):
            print(f">>>> {idx}/{len(comment_list)}")
            print(f"Comment: {comment}")
            tag_res = gpt_useless_tag(instruction_combine, comment)

            temp_dict = {
                "comment_text" : comment,
                "tag1": tag_res['tag1'],
                "reason1": tag_res['reason1'],
                "tag2": tag_res['tag2'],
                "reason2": tag_res['reason2'],
                "tag3": tag_res['tag3'],
                "reason3": tag_res['reason3']
            }

            test_list.append(temp_dict)
        
        test_df = pd.DataFrame(test_list)
        test_df.to_csv(f"gpt_tag/video_{i}_useless_tag_4-1mini.csv", index=False, encoding='utf-8-sig')