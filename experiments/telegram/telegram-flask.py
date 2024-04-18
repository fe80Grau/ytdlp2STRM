from flask import Flask, request, Response, stream_with_context
from telethon import TelegramClient
import re

# Initialization of the Telegram client
api_id = '27321181'  # replace with your api_id
api_hash = '28fa09fe080446d6215b8bac3802762a'  # replace with your api_hash
client = TelegramClient('session_name', api_id, api_hash)
app = Flask(__name__)

CHUNK_SIZE = 64 * 1024  # 64 KB

def download_generator(client, document, start, end):
    pos = start
    remaining = end - start + 1
    async def download():
        async for chunk in client.iter_download(document, offset=pos, limit=remaining):
            yield chunk
            remaining -= len(chunk)
            if remaining <= 0:
                break
    return download()

@app.route("/telegram/direct/<telegram_id>")
def telegram_direct(telegram_id):
    video_id = int(telegram_id)
    if not video_id:
        return "Video ID is required", 400

    client.loop.run_until_complete(client.start())
    message = client.loop.run_until_complete(client.get_messages('pokemontvcastellano', ids=[video_id]))
    if not message or not hasattr(message[0], 'media'):
        return "Message not found or it doesn't contain any media", 404

    document = message[0].media.document
    file_size = document.size

    range_header = request.headers.get("Range")
    start, end = 0, file_size - 1  # Default assumption
    headers = {
        "Accept-Ranges": "bytes",
    }

    if range_header:
        match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if match:
            start, end = match.groups()
            start = int(start)
            end = int(end) if end else file_size - 1

            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(end - start + 1)
            status_code = 206  # Partial Content
        else:
            return "Invalid Range header", 416  # Range Not Satisfiable
    else:
        status_code = 200  # OK
        headers["Content-Length"] = str(file_size)

    return Response(stream_with_context(download_generator(client, document, start, end)), status=status_code, headers=headers, content_type="video/mp4")

if __name__ == '__main__':
    app.run(port=5051)
