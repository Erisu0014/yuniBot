# import nonebot
from nonebot import get_driver
from nonebot import require
from nonebot.adapters.cqhttp import Bot, MessageSegment
from nonebot.plugin import on_command

from alicebot.plugins.nonebot_guild_patch import GuildMessageEvent
from .config import Config

global_config = get_driver().config
config = Config(**global_config.dict())

matcher = on_command('test')
bot_id = 1503306252


@matcher.handle()
async def _(bot: Bot, event: GuildMessageEvent):
    await matcher.send(MessageSegment.at(event.get_user_id()))
    await matcher.send(MessageSegment.text("不懂你什么意思"))
    with open('D:\\pycharmProjects\\aliceBot\\emoji\\重炮收到.gif', 'rb') as f:
        data = f.read()
        f.close()
        await matcher.send(MessageSegment.at(event.get_user_id()).image(file=data, cache=False))


#
scheduler = require("nonebot_plugin_apscheduler").scheduler


# @scheduler.scheduled_job("cron", minute="*/5", id="hello")
# async def run_every_5_minutes():
#     bot = get_driver().bots[str(bot_id)]
#     sender = Sender(user_id='144115218678801167')
#     event = GuildMessageEvent(time=int(time.time()), self_id=bot_id,
#                               post_type='message', sub_type='channel', user_id='144115218678801167',
#                               message_type='guild', message_id='133-38101123160', guild_id='13914601637229449',
#                               channel_id='1480002', message="0",
#                               sender=sender, self_tiny_id=144115218678801167)
#     await patched_send(bot, event, MessageSegment.text("定时任务才不需要这么麻烦呢"))

# scheduler.add_job(run_every_2_minutes, "interval", days=1, id="hello")
