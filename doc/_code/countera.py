import sys
import asyncio
import amanobot
from amanobot.aio.loop import MessageLoop
from amanobot.aio.delegate import pave_event_space, per_chat_id, create_open

class MessageCounter(amanobot.aio.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(MessageCounter, self).__init__(*args, **kwargs)
        self._count = 0

    async def on_chat_message(self, msg):
        self._count += 1
        await self.sender.sendMessage(self._count)

TOKEN = sys.argv[1]  # get token from command-line

bot = amanobot.aio.DelegatorBot(TOKEN, [
    pave_event_space()(
        per_chat_id(), create_open, MessageCounter, timeout=10),
])

loop = asyncio.get_event_loop()
loop.create_task(MessageLoop(bot).run_forever())
print('Listening ...')

loop.run_forever()
