# import nonebot
import base64
from io import BytesIO

from PIL import Image
from nonebot import get_driver
from nonebot import require
from nonebot.adapters.cqhttp import Bot, Message, MessageSegment
from nonebot.plugin import on_command

from alicebot.plugins.nonebot_guild_patch import GuildMessageEvent
from alicebot.utils import send_guild_message
from .config import Config

global_config = get_driver().config
config = Config(**global_config.dict())

matcher = on_command('test')


def pic2b64(pic: Image) -> str:
    buf = BytesIO()
    pic.save(buf, format='GIF')
    base64_str = base64.b64encode(buf.getvalue()).decode()
    return 'base64://' + base64_str


@matcher.handle()
async def _(bot: Bot, event: GuildMessageEvent):
    with open('D:\\pycharmProjects\\aliceBot\\emoji\\重炮收到.gif', 'rb') as f:
        data = f.read()
        f.close()
        # res = pic2b64(Image.open("D:\\pycharmProjects\\aliceBot\\emoji\\重炮收到.gif"))
        await matcher.send(
            Message(f"{MessageSegment.at(event.get_user_id())}不懂你什么意思{MessageSegment.image(data)}"))


scheduler = require("nonebot_plugin_apscheduler").scheduler


@scheduler.scheduled_job("cron", hour=17, minute=30, id="xiaban")
async def xiaban():
    with open('D:\\pycharmProjects\\aliceBot\\emoji\\重炮收到.gif', 'rb') as f:
        data = f.read()
        f.close()
        await send_guild_message('13914601637229449', '1480002', f"下班啦下班啦~{MessageSegment.image(data)}")
