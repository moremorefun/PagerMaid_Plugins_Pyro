import json
import os
import aiohttp

from pagermaid.enums import Message
from pagermaid.listener import listener

config_file = "mf-help-gemini.json"

default_settings = {
    "api_key": ""
}
settings = {}

# 读取配置文件
if not os.path.exists(config_file):
    with open(config_file, "w") as file:
        json.dump(default_settings, file, indent=4)
    print("文件不存在，已创建新文件并设置了默认值。")
else:
    try:
        with open(config_file, "r") as file:
            settings = json.load(file)
    except (IOError, ValueError) as e:
        print(f"加载json设置失败: {e}")

    for key, value in default_settings.items():
        settings.setdefault(key, value)

    try:
        with open(config_file, "w") as file:
            json.dump(settings, file, indent=4)
    except (IOError, ValueError) as e:
        print(f"更新设置失败: {e}")


@listener(command="aifaq", description="利用gemini回复提出的问题", parameters="<文本>")
async def aifaq(message: Message):
    question = message.arguments
    answer = await fetch_answer(question)
    new_text = f"{question}"
    new_text += f"\n<blockquote>{answer}</blockquote>"
    await message.edit(new_text)


async def fetch_answer(question):
    api_key = settings.get("api_key")
    if not api_key:
        return "请先设置API密钥。"
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=" + api_key
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "{question}".format(
                            question=question)
                    }
                ]
            }
        ],
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        max_retries = 3
        retry_count = 0
        resp_body = ''
        while retry_count < max_retries:
            try:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        print(f"翻译失败：{response.status}")
                        retry_count += 1
                        continue

                    result = await response.json()
                    resp_body = json.dumps(result, indent=4)
                    try:
                        return result['candidates'][0]['content']['parts'][0]['text']
                    except (KeyError, IndexError) as e:
                        print(f"结果解析失败：{e}")
                        retry_count += 1
                        continue
            except Exception as e:
                print(f"请求失败：{e}")
                retry_count += 1
                continue
        return 'Fail. resp body: {body}'.format(body=resp_body)
