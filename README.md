# Errand Bot

A Telegram bot that turns a rushed message like

> milk, eggs and pick up my prescription before 6pm

into a categorised, deadline-aware errand list.

Send it plain English. It splits the message into separate items, works out
whether each one is groceries, pharmacy or a general errand, pulls out any
time you mentioned, and stores the lot in SQLite.

## Status

| Step | Feature | State |
| --- | --- | --- |
| 1 | `/start`, connect via long polling | Done |
| 2 | Free-text parsing, categories, deadlines, SQLite | Done |
| 3 | `/list` — open items grouped by category | In progress |
| 4 | `/plan` — ordered plan by deadline, then category | In progress |
| 5 | `/done <item>`, `/clear` | In progress |
| 6 | Full README with example conversation | In progress |

## How it works

Telegram doesn't push messages to your code directly. A bot registered with
[@BotFather](https://t.me/BotFather) gets a **token**, and your program talks to
`https://api.telegram.org/bot<TOKEN>/<method>` over HTTPS.

There are two ways to receive messages:

- **Long polling** — the program repeatedly asks Telegram "anything new?".
  Telegram holds the connection open until a message arrives. Needs no public
  IP, so it runs fine from a laptop. **This bot uses polling.**
- **Webhooks** — you give Telegram a public HTTPS URL and it calls you.
  More efficient at scale, but needs a public server and a TLS certificate.

Only one process may poll a given token at a time; a second copy gets a
`Conflict` error from Telegram.

## Access control

The bot is single-user by design. Rather than a password — which would sit in
your chat history forever and could be forwarded on — it checks the sender's
Telegram user id against an allowlist. Telegram verifies that id itself, so a
client cannot forge it.

Messages from anyone else are logged and ignored with no reply, since answering
"you're not authorised" only confirms the bot exists. If `ALLOWED_USER_IDS` is
unset the bot refuses to start rather than defaulting to open.

## Setup

Requires Python 3.11+.

```bash
git clone https://github.com/faj0324/errand-bot.git
cd errand-bot
python -m venv .venv
.venv/Scripts/activate        # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
TELEGRAM_BOT_TOKEN=your-token-from-botfather
ALLOWED_USER_IDS=your-telegram-user-id
```

`.env` is gitignored and must never be committed — the token is the bot's
password. To find your user id, start the bot and send it `/start`; the log
line prints the id of whoever messaged it.

Run it:

```bash
python bot.py
```

## Parsing rules

**Splitting** — on commas, semicolons, newlines, `and`, `then`, `&`, `plus`,
`also`, `as well as`, and phrases like `I should` / `I need to`. Leading filler
(`I need to`, `remind me to`, `please`) is stripped.

A run of bare shopping words with no punctuation is also split, so
`milk bread` becomes two items — but only when *every* word is a known item, so
`collect my passport` stays whole. The trade-off is that a dish name made of
two ingredients, like `chicken rice`, splits into two.

**Categories** — keyword sets. Pharmacy wins over groceries, so
"milk and paracetamol" is a pharmacy trip, not a grocery run.

| Category | Examples |
| --- | --- |
| `groceries` | milk, eggs, bread, rice, coffee, vegetables |
| `pharmacy` | medicine, prescription, painkillers, vitamins |
| `errand` | anything unmatched |

**Deadlines** — via [dateparser](https://github.com/scrapinghub/dateparser).
A time mentioned anywhere applies to every item in that message unless an item
names its own, so "milk, eggs and prescription before 6pm" puts 6pm on all
three — which is what you mean on a single trip.

Vague times get a sensible hour instead of the current time:

| You say | Deadline |
| --- | --- |
| `today` | 23:59 today |
| `tomorrow morning` | 09:00 tomorrow |
| `this afternoon` | 14:00 |
| `this evening` | 18:00 |
| `tonight` | 20:00 |
| `before 6pm` / `before 5 pm` | 18:00 / 17:00 |
| `before 5` (bare hour) | 17:00 |
| `by 9` (bare hour) | 09:00 |

A bare hour is read the way people mean it on an errand list: 1-6 is the
afternoon, 7-12 the morning. Any time already past rolls to the next day.

Four `dateparser` gaps are worked around: it matches `tomorrow` but drops the
`morning` after it, does not recognise `tonight` at all, reads `5pm` but not
`5 pm` with a space, and ignores a bare hour like `before 5` entirely.

Deadlines are stored as naive local time. Fine on one machine; this would need
timezone handling to run on a server in another region.

## Tests

```bash
python test_parsing.py
```

Covers categorisation, deadline extraction and message splitting against a
fixed reference time, so results don't drift with the real clock.

## Project layout

| File | Purpose |
| --- | --- |
| `bot.py` | Handlers, allowlist, entry point |
| `parsing.py` | Splitting, categorising, deadline extraction |
| `db.py` | SQLite schema and queries |
| `test_parsing.py` | Parser tests |
