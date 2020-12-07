import os
import asyncio

import discord
from discord.ext import tasks, commands
import youtube_dl
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

client = commands.Bot(command_prefix='.')
token = open('discord_token.txt', 'r').read()

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ffmpeg_options = {
    'options': '-vn'
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def play(self, ctx, *, query):
        """Plays a file from the local filesystem"""

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(query))

    @commands.command()
    async def yt(self, ctx, *, url):
        """Plays from a url (almost anything youtube_dl supports)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def stream(self, ctx, *, url):
        """Streams from a url (same as yt, but doesn't predownload)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()

    @play.before_invoke
    @yt.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


class Telegram(commands.Cog):
    def __init__(self, client):
        self.client = client
        Telegram.check_message.start(self)

    prev_msg_id = 0
    path = "to_discord.fifo"
    if os.path.exists(path):
        os.remove(path)

    @tasks.loop(seconds=0.5)
    async def check_message(self):
        if not os.path.exists(self.path):
            return

        pipe = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)
        message = os.read(pipe, 2000).decode('utf-8')
        os.close(pipe)

        if message != '':
            msg_id, msg_text, channel_id = message.split('$space$')
            if msg_id != self.prev_msg_id:
                self.prev_msg_id = msg_id
                print("Отправлено \"{}\" в канал \"{}\"".format(msg_text, channel_id))
                await client.get_channel(int(channel_id)).send(msg_text)


class ChatAI(commands.Cog):
    def __init__(self, client):
        self.client = client
        ChatAI.check_message.start(self)

    prev_msg_id = 0
    path = "to_discord.fifo"
    if os.path.exists(path):
        os.remove(path)

    @tasks.loop(seconds=0.5)
    async def check_message(self):
        if not os.path.exists(self.path):
            return

        channel_id = 777276267837915186
        pipe = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)
        message = os.read(pipe, 2000).decode('utf-8')
        os.close(pipe)
        if message:
            msg_id, msg_text = message.split('$space$')
            if msg_id != self.prev_msg_id:
                if msg_text:
                    self.prev_msg_id = msg_id
                    print("Отправлено \"{}\" в канал \"{}\"".format(msg_text, channel_id))
                    await client.get_channel(channel_id).send(msg_text)
                else:
                    await client.get_channel(channel_id).send("Я не знаю как ответить.......")

    @staticmethod
    @client.event
    async def on_message(message):
        if message.author == client.user or message.content.startswith('.'):
            await client.process_commands(message)
            return

        path = "from_discord.fifo"
        if not os.path.exists(path):
            os.mkfifo(path)

        pipe = open(path, "w")
        pipe.write(message.content)
        pipe.close()


class CatOrDog(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    async def catordog(self, ctx):
        if len(ctx.message.attachments) == 0:
            await ctx.send("Сначала прикрепите изображение")
            return

        attachment = ctx.message.attachments[0]

        byte_img = await attachment.read()
        prediction = self.recognition(byte_img)
        prediction = str(prediction).replace('[', '').replace(']', '')
        prediction = float(prediction) * 100
        if prediction > 50:
            await ctx.send("Я уверен на {0:.1f}%, что это собакен".format(prediction))
        else:
            await ctx.send("Я уверен на {0:.1f}%, что это котшка".format(100 - prediction))

    @staticmethod
    def recognition(img_bytes):
        from keras.models import load_model
        from keras.preprocessing import image
        import numpy as np
        from PIL import Image
        import io

        model = load_model('new_model.h5')

        img = Image.open(io.BytesIO(img_bytes))
        img = img.convert('RGB')
        target_size = (150, 150)
        img = img.resize(target_size)

        img_tensor = image.img_to_array(img)
        img_tensor = np.expand_dims(img_tensor, axis=0)
        img_tensor /= 255.

        prediction = model.predict(img_tensor)
        return prediction


@client.event
async def on_ready():
    print('Logged in discord as {0.user}'.format(client))


print("Включить режим общения с нейросетью?(Телеграм бот не будет работать) \ny/n: ")
if input() == 'y':
    print("Бот работает в режиме общения с нейросетью")
    client.add_cog(ChatAI(client))
else:
    print("Бот работает в режиме отправки сообщений из telegram")
    client.add_cog(Telegram(client))

client.add_cog(Music(client))
client.add_cog(CatOrDog(client))
client.run(token)
