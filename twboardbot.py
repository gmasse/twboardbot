#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import telepot
import telepot.aio
from telepot.aio.loop import MessageLoop
import requests
import yaml
import json
from operator import itemgetter
from builtins import str as text

with open("config.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

def twstat(weeks_ago= 3):
    hours_ago = 24*7*weeks_ago

    query = { "queries": [ { "metric": "followers_count_total" } ] }
    url = cfg['metrics']['url']+'/api/query/last'
    resp = requests.post(url, json=query, auth=('twboardbot', cfg['metrics']['read_token']))

    stats = {}
    if resp.status_code != 200:
        # This means something went wrong.
        print('ERROR: POST /api/query/last {}'.format(resp.status_code))
    else:
        unsorted_list = [(item['tags']['username'], int(float(item['value']))) for item in resp.json()]
        for (username, count) in unsorted_list:
            stats[username] = { 'now': count }

    query = { "start": text(hours_ago)+"h-ago", "end": text(hours_ago-24)+"h-ago", "queries": [ { "metric": "followers_count_total", "aggregator": "max", "tags": { "username": "*" }} ] }
    url = cfg['metrics']['url']+'/api/query'
    resp = requests.post(url, json=query, auth=('twboardbot', cfg['metrics']['read_token']))

    if resp.status_code != 200:
        # This means something went wrong.
        print('ERROR: POST /api/query {}'.format(resp.status_code))
    else:
        for item in resp.json():
            username = item['tags']['username']
            dps = item['dps']
            first_timestamp = sorted(dps)[0]
            stats[username][text(weeks_ago)+'w-ago'] = int(float(dps[first_timestamp]))
            stats[username][u'\u0394-'+text(weeks_ago)+'w'] = stats[username]['now'] - stats[username][text(weeks_ago)+'w-ago']

    for (username, value) in stats.items():
        if text(weeks_ago)+'w-ago' not in value:
            stats[username][text(weeks_ago)+'w-ago'] = None
            stats[username][u'\u0394-'+text(weeks_ago)+'w'] = -999999999

    return stats


def render_text(stats,weeks_ago=3):
    output = u''
    key=u'\u0394-'+text(weeks_ago)+'w'
    unsorted_list = [(item[0], item[1][key]) for item in stats.items()]
    sorted_list = sorted(unsorted_list, key=itemgetter(1), reverse=True)
    output += u'{:<15}{:>4}{:>5}'.format('@username', key, 'now')
    output += u"\n"
    output += u'-'*24
    output += u"\n"
    for (username, value) in sorted_list:
        delta = stats[username][key]
        if stats[username][text(weeks_ago)+'w-ago'] is None:
            delta = ''
        output += u'{:<15}{:>4}{:>5}'.format(username, delta, stats[username]['now'])
        output += u"\n"

    return output


def render_image(stats,weeks_ago=3):
    from PIL import ImageFont, ImageDraw, Image
    from io import BytesIO

    FSIZE = 30
    INTERLINE = int(FSIZE/3)
    WIDTH = 512

    key=u'\u0394-'+text(weeks_ago)+'w'
    unsorted_list = [(item[0], item[1][key]) for item in stats.items()]
    sorted_list = sorted(unsorted_list, key=itemgetter(1), reverse=True)

    img_size = (WIDTH, (len(sorted_list)+2)*(FSIZE+INTERLINE)+2*INTERLINE)
    # make a blank image for the text
    image = Image.new('RGB', img_size, color='white')

    # get a font
    # ex: https://github.com/google/fonts/blob/master/ofl/lato/Lato-Regular.ttf?raw=true
    font = ImageFont.truetype('Lato-Regular.ttf', FSIZE)

    # get a drawing context
    draw = ImageDraw.Draw(image)

    col = (INTERLINE, int(WIDTH*0.7), WIDTH-INTERLINE)
    line = INTERLINE
    # draw table headers
    draw.text((col[0],line), '@username', font=font, fill='black')
    (width, height) = draw.textsize(key, font=font)
    draw.text((col[1]-width,line), key, font=font, fill='black')
    (width, height) = draw.textsize('now', font=font)
    draw.text((col[2]-width,line), 'now', font=font, fill='black')

    line += FSIZE + INTERLINE
    draw.line((INTERLINE,line,WIDTH-INTERLINE,line), fill='black', width=1)

    for (username, value) in sorted_list:
        # draw text
        draw.text((col[0],line), username, font=font, fill='black')
        if stats[username][text(weeks_ago)+'w-ago'] is not None:
            (width, height) = draw.textsize(text(stats[username][key]), font=font)
            draw.text((col[1]-width,line), text(stats[username][key]), font=font, fill='black')
        (width, height) = draw.textsize(text(stats[username]['now']), font=font)
        draw.text((col[2]-width,line), text(stats[username]['now']), font=font, fill='black')
        line += FSIZE + INTERLINE

    output = BytesIO()
    image.save(output, 'PNG')
    output.seek(0)

    return output


async def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    print(content_type, chat_type, chat_id)

    if content_type != 'text':
        return

    command = msg['text'].lower()

    if command == '/followers_txt':
        output = u'<pre>'
        output += render_text(twstat(3), 3)
        output += u'</pre>'
        print(output)
        await bot.sendMessage(chat_id, output, parse_mode='HTML')

    if command == '/followers':
        output = render_image(twstat(3), 3)
        await bot.sendPhoto(chat_id, ('z.png', output))


def main():
    global bot

    bot = telepot.aio.Bot(cfg['telegram']['token'])
    loop = asyncio.get_event_loop()

    loop.create_task(MessageLoop(bot, handle).run_forever())
    print('Listening ...')

    loop.run_forever()



if __name__ == "__main__":
  main()

