from nonebot import logger
from alicebot.plugins.nonebot_guild_patch import GuildMessageEvent, patched_send
from nonebot.adapters.cqhttp.event import Sender

from nonebot.adapters.cqhttp import Bot, MessageSegment
from nonebot import on_command
from nonebot import require
import asyncio
import base64
import html
import json
import math
import os
import random
import re
import string
import time
import traceback
from io import BytesIO
import aiohttp
import feedparser
from PIL import Image
from nonebot import get_driver

from .config import Config

global_config = get_driver().config
config = Config(**global_config.dict())
bot_id = 1503306252
rss_news = {}

data = {
    'rsshub': 'http://1.117.219.198:1200',
    'proxy': '',
    'proxy_urls': [],
    'last_time': {},
    'guild_rss': {},
    'guild_mode': {},
}

HELP_MSG = '''rss订阅
rss list : 查看订阅列表
rss add rss地址 : 添加rss订阅
rss addb up主id : 添加b站up主订阅
rss addr route : 添加rsshub route订阅
rss remove 序号 : 删除订阅列表指定项
rss mode 0/1 : 设置消息模式 标准/简略
详细说明见项目主页: https://github.com/zyujs/rss
'''


def save_data():
    path = os.path.join(os.path.dirname(__file__), 'data.json')
    try:
        with open(path, 'w', encoding='utf8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        traceback.print_exc()


def load_data():
    path = os.path.join(os.path.dirname(__file__), 'data.json')
    if not os.path.exists(path):
        save_data()
        return
    try:
        with open(path, encoding='utf8') as f:
            d = json.load(f)
            if 'rsshub' in d:
                if d['rsshub'][-1] == '/':
                    d['rsshub'] = d['rsshub'][:-1]
                data['rsshub'] = d['rsshub']
            if 'last_time' in d:
                data['last_time'] = d['last_time']
            if 'guild_rss' in d:
                data['guild_rss'] = d['guild_rss']
            if 'guild_mode' in d:
                data['guild_mode'] = d['guild_mode']
            if 'proxy' in d:
                data['proxy'] = d['proxy']
            if 'proxy_urls' in d:
                data['proxy_urls'] = d['proxy_urls']
    except:
        traceback.print_exc()
    global default_rss


load_data()

default_rss = [
    data['rsshub'] + '/bilibili/user/dynamic/353840826',  # pcr官方号
]


async def query_data(url, proxy=''):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy) as resp:
                return await resp.read()
    except:
        return None


def get_image_url(desc):
    imgs = re.findall(r'<img.*?src="(.+?)".+?>', desc)
    return imgs


def remove_html(content):
    # 移除html标签
    p = re.compile('<[^>]+>')
    content = p.sub("", content)
    return content


def remove_lf(content):
    text = ''
    for line in content.splitlines():
        line = line.strip()
        if line:
            text += line + '\n'
    text = text.rstrip()
    return text


