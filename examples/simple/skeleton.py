import sys
import time
import amanobot
from amanobot.loop import MessageLoop

"""
$ python3 skeleton.py <token>

A skeleton for your amanobot programs.
"""

def handle(msg):
    flavor = amanobot.flavor(msg)

    summary = amanobot.glance(msg, flavor=flavor)
    print(flavor, summary)


TOKEN = sys.argv[1]  # get token from command-line

bot = amanobot.Bot(TOKEN)
MessageLoop(bot, handle).run_as_thread()
print('Listening ...')

# Keep the program running.
while 1:
    time.sleep(10)
