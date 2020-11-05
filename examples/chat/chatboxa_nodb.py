import sys
import asyncio
import amanobot
from amanobot.aio.loop import MessageLoop
from amanobot.aio.delegate import (
    per_chat_id_in, per_application, call, create_open, pave_event_space)

"""
$ python3 chatboxa_nodb.py <token> <owner_id>

Chatbox - a mailbox for chats

1. People send messages to your bot.
2. Your bot remembers the messages.
3. You read the messages later.

It accepts the following commands from you, the owner, only:

- `/unread` - tells you who has sent you messages and how many
- `/next` - read next sender's messages

This example can be a starting point for **customer support** type of bots.
For example, customers send questions to a bot account; staff answers questions
behind the scene, makes it look like the bot is answering questions.

It further illustrates the use of `DelegateBot` and `ChatHandler`, and how to
spawn delegates differently according to the role of users.

This example only handles text messages and stores messages in memory.
If the bot is killed, all messages are lost. It is an *example* after all.
"""

# Simulate a database to store unread messages
class UnreadStore():
    def __init__(self):
        self._db = {}

    def put(self, msg):
        chat_id = msg['chat']['id']

        if chat_id not in self._db:
            self._db[chat_id] = []

        self._db[chat_id].append(msg)

    # Pull all unread messages of a `chat_id`
    def pull(self, chat_id):
        messages = self._db[chat_id]
        del self._db[chat_id]

        # sort by date
        messages.sort(key=lambda m: m['date'])
        return messages

    # Tells how many unread messages per chat_id
    def unread_per_chat(self):
        return [(k,len(v)) for k,v in self._db.items()]


# Accept commands from owner. Give him unread messages.
class OwnerHandler(amanobot.aio.helper.ChatHandler):
    def __init__(self, seed_tuple, store, **kwargs):
        super(OwnerHandler, self).__init__(seed_tuple, **kwargs)
        self._store = store

    async def _read_messages(self, messages):
        for msg in messages:
            # assume all messages are text
            await self.sender.sendMessage(msg['text'])

    async def on_chat_message(self, msg):
        content_type, chat_type, chat_id = amanobot.glance(msg)

        if content_type != 'text':
            await self.sender.sendMessage("I don't understand")
            return

        command = msg['text'].strip().lower()

        # Tells who has sent you how many messages
        if command == '/unread':
            results = self._store.unread_per_chat()

            lines = []
            for r in results:
                n = 'ID: %d\n%d unread' % r
                lines.append(n)

            if not len(lines):
                await self.sender.sendMessage('No unread messages')
            else:
                await self.sender.sendMessage('\n'.join(lines))

        # read next sender's messages
        elif command == '/next':
            results = self._store.unread_per_chat()

            if not len(results):
                await self.sender.sendMessage('No unread messages')
                return

            chat_id = results[0][0]
            unread_messages = self._store.pull(chat_id)

            await self.sender.sendMessage('From ID: %d' % chat_id)
            await self._read_messages(unread_messages)

        else:
            await self.sender.sendMessage("I don't understand")


class MessageSaver(amanobot.aio.helper.Monitor):
    def __init__(self, seed_tuple, store, exclude):
        # The `capture` criteria means to capture all messages.
        super(MessageSaver, self).__init__(seed_tuple, capture=[[lambda msg: not amanobot.is_event(msg)]])
        self._store = store
        self._exclude = exclude

    # Store every message, except those whose sender is in the exclude list, or non-text messages.
    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = amanobot.glance(msg)

        if chat_id in self._exclude:
            print('Chat id %d is excluded.' % chat_id)
            return

        if content_type != 'text':
            print('Content type %s is ignored.' % content_type)
            return

        print('Storing message: %s' % msg)
        self._store.put(msg)


class ChatBox(amanobot.aio.DelegatorBot):
    def __init__(self, token, owner_id):
        self._owner_id = owner_id
        self._seen = set()
        self._store = UnreadStore()

        super(ChatBox, self).__init__(token, [
            # Here is a delegate to specially handle owner commands.
            pave_event_space()(
                per_chat_id_in([owner_id]), create_open, OwnerHandler, self._store, timeout=20),

            # Only one MessageSaver is ever spawned for entire application.
            (per_application(), create_open(MessageSaver, self._store, exclude=[owner_id])),

            # For senders never seen before, send him a welcome message.
            (self._is_newcomer, call(self._send_welcome)),
        ])

    # seed-calculating function: use returned value to indicate whether to spawn a delegate
    def _is_newcomer(self, msg):
        if amanobot.is_event(msg):
            return None

        chat_id = msg['chat']['id']
        if chat_id == self._owner_id:  # Sender is owner
            return None  # No delegate spawned

        if chat_id in self._seen:  # Sender has been seen before
            return None  # No delegate spawned

        self._seen.add(chat_id)
        return []  # non-hashable ==> delegates are independent, no seed association is made.

    async def _send_welcome(self, seed_tuple):
        chat_id = seed_tuple[1]['chat']['id']

        print('Sending welcome ...')
        await self.sendMessage(chat_id, 'Hello!')


TOKEN = sys.argv[1]
OWNER_ID = int(sys.argv[2])

bot = ChatBox(TOKEN, OWNER_ID)
loop = asyncio.get_event_loop()

loop.create_task(MessageLoop(bot).run_forever())
print('Listening ...')

loop.run_forever()
