import asyncio
from os import getenv
import discord
from discord.ext import commands
from discord_together import DiscordTogether
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
from discord_slash.model import SlashCommandOptionType
import urllib.parse, urllib.request, re
import youtube_dl

bot = commands .Bot(command_prefix='p!')
slash = SlashCommand(bot, sync_commands=True)
bot.remove_command('help') # <---- DO NOT EDIT --->

queue = []
yt_url = ''
players = {}

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
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

@slash.slash(name='greet', description='Greets the user')
async def greet_command(ctx: SlashContext):
    try:
        await ctx.send('Hello')
    except Exception as e:
        print(str(e))
        
@slash.slash(name='join', description='join the voice channel the author is in')
async def join(ctx: SlashContext):
    """Joins a voice channel"""
    try:
        await ensure_voice(ctx)
    except Exception as e:
        print(str(e))

@slash.slash(name='stop', description='Stops and disconnects bot from voice')
async def stop(ctx: SlashContext):
    """Stops and disconnects the bot from voice"""
    try:    
        await ctx.voice_client.disconnect()
    except Exception as e:
        print(str(e))
        
@slash.slash(name='play', 
             description='Plays a video from YouTube', 
             options=[
                 create_option(
                     name='url',
                     description='Link to the YT video',
                     required=True,
                     option_type=SlashCommandOptionType.STRING)])
async def play_YT(ctx: SlashContext, *, url:str):
    global yt_url
    global queue
    try:
        await ensure_voice(ctx)
        if ctx.author.voice:
            
            if 'https://' in url or 'http://' in url:
               yt_url = url
            else:
                yt_url = await getYtVideo(ctx, url) 
            
            player, info = await ytdl_source(yt_url, loop=bot.loop, stream=True)
            
            time = info['duration']
            hours = int(time / 3600)
            minutes = int(((time % 3600) / 3600) * 60)
            seconds = int((((time % 3600) % 60) / 60) * 60)
            title = info['title']
            channel = info['channel']
            channel_url = info['channel_url']
            
            if len(queue) == 0:
                embed = discord.Embed(title="Playing song:", description=f"**Channel :** [{channel}]({channel_url})\n\n[{title}]({yt_url})\n\n\nduration:  {hours if hours>=10 else ('0'+str(hours))}:{minutes if minutes>=10 else ('0'+str(minutes))}:{seconds if seconds>=10 else ('0'+str(seconds))}", color=discord.Color.green())
                await ctx.send(embed=embed)
                ctx.voice_client.play(player, after=lambda x=None: play_next(ctx.voice_client))
                queue.append(player)
            else:
                await ctx.send('**Song queued**')
                queue.append(player)
    except Exception as e:
        print(str(e))
        
async def ytdl_source(url, *, loop=None, stream=False):
    try:
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download = not stream))

        if 'entries' in data:
            data = data['entries'][0]
            
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        pcmAudio = discord.FFmpegPCMAudio(filename, **ffmpeg_options)
        return discord.PCMVolumeTransformer(pcmAudio, volume=0.25), data
    except Exception as e:
        print(str(e))

async def getYtVideo(ctx, search):
    await ctx.send(f':mag: **searching for** `{search}`')
    query_string = urllib.parse.urlencode({'search_query': search})
    htm_content = urllib.request.urlopen('http://www.youtube.com/results?' + query_string)
    search_results = re.findall(r'/watch\?v=(.{11})', htm_content.read().decode())
    url = 'http://www.youtube.com/watch?v=' + search_results[0]
    return url

def play_next(voice):
    try:
        player = queue.pop(0)
        voice.play(player, after=lambda x=None: play_next(voice))
    except:
        pass

async def ensure_voice(ctx: SlashContext):
    if ctx.author.voice:
        voice_channel: discord.VoiceChannel = ctx.author.voice.channel
        if not ctx.voice_client:
            if voice_channel.permissions_for(ctx.guild.me).connect:
                await voice_channel.connect()
            else:
                await ctx.send("*__I don't have access to this channel__*")
        elif voice_channel != ctx.voice_client.channel:
            await ctx.send("*__ I know you like peanuts, but I am in another channel right now! __* ")
            raise commands.CommandError("Author not connected to a voice channel")
    elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()
    else:
        await ctx.send("*__ It's lonely in there, please join a channel first __*")


bot.run(getenv('TOKEN'))