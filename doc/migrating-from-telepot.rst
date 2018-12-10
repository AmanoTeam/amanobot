Migrating from Telepot guide
============

If you use Telepot, but don't want to entirely rewrite your project just because Telepot was `discontinued <https://github.com/nickoala/telepot/issues/408#issuecomment-409827643>`_, Amanobot will be the best choice for you, because it is based on Telepot, with all the new Telegram API methods and functions. 

Migration
------------

To migrate from Telepot to Amanobot is very easy, you just need to replace all "telepot" occurences with "amanobot". here's a list of some things you need to change:

+--------------------+---------------------+
| Telepot            | Amanobot            |
+====================+=====================+
| telepot            | amanobot            |
+--------------------+---------------------+
| telepot.aio        | amanobot.aio        |
+--------------------+---------------------+
| telepot.loop       | amanobot.loop       |
+--------------------+---------------------+
| telepot.exception  | amanobot.exception  |
+--------------------+---------------------+
| telepot.namedtuple | amanobot.namedtuple |
+--------------------+---------------------+


-----------------------------------------------------------------------------
