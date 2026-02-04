from alphagram import Client, filters
from alphagram.errors import FloodWait
from config import SESSION_STRING
import asyncio
import traceback
import os
from flask import Flask
import threading

flask_app = Flask(__name__)

app = Client("FORWARDER", use_default_api=True, session_string=SESSION_STRING)

logs = []
task = None
s, f = 0, 0
caption = ''

not_allowed = []

async def forward(chat_id: int, fwd_id: int, st: int, en: int):
    global s, f

    c = st
    while c <= en:
        try:
            batch_end = min(c + 199, en)
            msgs = await app.get_messages(chat_id, list(range(c, batch_end + 1)))
            if not isinstance(msgs, list):
                msgs = [msgs]
            for msg in msgs:
                if not msg:
                    c += 1
                    continue
                if msg.text and 'text' in not_allowed:
                    continue
                elif msg.photo and 'photo' in not_allowed:
                    continue
                elif msg.video and 'video' in not_allowed:
                    continue
                elif msg.animation and 'gif' in not_allowed:
                    continue
                elif msg.audio and 'audio' in not_allowed:
                    continue
                elif msg.voice and 'voice' in not_allowed:
                    continue
                elif msg.document and 'file' in not_allowed:
                    continue
                await msg.copy(fwd_id, caption=caption)
                s += 1
                c += 1
                await asyncio.sleep(0.25)

        except FloodWait as e:
            t = e.value if isinstance(e.value, int) else 30
            await asyncio.sleep(t)
            logs.append(f"Sleeping for {t}s.")

        except Exception:
            logs.append(traceback.format_exc())
            f += 1
            c += 1


@app.on_message(filters.command("a", '.') & filters.me)
async def allow_handler(_, m):
    types_ = ['text', 'photo', 'video', 'gif', 'audio', 'voice', 'file']
    txt = ''
    for type_ in types_:
        if type_ in not_allowed:
            txt += f'`.{type_}` ❌\n'
        else:
            txt += f'`.{type_}` ✅\n'
    await m.edit(txt)
    

@app.on_message(filters.command(['text', 'photo', 'video', 'gif', 'audio', 'voice', 'file'], '.') & filters.me)
async def uf_handler(_, m):
    type_ = m.text.split()[0][1:]
    if type_ in not_allowed:
        not_allowed.remove(type_)
        txt = f'Enabled {type_} ✅'
    else:
        not_allowed.append(type_)
        txt = f'Disabled {type_} ❌'
    await m.edit(txt)


@app.on_message(filters.command("id", '.') & filters.me)
async def id_handler(_, m):
    if m.reply_to_message:
        txt = f'Chat ID: `{m.chat.id}`\nMsg ID: `{m.reply_to_message.id}`'
    else:
        txt = f'Chat ID: `{m.chat.id}`'
    await m.edit(txt)


@app.on_message(filters.command("caption", '.') & filters.me)
async def caption_handler(_, m):
    global caption
    spl = m.text.split()
    if len(spl) > 1:
        caption = " ".join(spl[1:])
    else:
        if caption:
            return await m.edit(f"Caption was set to '{caption}'")
        else:
            return await m.edit(f"No Caption.")
    await m.edit(f"Caption was set to '{caption}'")


@app.on_message(filters.command("dcaption", '.') & filters.me)
async def dcaption_handler(_, m):
    global caption
    caption = ''
    await m.edit("Caption removed.")


@app.on_message(filters.command("logs", '.') & filters.me)
async def logs_handler(_, m):
    if not logs:
        return await m.edit("No Logs Stored.")
    with open("logs.txt", "w") as e:
        e.write("/n/n".join(logs))
    await m.reply_document("logs.txt")
    os.remove("logs.txt")


@app.on_message(filters.command('f', '.') & filters.me)
async def f_handler(_, m):
    global task, s, f

    if task:
        return await m.edit("A process is already running, use /cancel to cancel.") 

    try:
        spl = m.text.split()
        chat_id = int(spl[1])
        st_id, en_id = int(spl[2]), int(spl[3])
        fwd_id = m.chat.id
    except:
        traceback.print_exc()
        return await m.edit('.f from_chat_id start end')

    ok = await m.edit("forwarding...\n\nVisit the hosted URL for progress.")

    s, f = 0, 0
    task = asyncio.create_task(forward(chat_id, fwd_id, st_id, en_id))

    try:
        await task
    except:
        pass
    finally:
        task = None
        txt = f"Forwarded\n\n{s=}\n{f=}"
        s, f = 0, 0
        await ok.edit(txt)

    
@app.on_message(filters.command('cancel', '.') & filters.me)
async def cancel_handler(_, m):
    if not task:
        return await m.edit("No Task is going.")
    task.cancel()
    await m.edit("Cancelled.")


@flask_app.route('/')
def index():
    if not task:
        return "No Task is going.", 200
    return f"{s=}\n{f=}", 200


port = int(os.getenv("PORT", 8000))
threading.Thread(target=flask_app.run, kwargs={'host': '0.0.0.0', 'port': port}, daemon=True).start()
app.run(print("Started."))
