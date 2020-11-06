import sys
import time
import amanobot
import amanobot.namedtuple
from amanobot.loop import MessageLoop

"""
$ python3 emodi.py <token>

Emodi: An Emoji Unicode Decoder - You send it some emoji, it tells you the unicodes.
"""

def handle(msg):
    content_type, chat_type, chat_id = amanobot.glance(msg)
    m = amanobot.namedtuple.Message(**msg)

    if chat_id < 0:
        # group message
        print('Received a %s from %s, by %s' % (content_type, m.chat, m.from_))
    else:
        # private message
        print('Received a %s from %s' % (content_type, m.chat))  # m.chat == m.from_

    if content_type == 'text':
        reply = ''

        # For long messages, only return the first 10 characters.
        if len(msg['text']) > 10:
            reply = 'First 10 characters:\n'

        # Length-checking and substring-extraction may work differently
        # depending on Python versions and platforms. See above.

        reply += msg['text'][:10].encode('unicode-escape').decode('ascii')
        bot.sendMessage(chat_id, reply)


TOKEN = sys.argv[1]  # get token from command-line

bot = amanobot.Bot(TOKEN)
MessageLoop(bot, handle).run_as_thread()
print('Listening ...')

# Keep the program running.
while 1:
    time.sleep(10)