async def generate_image(url_list):
    raw_images = []
    num = 0
    for url in url_list:
        url = html.unescape(url)
        proxy = ''
        for purl in data['proxy_urls']:
            if purl in url:
                proxy = data['proxy']
        image = await query_data(url, proxy)
        if image:
            try:
                im = Image.open(BytesIO(image))
                im = im.convert("RGBA")
                raw_images.append(im)
                num += 1
            except:
                pass
        if num >= 9:
            break

    if num == 0:
        return None
    elif num == 1:
        io = BytesIO()
        raw_images[0].save(io, 'png')
        return io.getvalue()

    dest_img = None
    box_size = 300
    row = 3
    border = 5
    height = 0
    width = 0
    if num == 3 or num >= 5:  # 3列
        width = 900 + border * 2
        height = math.ceil(num / 3) * (300 + border) - border
    else:  # 2列
        box_size = 400
        row = 2
        width = 800 + border
        height = math.ceil(num / 2) * (400 + border) - border
    dest_img = Image.new('RGBA', (width, height), (255, 255, 255, 0))

    for i in range(num):
        im = raw_images[i]
        if im:
            w, h = im.size
            if w > h:
                x0 = (w // 2) - (h // 2)
                x1 = x0 + h
                im = im.crop((x0, 0, x1, h))
            elif h > w:
                y0 = (h // 2) - (w // 2)
                y1 = y0 + w
                im = im.crop((0, y0, w, y1))
            im = im.resize((box_size, box_size), Image.ANTIALIAS)
            x = (i % row) * (box_size + border)
            y = (i // row) * (box_size + border)
            dest_img.paste(im, (x, y))
    io = BytesIO()
    dest_img.save(io, 'png')
    return io.getvalue()


def get_published_time(item):
    time_t = 0
    if 'published_parsed' in item:
        time_t = time.mktime(item['published_parsed'])
    if 'updated_parsed' in item:
        time_t = time.mktime(item['updated_parsed'])
    return time_t


def get_latest_time(item_list):
    last_time = 0
    for item in item_list:
        time = get_published_time(item)
        if time > last_time:
            last_time = time
    return last_time


def check_title_in_content(title, content):
    title = title[:len(title) // 2]
    title = title.replace('\n', '').replace('\r', '').replace(' ', '')
    content = content.replace('\n', '').replace('\r', '').replace(' ', '')
    if title in content:
        return True
    return False


async def get_rss_news(rss_url):
    news_list = []
    proxy = ''
    for purl in data['proxy_urls']:
        if purl in rss_url:
            proxy = data['proxy']
    res = await query_data(rss_url, proxy)
    if not res:
        return news_list
    feed = feedparser.parse(res)
    if feed['bozo'] != 0:
        logger.info(f'rss解析失败 {rss_url}')
        return news_list
    if len(feed['entries']) == 0:
        return news_list
    if rss_url not in data['last_time']:
        logger.info(f'rss初始化 {rss_url}')
        data['last_time'][rss_url] = get_latest_time(feed['entries'])
        return news_list

    last_time = data['last_time'][rss_url]

    for item in feed["entries"]:
        if get_published_time(item) > last_time:
            summary = item['summary']
            # 移除转发信息
            i = summary.find('//转发自')
            if i > 0:
                summary = summary[:i]
            news = {
                'feed_title': feed['feed']['title'],
                'title': item['title'],
                'content': remove_html(summary),
                'id': item['id'],
                'image': await generate_image(get_image_url(summary)),
            }
            news_list.append(news)

    data['last_time'][rss_url] = get_latest_time(feed['entries'])
    return news_list


async def refresh_all_rss():
    for item in default_rss:
        if item not in rss_news:
            rss_news[item] = []
    for guild_rss in data['guild_rss'].values():
        for rss_url in guild_rss:
            if rss_url not in rss_news:
                rss_news[rss_url] = []
    # 删除没有引用的项目的推送进度
    for rss_url in list(data['last_time'].keys()):
        if rss_url not in rss_news:
            data['last_time'].pop(rss_url)
    for rss_url in rss_news.keys():
        rss_news[rss_url] = await get_rss_news(rss_url)
    save_data()


def add_salt(data):
    salt = ''.join(random.sample(string.ascii_letters + string.digits, 6))
    return data + bytes(salt, encoding="utf8")


def format_msg(news):
    msg = f"{news['feed_title']}更新:\n{news['id']}"
    if not check_title_in_content(news['title'], news['content']):
        msg += f"\n{news['title']}"
    msg += f"\n----------\n{remove_lf(news['content'])}"
    if news['image']:
        base64_str = f"base64://{base64.b64encode(add_salt(news['image'])).decode()}"
        msg += f'[CQ:image,file={base64_str}]'
    return msg


def format_brief_msg(news):
    msg = f"{news['feed_title']}更新:\n{news['id']}"
    msg += f"\n----------\n{news['title']}"
    return msg


async def guild_process(event: GuildMessageEvent):
    bot = get_driver().bots[str(bot_id)]
    await refresh_all_rss()
    # todo guildId根据api获取，并通过for循环推送
    gid = 13914601637229449
    rss_list = default_rss
    if str(gid) in data['guild_rss']:
        rss_list = data['guild_rss'][str(gid)]
    else:
        data['guild_rss'][str(gid)] = default_rss
    for rss_url in rss_list:
        if rss_url in rss_news:
            news_list = rss_news[rss_url]
            for news in reversed(news_list):
                msg = None
                if str(gid) in data['guild_mode'] and data['guild_mode'][str(gid)] == 1:
                    msg = format_brief_msg(news)
                else:
                    msg = format_msg(news)
                try:
                    await patched_send(bot, event, msg)
                except:
                    logger.info(f'群 {gid} 推送失败')
            await asyncio.sleep(1)


async def rss_add(guild_id, rss_url):
    guild_id = str(guild_id)
    proxy = ''
    for purl in data['proxy_urls']:
        if purl in rss_url:
            proxy = data['proxy']
    res = await query_data(rss_url, proxy)
    feed = feedparser.parse(res)
    if feed['bozo'] != 0:
        return f'无法解析rss源:{rss_url}'

    if guild_id not in data['guild_rss']:
        data['guild_rss'][guild_id] = default_rss
    if rss_url not in set(data['guild_rss'][guild_id]):
        data['guild_rss'][guild_id].append(rss_url)
    else:
        return '订阅列表中已存在该项目'
    save_data()
    return '添加成功'


def rss_remove(guild_id, i):
    guild_id = str(guild_id)
    if guild_id not in data['guild_rss']:
        data['guild_rss'][guild_id] = default_rss
    if i >= len(data['guild_rss'][guild_id]):
        return '序号超出范围'
    data['guild_rss'][guild_id].pop(i)
    save_data()
    return '删除成功\n当前' + rss_get_list(guild_id)


def rss_get_list(guild_id):
    guild_id = str(guild_id)
    if guild_id not in data['guild_rss']:
        data['guild_rss'][guild_id] = default_rss
    msg = '订阅列表:'
    num = len(data['guild_rss'][guild_id])
    for i in range(num):
        url = data['guild_rss'][guild_id][i]
        url = re.sub(r'http[s]*?://.*?/', '/', url)
        msg += f"\n{i}. {url}"
    if num == 0:
        msg += "\n空"
    return msg


def rss_set_mode(guild_id, mode):
    guild_id = str(guild_id)
    mode = int(mode)
    if mode > 0:
        data['guild_mode'][guild_id] = 1
        msg = '已设置为简略模式'
    else:
        data['guild_mode'][guild_id] = 0
        msg = '已设置为标准模式'
    save_data()
    return msg


rss = on_command('rss')


@rss.handle()
async def rss_cmd(bot: Bot, event: GuildMessageEvent):
    if event.get_user_id() == bot_id:
        pass
    msg = ''
    guild_id = event.guild_id
    args = event.get_plaintext().split(' ')
    # todo 判断为管理员再进行操作
    is_admin = True
    if len(args) == 0:
        msg = HELP_MSG
    elif args[0] == 'help':
        msg = HELP_MSG
    elif args[0] == 'add':
        if not is_admin:
            msg = '权限不足'
        elif len(args) >= 2:
            msg = await rss_add(guild_id, args[1])
        else:
            msg = '需要附带rss地址'
    elif args[0] == 'addb' or args[0] == 'add-bilibili':
        if not is_admin:
            msg = '权限不足'
        elif len(args) >= 2 and args[1].isdigit():
            rss_url = data['rsshub'] + '/bilibili/user/dynamic/' + str(args[1])
            msg = await rss_add(guild_id, rss_url)
        else:
            msg = '需要附带up主id'
    elif args[0] == 'addr' or args[0] == 'add-route':
        if not is_admin:
            msg = '权限不足'
        elif len(args) >= 2:
            rss_url = data['rsshub'] + args[1]
            msg = await rss_add(guild_id, rss_url)
        else:
            msg = '需要提供route参数'
        pass
    elif args[0] == 'remove' or args[0] == 'rm':
        if not is_admin:
            msg = '权限不足'
        elif len(args) >= 2 and args[1].isdigit():
            msg = rss_remove(guild_id, int(args[1]))
        else:
            msg = '需要提供要删除rss订阅的序号'
    elif args[0] == 'list' or args[0] == 'ls':
        msg = rss_get_list(guild_id)
    elif args[0] == 'mode':
        if not is_admin:
            msg = '权限不足'
        elif len(args) >= 2 and args[1].isdigit():
            msg = rss_set_mode(guild_id, args[1])
        else:
            msg = '需要附带模式(0/1)'
    else:
        msg = '参数错误'
    await rss.send(MessageSegment.text(msg))


scheduler = require("nonebot_plugin_apscheduler").scheduler


@scheduler.scheduled_job('interval', minutes=5)
async def job():
    sender = Sender(user_id='144115218678801167')
    event = GuildMessageEvent(time=int(time.time()), self_id=bot_id,
                              post_type='message', sub_type='channel', user_id='144115218678801167',
                              message_type='guild', message_id='133-38101123160', guild_id='13914601637229449',
                              channel_id='1480002', message="0",
                              sender=sender, self_tiny_id=144115218678801167)
    await guild_process(event)