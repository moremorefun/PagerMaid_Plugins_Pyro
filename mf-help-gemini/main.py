from pagermaid.enums import Message
from pagermaid.listener import listener


@listener(command="aifaq", description="利用gemini回复提出的问题", parameters="<文本>")
async def fy(message: Message):
    text_to_answer = message.arguments
    new_text = f"{text_to_answer}"
    new_text += f"\n<blockquote>{text_to_answer}</blockquote>"
    await message.edit(new_text)
