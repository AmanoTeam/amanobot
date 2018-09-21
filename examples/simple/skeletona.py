import sys
import asyncio
import amanobot
import amanobot.aio
from amanobot.aio.loop import MessageLoop

"""
$ python3 skeletona.py <token>

A skeleton for your async amanobot programs.
"""

def handle(msg):
    flavor = amanobot.flavor(msg)

    summary = amanobot.glance(msg, flavor=flavor)
    print(flavor, summary)


TOKEN = sys.argv[1]  # get token from command-line

bot = amanobot.aio.Bot(TOKEN)
loop = asyncio.get_event_loop()

loop.create_task(MessageLoop(bot, handle).run_forever())
print('Listening ...')

loop.run_forever()
