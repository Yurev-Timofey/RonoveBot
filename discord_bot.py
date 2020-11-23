import os
import discord
from discord.ext import tasks


client = discord.Client()
token = open('discord_token.txt', 'r').read()
prev_msg_id = 0
path = "pipe.fifo"
if os.path.exists(path):
    os.remove(path)


@client.event
async def on_ready():
    print('Logged in discord as {0.user}'.format(client))
    check_telegram_message.start()


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if "эй" in message.content.lower():
        await message.channel.send('Привет-привет!')


@tasks.loop(seconds=0.5)
async def check_telegram_message():
    global prev_msg_id

    if not os.path.exists(path):
        return

    pipe = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    message = os.read(pipe, 2000).decode('utf-8')
    os.close(pipe)

    if message != '':
        msg_id, msg_text, channel_id = message.split('$space$')
        if msg_id != prev_msg_id:
            prev_msg_id = msg_id
            print("Отправлено \"{}\" в канал \"{}\"".format(msg_text, channel_id))
            await client.get_channel(int(channel_id)).send(msg_text)


client.run(token)
