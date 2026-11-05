# TheDelilahBot

An English tutor that lives in a Telegram bot: you chat with it like any other contact, it replies in English and, in every message, corrects your mistakes and explains them so you can improve your written English.

> **Language policy:** the bot uses English only. Replies, corrections and explanations are all in English.

---

## The idea

Learning written English takes constant practice, and practice works best when it's a real conversation rather than an isolated exercise.

The tutor isn't just a proofreader. It's a conversation partner that **remembers** what we've talked about, brings up earlier topics again and adapts to my level.

## How it works (concept)

1. I send the tutor a message in English on Telegram.
2. The tutor answers in three parts:
   - **Reply:** its response to the conversation, in simple English suited to my level, ending with a question to keep the chat going.
   - **Correction:** my message rewritten correctly (or a compliment if it had no mistakes).
   - **Explanation:** a short explanation in English of each mistake: what was wrong and why.
3. The whole conversation is saved, so the tutor has context and can pick up topics again in later messages.

### Example

> **Me:** Yesterday I go to the cinema with my friends and we watch a horror movie.
>
> **Tutor:**
>
> *Reply:* That sounds fun! Horror movies are exciting. Were you scared? What was the name of the movie?
>
> *Correction:* Yesterday I **went** to the cinema with my friends and we **watched** a horror movie.
>
> *Explanation:* You're talking about something that happened yesterday, so the verbs must be in the past tense: "go" → "went" (irregular verb) and "watch" → "watched" (regular verb, add *-ed*).

## Planned features

- 💬 **Natural conversation** in English, on any topic.
- ✍️ **Feedback on every message:** correction and explanation, in English.
- 🧠 **Memory and history:** the tutor remembers past conversations and who I am (interests, topics, job).
- 📊 **Mistake tracking:** a log of my mistakes to find the most frequent ones.
- 🔁 **Reviews:** a periodic summary of my common mistakes, with examples to practice.
- 🎚️ **Adjustable level:** from A2 to B1, B2 and beyond as I improve.

## Architecture (high level)

```
┌──────────┐     ┌──────────────┐     ┌────────────────┐     ┌──────────┐
│ Telegram │ ──▶ │   bot.py     │ ──▶ │   AI model     │     │ Database │
│  (user)  │ ◀── │ (Python bot) │ ◀── │  (Groq)        │     │ (SQLite) │
└──────────┘     └──────┬───────┘     └────────────────┘     └────▲─────┘
                        │                                         │
                        └───────── history, profile, mistakes ────┘
```

