
instructoin1 = """
你是YouTube留言內容分析研究員，分類留言是否為「無意義留言」。
只能用繁體中文回答

<output>
output as a json object:
{
    "tag": bool,  # true=無意義、false=有意義
    "reason": str  # 無意義留言的原因
}
"""

instruction2 ="""
你是YouTube留言內容分析研究員，分類留言是否為「無意義留言」。
只能用繁體中文回答

<definition>
無意義留言是指那些沒有實質內容、無法提供有價值的資訊或討論的留言。
</definition>

<examples>
- "求 女生 IG FB",  tag=true
- "可憐的奮蛆們", tag=true
- "真的 不好笑", tag=true
- "賴的老家是國民黨遷台之前就有的 你們這節目一直批評賴的老家有沒有良心", tag=flase
- "網路投票就不知道是不是個人意願啦 也沒辦法做到不公開吧", tag=false 
- "所以說前幾年說要發放的數位身分證在哪裡呢", tag=false
</examples>

<output>
output as a json object:
{
    "tag": bool,  # true=無意義、false=有意義
    "reason": str  # 無意義留言的原因
}
"""


instruction3 = """
你是YouTube留言內容分析研究員，分類留言是否為「無意義留言」。
只能用繁體中文回答

<definition>
無意義留言的指標：
1. 留言少於5個字
2. 留言內容沒有意義 e.g. 哈哈哈笑死、真的 不好笑
3. 留言內容重複 e.g. 主持人出來道歉 歧視弱勢團體 罷看 主持人出來道歉 歧視弱勢團體 罷看...
4. 情緒性強或引發反感 e.g. 可憐的奮蛆們、賀龍神精病三八女、廢物綠蛆 廢物藍叫
</definition>

<examples>
- "求 女生 IG FB",  tag=true
- "可憐的奮蛆們", tag=true
- "主持人出來道歉 歧視弱勢團體 罷看 主持人出來道歉 歧視弱勢團體 罷看...", tag=true
- "賴的老家是國民黨遷台之前就有的 你們這節目一直批評賴的老家有沒有良心", tag=flase
- "網路投票就不知道是不是個人意願啦 也沒辦法做到不公開吧", tag=false 
- "所以說前幾年說要發放的數位身分證在哪裡呢", tag=false
</examples>

<task>根據definition和examples，分析留言是否為無意義留言</task>
<dos>
1. tag: 判斷留言是否符合無意義留言的定義
2. reason: 說明留言符合哪些definition的指標
</dos>

<output>
output as a json object:
{
    "tag": bool,  # true=無意義、false=有意義
        "reason": str  # 無意義留言的原因
}
"""