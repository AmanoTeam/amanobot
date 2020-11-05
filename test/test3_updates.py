# coding=utf8

import time
import threading
import pprint
import sys
import traceback
import amanobot
import amanobot.namedtuple

"""
This script tests:
- receiving all types of messages, by asking user to produce each

Run it by:
$ python3.X test3.py <token> <user_id>

It will assume the bot identified by <token>, and only communicate with the user identified by <user_id>.

If you don't know your user id, run:
$ python test.py <token> 0

And send it a message anyway. It will print out your user id as an unauthorized user.
Ctrl-C to kill it, then run the proper command again.
"""

def equivalent(data, nt):
    if type(data) is dict:
        keys = list(data.keys())

        # number of dictionary keys == number of non-None values in namedtuple?
        if len(keys) != len([f for f in nt._fields if getattr(nt, f) is not None]):
            return False

        # map `from` to `from_`
        fields = [k+'_' if k in ['from'] else k for k in keys]

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
        answer = input('Do you want to continue? [y] ')
        if answer != 'y':
            exit(1)

expected_content_type = None
content_type_iterator = iter([
    'text', 'voice', 'sticker', 'photo', 'audio' ,'document', 'video', 'contact', 'location',
    'new_chat_member',  'new_chat_title', 'new_chat_photo',  'delete_chat_photo', 'left_chat_member'
])

def see_every_content_types(msg):
    global expected_content_type, content_type_iterator

    content_type, chat_type, chat_id = amanobot.glance(msg)
    from_id = msg['from']['id']

    if chat_id != USER_ID and from_id != USER_ID:
        print('Unauthorized user:', chat_id, from_id)
        return

    examine(msg, amanobot.namedtuple.Message)
    try:
        if content_type == expected_content_type:
            expected_content_type = next(content_type_iterator)
            bot.sendMessage(chat_id, 'Please give me a %s.' % expected_content_type)
        else:
            bot.sendMessage(chat_id, 'It is not a %s. Please give me a %s, please.' % (expected_content_type, expected_content_type))
    except StopIteration:
        # reply to sender because I am kicked from group already
        bot.sendMessage(from_id, 'Thank you. I am done.')

TOKEN = sys.argv[1]
USER_ID = int(sys.argv[2])

# amanobot.api.set_proxy('http://192.168.0.103:3128')

bot = amanobot.Bot(TOKEN)

expected_content_type = content_type_iterator.__next__()
bot.sendMessage(USER_ID, 'Please give me a %s.' % expected_content_type)

bot.message_loop(see_every_content_types, run_forever=True)
