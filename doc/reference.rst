amanobot reference
=================

Amanobot has two versions:

- **Traditional version** uses
  `urllib3 <https://urllib3.readthedocs.io/en/latest/>`_ to make HTTP requests,
  and uses threads to achieve delegation by default.
- **Async version** is based on
  `asyncio <https://docs.python.org/3/library/asyncio.html>`_, uses
  `aiohttp <http://aiohttp.readthedocs.io/en/stable/>`_ to make asynchronous
  HTTP requests, and uses asyncio tasks to achieve delegation.

This page focuses on traditional version. Async version is very similar,
the most significant differences being:

- Blocking methods (mostly network operations) become coroutines, and should be
  called with ``await``.
- Delegation is achieved by tasks, instead of threads. Thread-safety ceases to
  be a concern.

Traditional modules are under the package :mod:`amanobot`, while async modules are
under :mod:`amanobot.aio`:

+--------------------+------------------------+
| Traditional        | Async                  |
+====================+========================+
| amanobot           | amanobot.aio           |
+--------------------+------------------------+
| amanobot.loop      | amanobot.aio.loop      |
+--------------------+------------------------+
| amanobot.delegate  | amanobot.aio.delegate  |
+--------------------+------------------------+
| amanobot.helper    | amanobot.aio.helper    |
+--------------------+------------------------+
| amanobot.routing   | amanobot.aio.routing   |
+--------------------+------------------------+
| amanobot.api       | amanobot.aio.api       |
+--------------------+------------------------+

Some modules do not have async counterparts, e.g. :mod:`amanobot.namedtuple` and
:mod:`amanobot.exception`, because they are shared.

Try to combine this reading with the provided
`examples <https://github.com/AmanoTeam/amanobot/tree/master/examples>`_ .
One example is worth a thousand words. I hope they make things clear.

Basic Bot
---------

The ``Bot`` class is mostly a wrapper around `Telegram Bot API <https://core.telegram.org/bots/api>`_.
Many methods are straight mappings to Bot API methods. Where appropriate,
I only give links below. No point to duplicate all the details.

.. autoclass:: amanobot.Bot
   :members:

Message Loop and Webhook
------------------------

There are two ways to obtain updates from Telegram Bot API: make calls to
:meth:`.Bot.getUpdates` continuously, or use webhook.

In the former case, it is troublesome to have to program that manually.
So :class:`.MessageLoop` is here to ease your burden. In the latter case,
although the programming overhead is mainly on the web server, a structured way
to funnel web requests into amanobot is desirable. The result is :class:`.Webhook`
and :class:`.OrderedWebhook`.

The idea is similar. You supply a message-handling function to the object
constructor, then use :meth:`.run_as_thread` to get it going. A :class:`.MessageLoop`
makes calls to :meth:`.getUpdates` continuously, and apply the message-handling
function to every message received. A :class:`.Webhook` or :class:`.OrderedWebhook`
would not do anything by itself; you have to :meth:`.feed` it the new update
every time the web server receives one.

In place of the message-handling function, you can supply one of the following:

- a function that takes one argument (the message)
- if ``None``, the bot's ``handle`` method is used
- a routing table

A *routing table* is a dictionary of ``{flavor: function}``, mapping messages to
appropriate handler functions according to their flavors. It allows you to
define functions specifically to handle one flavor of messages. It usually looks
like this: ``{'chat': fn1, 'callback_query': fn2, 'inline_query': fn3, ...}``.
Each handler function should take one argument (the message).

.. autoclass:: amanobot.loop.MessageLoop
   :members:
   :undoc-members:
   :inherited-members:

In practice, you should always use :class:`.OrderedWebhook` rather than :class:`.Webhook`.
Updates are individual HTTP requests, and there is no guarantee of their arrival
order. :class:`.OrderedWebhook` puts them in order (according to ``update_id``)
before applying the message-handling function. In contrast, :class:`.Webhook`
applies the message-handling function in the order you feed them. Unless you
want to implement your own ordering logic, :class:`.Webhook` should not be used.

In async version, a task of :meth:`.run_forever` should be created instead of
:meth:`.run_as_thread`.

Refer to `webhook examples <https://github.com/AmanoTeam/amanobot/tree/master/examples/webhook>`_
for usage.

.. autoclass:: amanobot.loop.OrderedWebhook
   :members:
   :undoc-members:
   :inherited-members:

.. autoclass:: amanobot.loop.Webhook
   :members:
   :undoc-members:
   :inherited-members:

Functions
---------

.. autofunction:: amanobot.flavor
.. autofunction:: amanobot.glance
.. autofunction:: amanobot.flance
.. autofunction:: amanobot.peel
.. autofunction:: amanobot.fleece
.. autofunction:: amanobot.is_event
.. autofunction:: amanobot.message_identifier
.. autofunction:: amanobot.origin_identifier

DelegatorBot
------------