**Current state:** the bot answers with AI and remembers the conversation. Each chat has its own conversations, saved in a SQLite database, and the last messages are sent to Groq as context (see [Conversations](#conversations)). Answers are streamed in real time and shown with rich formatting (see [Formatting and streaming](#formatting-and-streaming)). The tutor format, user profile and mistake tracking are still pending.

Planned message flow:

1. The user sends a message on Telegram.
2. `bot.py` receives it through the Telegram Bot API.
3. The bot loads the user's recent history and profile from the database.
4. It sends the message plus that context to the AI model, with instructions to answer in the *Reply / Correction / Explanation* format, in English only.
5. It saves the new message, the answer and the detected mistakes to the database.
6. It sends the answer back to the user on Telegram.

### Components

| Component | Technology | Status |
|---|---|---|
| Messaging interface | Telegram, via [`python-telegram-bot`](https://python-telegram-bot.org) (polling) | ✅ Working (text messages only) |
| Configuration | `.env` file loaded with `python-dotenv` (see [Environment variables](#environment-variables)) | ✅ Working |
| Commands menu | Registered with `set_my_commands` on startup | ✅ Working (`/new`, `/start`) |
| AI model | [Groq](https://console.groq.com) free tier, via the `groq` Python SDK | ✅ Working (with conversation history and streaming) |
| Rich formatting and live typing | Telegram [Rich Messages](https://core.telegram.org/bots/api#sendrichmessage) (Bot API 10.1+), managed in `telegram_rich.py` | ✅ Working (with plain text fallback) |
| Database: conversations and messages | SQLite (`delilah.db`), managed in `db.py` | ✅ Working |
| Database: user profile and mistakes | SQLite (new tables) | ⏳ Pending |
| Tutor format (Reply / Correction / Explanation) | Prompt for the AI model | ⏳ Pending |

### Project structure

Current files:

| File | What it does |
|---|---|
| `bot.py` | Configuration, Telegram handlers, Groq calls (streaming) and bot startup (`main()`) |
| `db.py` | SQLite database: conversations and messages |
| `telegram_rich.py` | Telegram Rich Messages and drafts (via `do_api_request`) |

**Planned layout (layers).** Before adding the tutor features, the code will be reorganized by responsibility. MVC isn't used because a bot has no views of its own (Telegram is the interface), and `python-telegram-bot` already acts as the framework.

```
TheDelilahBot/
├── main.py              ← starts the bot (registers handlers, run_polling)
├── config.py            ← reads .env (TOKEN, GROQ_MODEL, MAX_TOKENS, ...)
├── handlers/            ← Telegram side: receives messages and replies
│   ├── commands.py      ← /start, /new (later /level, /review)
│   └── messages.py      ← text messages
├── services/            ← logic, knows nothing about Telegram
│   ├── ai.py            ← Groq calls and streaming
│   └── tutor.py         ← tutor prompt, mistake detection (future)
├── storage/
│   └── db.py            ← database
└── telegram_rich.py     ← Rich Messages helpers
```

- **handlers** only translate between Telegram and the rest of the code.
- **services** hold the logic, so they can be reused if the messaging platform ever changes.
- **storage** saves and reads data.

## Commands

The commands appear in Telegram's **☰ Menu** button (next to the text box) and as suggestions when you type `/`.

| Command | What it does |
|---|---|
| `/new` | Starts a new conversation. The previous one stays saved, but it's no longer sent to the AI. |
| `/start` | Shows the welcome message. |

## Conversations

- **Each chat is separate.** Every Telegram chat has its own conversations; they never mix.
- **One active conversation per chat.** Normal messages go to the active conversation. If there isn't one, it's created automatically.
- **Resume an old conversation with a reply.** Reply (swipe or long-press → *Reply*) to an old message, and the bot continues *that* conversation. It becomes the active one, so your next messages go there too.
- **Limited context.** Only the last `HISTORY_LIMIT` messages (default 10) are sent to the AI, to stay under the free tier's token limits. Older messages stay saved in the database.
- **Errors aren't saved.** If the AI fails, nothing is stored, so you can just send your message again.

The database is the file `delilah.db`, created automatically next to `db.py` the first time the bot runs. It's ignored by git, so your conversations are never uploaded.

## Formatting and streaming

AI models write in Markdown (`**bold**`, `# headings`, lists, tables). Regular Telegram messages don't understand that syntax and show the asterisks as they are, so the bot uses Telegram's **Rich Messages** instead, which render Markdown natively.

How an answer is sent:

1. The bot asks Groq for the answer in **streaming** mode, so the text arrives in small pieces.
2. While it arrives, the bot shows it as a **draft** (`sendRichMessageDraft`): you see the answer being typed in real time. Drafts are updated at most once per second (`DRAFT_INTERVAL` in `bot.py`).
3. When the answer is complete, the bot sends the **final message** (`sendRichMessage`). Drafts are temporary, so this is the message that stays in the chat and is saved in the database.

Notes:

- **Drafts only work in private chats.** In groups, the bot just sends the final message.
- **Fallbacks:** if a draft fails, the bot stops sending drafts for that answer but still sends the final message. If the final rich message fails, the answer is sent as plain text (split into 4096-character messages). Errors are logged in the console.
- **Library support:** `python-telegram-bot` doesn't include Rich Messages yet, so `telegram_rich.py` calls them with `do_api_request`, the library's way to use newer Bot API methods.
- **Telegram app:** Rich Messages are recent (Bot API 10.1, June 2026), so keep your Telegram app updated.

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create a .env file (see "Environment variables" below)

# 4. Run the bot
python bot.py
```

## Environment variables

Create a `.env` file in the project root (it's ignored by git, so your keys stay private):

```
TOKEN=your-telegram-bot-token
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile
MAX_TOKENS=800
HISTORY_LIMIT=10
```

| Variable | Required | Description |
|---|---|---|
| `TOKEN` | Yes | Telegram bot token, from [@BotFather](https://t.me/BotFather). |
| `GROQ_API_KEY` | Yes | Groq API key, from [console.groq.com/keys](https://console.groq.com/keys) (free, no card needed). |
| `GROQ_MODEL` | Yes | Groq chat model to use, e.g. `llama-3.3-70b-versatile`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`. Don't use `guard`, `whisper` or `tts` models: they can't chat. |
| `MAX_TOKENS` | No (default `800`) | Max length of each answer, in tokens. Keeps requests under the free tier's per-minute limits. If an answer reaches it, the bot adds a "cut off" note. |
| `HISTORY_LIMIT` | No (default `10`) | How many previous messages of the conversation are sent to the AI as context. Higher means better memory but more tokens per request. |

The bot reads `.env` only when it starts, so restart it after any change.
