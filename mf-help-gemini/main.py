import aiohttp

from pagermaid.enums import Message
from pagermaid.listener import listener
from pagermaid.services import sqlite
from pagermaid.utils import logs

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-1.5-flash"


@listener(command="set-gemini-key", description="设置gemini的apikey", parameters="<文本>")
async def gemini_set_key(message: Message):
    if not message.parameter or len(message.parameter) != 1:
        return await message.edit("参数错误，请使用set-gemini-key <文本>来设置Gemini API密钥。")

    gemini_key = message.parameter[0]
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{GEMINI_API_BASE_URL}/models/{GEMINI_MODEL}?key={gemini_key}") as response:
                if response.status != 200:
                    return await message.edit("Gemini API密钥无效。")
                await response.json()
                sqlite["gemini_key"] = gemini_key
                await message.edit("已设置Gemini API密钥。")
        except Exception as e:
            await message.edit(f"Gemini API密钥无效。{e}")


@listener(command="set-fy-to", description="设置翻译目标语言", parameters="<文本>")
async def gemini_set_key(message: Message):
    if not message.parameter or len(message.parameter) != 1:
        return await message.edit("参数错误，请使用set-fy-to <文本>来设翻译的目标语言")

    arg = message.parameter[0]
    sqlite["fy_to"] = arg
    await message.edit("已设置翻译的目标语言。{arg}")


@listener(command="aiqa", description="利用gemini回复提出的问题", parameters="<文本>")
async def aiqa(message: Message):
    await process_gemini_request(message, fetch_answer)


@listener(command="aify", description="利用gemini进行翻译", parameters="<文本>")
async def aify(message: Message):
    await process_gemini_request(message, fetch_fy)


async def process_gemini_request(message: Message, fetch_function):
    question = message.arguments
    answer = await fetch_function(question)
    new_text = f"{question}\n<blockquote>{answer}</blockquote>"
    await message.edit(new_text)


async def fetch_gemini_response(payload):
    api_key = sqlite.get("gemini_key")
    if not api_key:
        return "请先设置API密钥。set-gemini-key"

    url = f"{GEMINI_API_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={api_key}"

    async with aiohttp.ClientSession() as session:
        for _ in range(3):  # 最多重试3次
            try:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        logs.error(f"请求失败：HTTP {response.status}")
                        continue

                    result = await response.json()
                    return result['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                logs.error(f"请求失败：{e}")

        return f'请求失败，响应内容：{await response.text()}'


async def fetch_answer(question: str) -> str:
    payload = {
        "contents": [{"role": "user", "parts": [{"text": question}]}],
        "safetySettings": [
            {"category": category, "threshold": "BLOCK_NONE"}
            for category in [
                "HARM_CATEGORY_HARASSMENT",
                "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_DANGEROUS_CONTENT",
            ]
        ],
    }
    return await fetch_gemini_response(payload)


async def fetch_fy(request_txt: str) -> str:
    fy_to = sqlite.get("fy_to", "en")
    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": f"You are a professional translation engine. \nPlease translate the text into {fy_to} without explanation."
                }
            ]
        },
        "contents": [{"role": "user", "parts": [{"text": request_txt}]}],
        "safetySettings": [
            {"category": category, "threshold": "BLOCK_NONE"}
            for category in [
                "HARM_CATEGORY_HARASSMENT",
                "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_DANGEROUS_CONTENT",
            ]
        ],
    }
    return await fetch_gemini_response(payload)