.. autoclass:: amanobot.DelegatorBot

A *seeder* is a function that:

- takes one argument - a message
- returns a *seed*. Depending on the nature of the seed, behavior is as follows:
    - if the seed is a hashable (e.g. number, string, tuple), it looks for a
      *delegate* associated with the seed. (Think of a dictionary of ``{seed: delegate}``)
        - if such a delegate exists and is alive, it is assumed that the message
          will be picked up by the delegate. Nothing more is done.
        - if no delegate exists or that delegate is no longer alive, a new
          delegate is obtained by calling the delegator function. The new
          delegate is associated with the seed.
        - **In essence, when the seed is a hashable, only one delegate is running
          for a given seed.**
    - if the seed is a non-hashable, (e.g. list), a new delegate is always
      obtained by calling the delegator function. No seed-delegate association
      occurs.
    - if the seed is ``None``, nothing is done.

A *delegator* is a function that:

- takes one argument - a (bot, message, seed) tuple. This is called a *seed tuple*.
- returns a *delegate*, which can be one of the following:
    - an object that has methods ``start()`` and ``is_alive()``. Therefore, a
      ``threading.Thread`` object is a natural delegate. Once returned, the
      object's ``start()`` method is called.
    - a function. Once returned, it is wrapped in a ``Thread(target=function)``
      and started.
    - a (function, args, kwargs) tuple. Once returned, it is wrapped in a
      ``Thread(target=function, args=args, kwargs=kwargs)`` and started.

The above logic is implemented in the ``handle`` method.
You only have to create a :class:`.MessageLoop` with no callback
argument, the above logic will be executed for every message received.

In the list of delegation patterns, all seeder functions are evaluated in order.
One message may start multiple delegates.

The module :mod:`amanobot.delegate` has a bunch of seeder factories
and delegator factories, which greatly ease the use of DelegatorBot. The module
:mod:`amanobot.helper` also has a number of ``*Handler`` classes which provide
a connection-like interface to deal with individual chats or users.

I have given an `answer <https://stackoverflow.com/questions/45387797/how-does-the-delegatorbot-work-exactly-in-amanobot/45397368#45397368>`_
on Stack Overflow which elaborates on the inner workings of DelegatorBot in
greater details. Interested readers are encouraged to read that.

In the rest of discussions, *seed tuple* means a (bot, message, seed) tuple,
referring to the single argument taken by delegator functions.

``amanobot.delegate``
--------------------

.. automodule:: amanobot.delegate
   :members:

``amanobot.helper``
------------------

Handlers
++++++++

.. autoclass:: amanobot.helper.Monitor
   :show-inheritance:
   :members:

.. autoclass:: amanobot.helper.ChatHandler
   :show-inheritance:
   :members:

.. autoclass:: amanobot.helper.UserHandler
   :show-inheritance:
   :members:

.. autoclass:: amanobot.helper.InlineUserHandler
   :show-inheritance:
   :members:

.. autoclass:: amanobot.helper.CallbackQueryOriginHandler
   :show-inheritance:
   :members:

.. autoclass:: amanobot.helper.InvoiceHandler
   :show-inheritance:
   :members:

Contexts
++++++++

.. autoclass:: amanobot.helper.ListenerContext
   :members:
   :undoc-members:

.. autoclass:: amanobot.helper.ChatContext
   :show-inheritance:
   :members:
   :undoc-members:

.. autoclass:: amanobot.helper.UserContext
   :show-inheritance:
   :members:
   :undoc-members:

.. autoclass:: amanobot.helper.CallbackQueryOriginContext
   :show-inheritance:
   :members:
   :undoc-members:

.. autoclass:: amanobot.helper.InvoiceContext
   :show-inheritance:
   :members:
   :undoc-members:

.. autoclass:: amanobot.helper.Sender
   :members:

.. autoclass:: amanobot.helper.Administrator
   :members:

.. autoclass:: amanobot.helper.Editor
   :members:

.. autoclass:: amanobot.helper.Listener
   :members:

Mixins
++++++

.. autoclass:: amanobot.helper.Router
   :members:

.. autoclass:: amanobot.helper.DefaultRouterMixin
   :members:
   :undoc-members:

.. autoclass:: amanobot.helper.StandardEventScheduler
   :members:
   :undoc-members:

.. autoclass:: amanobot.helper.StandardEventMixin
   :members:
   :undoc-members:
   :exclude-members: StandardEventScheduler

.. autoclass:: amanobot.helper.IdleEventCoordinator
   :members:

.. autoclass:: amanobot.helper.IdleTerminateMixin
   :members:
   :undoc-members:
   :exclude-members: IdleEventCoordinator

.. autoclass:: amanobot.helper.CallbackQueryCoordinator
   :members:
   :undoc-members:

.. autoclass:: amanobot.helper.InterceptCallbackQueryMixin
   :members:
   :undoc-members:
   :exclude-members: CallbackQueryCoordinator

