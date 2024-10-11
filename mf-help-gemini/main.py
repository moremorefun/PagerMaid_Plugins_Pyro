import aiohttp
from pagermaid.enums import Message
from pagermaid.listener import listener
from pagermaid.services import sqlite
from pagermaid.utils import logs

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-1.5-flash"


async def set_key(message: Message, key_type: str, description: str):
    if not message.parameter or len(message.parameter) != 1:
        return await message.edit(f"参数错误，请使用{message.command} <文本>来{description}")
    value = message.parameter[0]
    sqlite[key_type] = value
    await message.edit(f"已{description}。")


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


def create_payload(question: str, system_instruction: str = None):
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
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    return payload


async def process_gemini_request(message: Message, fetch_function, to_language=None):
    question = message.arguments
    answer = await fetch_function(question, to_language)
    new_text = f"{question}\n<blockquote>{answer}</blockquote>"
    await message.edit(new_text)


async def fetch_answer(question: str, to_language=None) -> str:
    payload = create_payload(question)
    return await fetch_gemini_response(payload)


async def fetch_fy(request_txt: str, to_language=None) -> str:
    fy_to = to_language or sqlite.get("fy_to", "en")
    system_instruction = f"You are a professional translation engine. \nPlease translate the text into {fy_to} without explanation."
    payload = create_payload(request_txt, system_instruction)
    return await fetch_gemini_response(payload)


@listener(command="set-gemini-key", description="设置gemini的apikey", parameters="<文本>")
async def gemini_set_key(message: Message):
    async with aiohttp.ClientSession() as session:
        try:
            gemini_key = message.parameter[0]
            async with session.get(f"{GEMINI_API_BASE_URL}/models/{GEMINI_MODEL}?key={gemini_key}") as response:
                if response.status != 200:
                    return await message.edit("Gemini API密钥无效。")
                await response.json()
            await set_key(message, "gemini_key", "设置Gemini API密钥")
        except Exception as e:
            await message.edit(f"Gemini API密钥无效。{e}")


@listener(command="set-fy-to", description="设置翻译目标语言", parameters="<文本>")
async def set_fy_to(message: Message):
    await set_key(message, "fy_to", "设置翻译的目标语言")


@listener(command="aiqa", description="利用gemini回复提出的问题", parameters="<文本>")
async def aiqa(message: Message):
    await process_gemini_request(message, fetch_answer)


@listener(command="aify", description="利用gemini进行翻译", parameters="<文本>")
async def aify(message: Message):
    await process_gemini_request(message, fetch_fy)


@listener(command="aify2cn", description="利用gemini进行翻译到中文", parameters="<文本>")
async def aify2cn(message: Message):
    await process_gemini_request(message, fetch_fy, "zh")
