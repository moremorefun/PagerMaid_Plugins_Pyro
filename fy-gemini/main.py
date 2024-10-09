from pyrogram import Client

from pagermaid.enums import Message
from pagermaid.listener import listener


@listener(
    is_plugin=True, command="guess", description="能不能好好说话？ - 拼音首字母缩写释义工具（需要回复一句话）"
)
async def guess(_: Client, message: Message):
    await message.edit("没有匹配到拼音首字母缩写")