.. autoclass:: amanobot.helper.Answerer
   :members:

.. autoclass:: amanobot.helper.AnswererMixin
   :members:
   :undoc-members:
   :exclude-members: Answerer

Utilities
+++++++++

.. autoclass:: amanobot.helper.SafeDict
   :members:

.. autofunction:: amanobot.helper.openable

``amanobot.exception``
---------------------

.. automodule:: amanobot.exception
   :members:
   :undoc-members:

``amanobot.namedtuple``
----------------------

Amanobot's custom is to represent Bot API object as *dictionary*.
On the other hand, the module :mod:`amanobot.namedtuple` also provide namedtuple
classes mirroring those objects. The reasons are twofold:

1. Under some situations, you may want an object with a complete set of fields,
   including those whose values are ``None``. A dictionary translated from Bot API's response
   would have those ``None`` fields absent. By converting such a dictionary to a namedtuple,
   all fields are guaranteed to be present, even if their values are ``None``.
   This usage is for **incoming** objects received from Telegram servers.

2. Namedtuple allows easier construction of objects like
   `ReplyKeyboardMarkup <https://core.telegram.org/bots/api#replykeyboardmarkup>`_,
   `InlineKeyboardMarkup <https://core.telegram.org/bots/api#inlinekeyboardmarkup>`_,
   and various `InlineQueryResult <https://core.telegram.org/bots/api#inlinequeryresult>`_, etc.
   This usage is for **outgoing** objects sent to Telegram servers.

Incoming objects include:

- `User <https://core.telegram.org/bots/api#user>`_
- `Chat <https://core.telegram.org/bots/api#chat>`_
- `Message <https://core.telegram.org/bots/api#message>`_
- `MessageEntity <https://core.telegram.org/bots/api#messageentity>`_
- `PhotoSize <https://core.telegram.org/bots/api#photosize>`_
- `Audio <https://core.telegram.org/bots/api#audio>`_
- `Document <https://core.telegram.org/bots/api#document>`_
- `Sticker <https://core.telegram.org/bots/api#sticker>`_
- `Video <https://core.telegram.org/bots/api#video>`_
- `Voice <https://core.telegram.org/bots/api#voice>`_
- `VideoNote <https://core.telegram.org/bots/api#videonote>`_
- `Contact <https://core.telegram.org/bots/api#contact>`_
- `Location <https://core.telegram.org/bots/api#location>`_
- `Venue <https://core.telegram.org/bots/api#venue>`_
- `UserProfilePhotos <https://core.telegram.org/bots/api#userprofilephotos>`_
- `File <https://core.telegram.org/bots/api#file>`_
- `ChatPhoto <https://core.telegram.org/bots/api#chatphoto>`_
- `ChatMember <https://core.telegram.org/bots/api#chatmember>`_
- `CallbackQuery <https://core.telegram.org/bots/api#callbackquery>`_
- `InlineQuery <https://core.telegram.org/bots/api#inlinequery>`_
- `ChosenInlineResult <https://core.telegram.org/bots/api#choseninlineresult>`_
- `Invoice <https://core.telegram.org/bots/api#invoice>`_
- `ShippingAddress <https://core.telegram.org/bots/api#shippingaddress>`_
- `OrderInfo <https://core.telegram.org/bots/api#orderinfo>`_
- `ShippingQuery <https://core.telegram.org/bots/api#shippingquery>`_
- `PreCheckoutQuery <https://core.telegram.org/bots/api#precheckoutquery>`_
- `SuccessfulPayment <https://core.telegram.org/bots/api#successfulpayment>`_

Outgoing objects include:

- `ReplyKeyboardMarkup <https://core.telegram.org/bots/api#replykeyboardmarkup>`_
- `KeyboardButton <https://core.telegram.org/bots/api#keyboardbutton>`_
- `ReplyKeyboardRemove <https://core.telegram.org/bots/api#replykeyboardremove>`_
- `InlineKeyboardMarkup <https://core.telegram.org/bots/api#inlinekeyboardmarkup>`_
- `InlineKeyboardButton <https://core.telegram.org/bots/api#inlinekeyboardbutton>`_
- `ForceReply <https://core.telegram.org/bots/api#forcereply>`_
- Various types of `InlineQueryResult <https://core.telegram.org/bots/api#inlinequeryresult>`_
- Various types of `InputMessageContent <https://core.telegram.org/bots/api#inputmessagecontent>`_
- `LabeledPrice <https://core.telegram.org/bots/api#labeledprice>`_
- `ShippingOption <https://core.telegram.org/bots/api#shippingoption>`_

``amanobot.routing``
-------------------

.. automodule:: amanobot.routing
   :members:

``amanobot.text``
----------------

.. automodule:: amanobot.text
   :members:

``amanobot.api``
----------------

.. automodule:: amanobot.api
   :members:
