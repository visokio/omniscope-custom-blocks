"""Send to Telegram: sends the input records as a message to a Telegram chat through a bot.

The records are written as JSON, as a table or as text, one line per record, and sent with the Bot API's
sendMessage. Telegram allows 4,096 characters per message, so a longer text is sent as several messages, split
between records.
"""
import html
import json

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

LIMIT = 4096
PRE = len("<pre></pre>")
FIELDS = ["Part", "Parts", "Records", "Characters", "Message ID", "Chat"]


def text(value):
    """A cell or option value as trimmed text; empty for a missing value."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def cell(value):
    """A value as it reads in a message: empty for missing, dates without a time of midnight, whole numbers
    without '.0'."""
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return ""
    if isinstance(value, pd.Timestamp):
        value = value.tz_localize(None) if value.tzinfo is not None else value
        return value.strftime("%Y-%m-%d") if value == value.normalize() else value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def json_value(value):
    """A value for JSON: numbers and true/false as they are, dates as text, missing as null."""
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return cell(value)
    if hasattr(value, "item"):  # numpy scalars
        value = value.item()
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value if isinstance(value, (bool, int, float, str)) else str(value)


def as_text(df):
    """Records as rows of text values, with the field names."""
    rows = [[cell(v) for v in record] for record in df.itertuples(index=False, name=None)]
    return [str(c) for c in df.columns], rows


def units(value):
    """Length as Telegram counts it: UTF-16 code units (an emoji counts as two)."""
    return len(value.encode("utf-16-le")) // 2


def pack(pieces, header=None, budget=LIMIT, join="\n"):
    """Group pieces (one per record) into messages of at most `budget` characters, each starting with the header;
    a single piece too long for a message is cut."""
    room = budget - (units(header) + units(join) if header else 0)
    parts, current, size = [], [], 0
    for piece in pieces:
        if units(piece) > room:
            kept, used = [], 0
            for ch in piece:
                used += units(ch)
                if used > room - 1:
                    break
                kept.append(ch)
            piece = "".join(kept) + "…"
        if current and size + units(join) + units(piece) > room:
            parts.append(current)
            current, size = [], 0
        size += (units(join) if current else 0) + units(piece)
        current.append(piece)
    if current:
        parts.append(current)
    return [((header + join) if header else "") + join.join(p) for p in parts], [len(p) for p in parts]


def shown_length(message, is_html):
    """The characters Telegram counts: the text after the HTML tags and escapes are read, in UTF-16 units."""
    return units(html.unescape(message)) - PRE if is_html else units(message)


def messages_for(df, form):
    names, rows = as_text(df)
    if form == "JSON":
        records = df.astype(object).where(df.notna(), None).itertuples(index=False, name=None)
        pieces = [json.dumps(dict(zip(names, [json_value(v) for v in r])), ensure_ascii=False) for r in records]
        texts, counts = pack(pieces, budget=LIMIT - 4, join=",\n")
        return [f"[\n{t}\n]" for t in texts], counts, False
    if form == "TABLE":
        widths = [max([len(n)] + [len(r[i]) for r in rows]) for i, n in enumerate(names)]
        line = lambda values: " | ".join(v.ljust(w) for v, w in zip(values, widths)).rstrip()  # noqa: E731
        header = line(names) + "\n" + "-+-".join("-" * w for w in widths)
        pieces = [line(r) for r in rows]
        # Shown as preformatted text (fixed width, so the columns line up); <, > and & are escaped for HTML
        texts, counts = pack(pieces, header, budget=LIMIT - PRE)
        return [f"<pre>{html.escape(t, quote=False)}</pre>" for t in texts], counts, True
    pieces = [" ".join(v for v in r if v) for r in rows]
    return pack(pieces) + (False,)


api = OmniscopeApi()
form = api.get_option("text_format") or "CONCAT"
token = text(api.get_option("bot_token"))
chat = text(api.get_option("chat_id"))

data = api.read_input_records(input_number=0)
if data is None:
    api.abort("Connect the records to send.")
if not token:
    api.abort("Enter the bot token (from @BotFather in Telegram).")
if not chat:
    api.abort("Enter the chat ID: a number such as 123456789 (a group's starts with -), or @channelname.")
if form not in ("JSON", "TABLE", "CONCAT"):
    api.abort(f"Unknown format {form!r}: choose JSON, Table or Text.")

sent = []
if len(data):
    texts, counts, is_html = messages_for(data, form)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for number, (message, count) in enumerate(zip(texts, counts), start=1):
        payload = {"chat_id": chat, "text": message}
        if is_html:
            payload["parse_mode"] = "HTML"
        api.update_message(f"Sending message {number} of {len(texts)}")
        try:
            response = requests.post(url, json=payload, timeout=60)
        except requests.RequestException as exc:
            # the exception's text holds the address, which holds the token: leave it out
            api.abort(f"Could not reach Telegram ({type(exc).__name__}); {len(sent)} of {len(texts)} messages "
                      "were sent before it.")
        try:
            reply = response.json()
        except ValueError:
            reply = {"ok": False, "description": f"HTTP {response.status_code}"}
        if not reply.get("ok"):
            api.abort(f"Telegram refused message {number} of {len(texts)}: "
                      f"{reply.get('description', 'HTTP %s' % response.status_code)}.")
        result = reply.get("result") or {}
        sent.append({"Part": number, "Parts": len(texts), "Records": count, "Characters": shown_length(message, is_html),
                     "Message ID": result.get("message_id"), "Chat": str((result.get("chat") or {}).get("id", chat))})

api.write_output_records(pd.DataFrame(sent, columns=FIELDS), output_number=0)
if sent:
    api.close(f"{len(data)} record{'s' if len(data) != 1 else ''} sent in {len(sent)} "
              f"message{'s' if len(sent) != 1 else ''}.")
else:
    api.close("No records: nothing sent.")
