# coding=utf8

import time
import threading
import pprint
import sys
import traceback
import random
import amanobot
from amanobot.namedtuple import (
    InlineQuery, ChosenInlineResult, InputTextMessageContent,
    InlineQueryResultArticle, InlineQueryResultPhoto, InlineQueryResultGame)

def equivalent(data, nt):
    if type(data) is dict:
        keys = data.keys()

        # number of dictionary keys == number of non-None values in namedtuple?
        if len(keys) != len([f for f in nt._fields if getattr(nt, f) is not None]):
            return False

        # map `from` to `from_`
        fields = list(map(lambda k: k+'_' if k in ['from'] else k, keys))

        return all(map(equivalent, [data[k] for k in keys], [getattr(nt, f) for f in fields]))
    if type(data) is list:
        return all(map(equivalent, data, nt))
    return data==nt

def examine(result, type):
    try:
        print('Examining %s ......' % type)

        nt = type(**result)
        assert equivalent(result, nt), 'Not equivalent:::::::::::::::\n%s\n::::::::::::::::\n%s' % (result, nt)

        pprint.pprint(result)
        pprint.pprint(nt)
        print()
    except AssertionError:
        traceback.print_exc()
        answer = raw_input('Do you want to continue? [y] ')
        if answer != 'y':
            exit(1)

def on_inline_query(msg):
    def compute():
        articles = [InlineQueryResultArticle(
                       id='abc', title='HK', input_message_content=InputTextMessageContent(message_text='Hong Kong'), url='https://www.google.com', hide_url=True),
                   {'type': 'article',
                       'id': 'def', 'title': 'SZ', 'input_message_content': {'message_text': 'Shenzhen'}, 'url': 'https://www.yahoo.com'}]

        photos = [InlineQueryResultPhoto(
                      id='123', photo_url='https://core.telegram.org/file/811140934/1/tbDSLHSaijc/fdcc7b6d5fb3354adf', thumb_url='https://core.telegram.org/file/811140934/1/tbDSLHSaijc/fdcc7b6d5fb3354adf'),
                  {'type': 'photo',
                      'id': '345', 'photo_url': 'https://core.telegram.org/file/811140184/1/5YJxx-rostA/ad3f74094485fb97bd', 'thumb_url': 'https://core.telegram.org/file/811140184/1/5YJxx-rostA/ad3f74094485fb97bd', 'caption': 'Caption', 'title': 'Title', 'input_message_content': {'message_text': 'Shenzhen'}}]

        games = [InlineQueryResultGame(
                    id='abc', game_short_name='sunchaser')]

        results = random.choice([articles, photos, games])
        return results

    query_id, from_id, query = amanobot.glance(msg, flavor='inline_query')

    if from_id != USER_ID:
        print('Unauthorized user:', from_id)
        return

    examine(msg, InlineQuery)
    answerer.answer(msg, compute)


def on_chosen_inline_result(msg):
    result_id, from_id, query = amanobot.glance(msg, flavor='chosen_inline_result')

    if from_id != USER_ID:
        print('Unauthorized user:', from_id)
        return

    examine(msg, ChosenInlineResult)

    print('Chosen inline query:')
    pprint.pprint(msg)


def compute(inline_query):
    articles = [InlineQueryResultArticle(
                   id='abc', title='HK', message_text='Hong Kong', url='https://www.google.com', hide_url=True),
               {'type': 'article',
                   'id': 'def', 'title': 'SZ', 'message_text': 'Shenzhen', 'url': 'https://www.yahoo.com'}]

    photos = [InlineQueryResultPhoto(
                  id='123', photo_url='https://core.telegram.org/file/811140934/1/tbDSLHSaijc/fdcc7b6d5fb3354adf', thumb_url='https://core.telegram.org/file/811140934/1/tbDSLHSaijc/fdcc7b6d5fb3354adf'),
              {'type': 'photo',
                  'id': '345', 'photo_url': 'https://core.telegram.org/file/811140184/1/5YJxx-rostA/ad3f74094485fb97bd', 'thumb_url': 'https://core.telegram.org/file/811140184/1/5YJxx-rostA/ad3f74094485fb97bd', 'caption': 'Caption', 'title': 'Title', 'message_text': 'Message Text'}]

    results = random.choice([articles, photos])
    return results


TOKEN = sys.argv[1]
USER_ID = int(sys.argv[2])

bot = amanobot.Bot(TOKEN)
answerer = amanobot.helper.Answerer(bot)

bot.sendMessage(USER_ID, 'Please give me an inline query.')

bot.message_loop({'inline_query': on_inline_query,
                  'chosen_inline_result': on_chosen_inline_result}, run_forever=True)
