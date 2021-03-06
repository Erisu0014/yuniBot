# import nonebot
import re
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont
from nonebot.adapters.cqhttp import Bot, MessageSegment
from nonebot.plugin import on_startswith
from nonebot.typing import T_State

from alicebot.plugins.nonebot_guild_patch import GuildMessageEvent
from .config import Config

matcher = on_startswith('要我一直')


def img_gen(pic):
    word1 = f'要我一直'
    word2 = f'吗'
    y = int(pic.size[1] * 600 / pic.size[0])
    y1 = int(pic.size[1] * 700 / pic.size[0] + 30)
    font = ImageFont.truetype('msyh.ttc', 100)
    im = Image.new('RGBA', (600, y1 if y1 > y + 150 else y + 150), (255, 255, 255, 255))
    draw = ImageDraw.Draw(im)
    img1 = pic.resize((600, y), Image.ANTIALIAS)
    img2 = pic.resize((100, int(y / 6)), Image.ANTIALIAS)
    im.paste(img1, (0, 0), img1)
    im.paste(img2, (400, int(y + (y1 - y - y / 6) / 2 if y1 > y + 150 else y + (150 - y / 6) / 2)))
    draw.text((0, y), word1, (0, 0, 0, 255), font)
    draw.text((500, y), word2, (0, 0, 0, 255), font)
    return im


@matcher.handle()
async def ywyz(bot: Bot, event: GuildMessageEvent, state: T_State):
    match = re.search(r"\[CQ:image,file=(.*),url=(.*)\]", str(event.message))
    if not match:
        return
    resp = requests.get(match.group(2), timeout=5)
    resp_cont = resp.content
    pic = img_gen(Image.open(BytesIO(resp_cont)).convert("RGBA"))
    buf = BytesIO()
    img = pic.convert('RGB')
    img.save(buf, format='JPEG')
    await matcher.finish(MessageSegment.image(buf.getvalue()))
