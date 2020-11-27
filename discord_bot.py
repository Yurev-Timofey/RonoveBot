import os
import asyncio

import discord
from discord.ext import tasks, commands
import youtube_dl

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
        if message.author == client.user:
            return
        # elif message.channel ==

        path = "from_discord.fifo"
        if not os.path.exists(path):
            os.mkfifo(path)

        pipe = open(path, "w")
        pipe.write(message.content)
        pipe.close()


@client.event
async def on_ready():
    print('Logged in discord as {0.user}'.format(client))


print("Включить режим нейросети?(Телеграм бот не будет работать) \ny/n: ")
if input() == 'y':
    client.add_cog(ChatAI(client))
else:
    client.add_cog(Telegram(client))

client.add_cog(Music(client))
client.run(token)
