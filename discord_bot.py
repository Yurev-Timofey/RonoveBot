import asyncio
import os
import discord

client = discord.Client()

token = open('discord_token.txt', 'r').read()
prev_msg_id = 0
path = "pipe.fifo"
if os.path.exists(path):
    os.remove(path)


@client.event
async def on_ready():
    print('Logged in discord as {0.user}'.format(client))
    client.loop.create_task(check_telegram_message())


async def check_telegram_message():
    global prev_msg_id
    while not client.is_closed():
        if not os.path.exists(path):
            continue

        pipe = open(path, "r")
        message = pipe.read()

        if message != '':
            msg_id, msg_text, channel_id = message.split('$space$')
            if msg_id != prev_msg_id:
                prev_msg_id = msg_id
                print("Отправлено \"{}\" в канал \"{}\"".format(msg_text, channel_id))
                await client.get_channel(int(channel_id)).send(msg_text)

        pipe.close()
        await asyncio.sleep(0.5)


client.run(token)
