import asyncio
import discord
import datetime
import json
from decouple import config
import random
import youtube_dl


TOKEN = config("BOT_TOKEN")
ID = int(config("BOT_ID"))
client = discord.Client(intents=discord.Intents.all())

timeDict = {}
commandQueue = []

commandlist = ['-help', '-list', '-schedule', '-delete', '-info', '-time', '-play', '-pause', '-resume', '-skip', '-queue', '-stop']

voice_clients = {}

yt_dl_opts = {'format': 'bestaudio/best'}
ytdl = youtube_dl.YoutubeDL(yt_dl_opts)

ffmpeg_options = {'options': "-vn"}

musicQueue = {}
isPaused = {}

async def enqueue(message, type):
    if(type == 'new'):
                if(message.guild.id in musicQueue.keys()):
                    musicQueue[message.guild.id].append(message)
                else:
                    musicQueue[message.guild.id] = [message]
                return("Enqueued")
    elif(type == 'old'):
        musicQueue[message.guild.id].insert(0, message)
        return ''

async def play(message, type):
    try:
        voice_client = await message.author.voice.channel.connect()
        voice_clients[voice_client.guild.id] = voice_client
        isPaused[voice_client.guild.id] = False
    except:
        print("error")

    try:
        url = message.content.split()[1]
        loop = asyncio.get_event_loop()
        extractedIinfo = ytdl.extract_info(url, download=False)
        data = await loop.run_in_executor(None, lambda: extractedIinfo)
        song = data['url']
        player = discord.FFmpegPCMAudio(song, **ffmpeg_options)
        if (not isPaused[message.guild.id]):
            voice_clients[message.guild.id].play(player)
            title = extractedIinfo.get('title', None)
            if(len(title) < 32):
                await message.guild.me.edit(nick=title)
            else:
                await message.guild.me.edit(nick=title[0:31])
            return 'Playing ' + str(title + ', **added by ' + (str(message.author.name) if str(message.author.nick) == 'None' else str(message.author.nick))) + '**'
        else:
            return await enqueue(message, type)

    except Exception as err:
        if(str(err) == 'Already playing audio.'):
            return await enqueue(message, type)
        elif('HTTP error 403 Forbidden' in str(err)):
            print(err)
            return await enqueue(message, type)
        else:
            print(err)

async def queue(message):
    try:
        first = musicQueue[message.guild.id][0]
        if len(musicQueue[message.guild.id]) == 0:
            return('Queue Empty')
        else:
            index = 1
            retval = ""
            for song in musicQueue[message.guild.id]:
                link = (song.content).split(' ')[1]
                info_dict = ytdl.extract_info(link, download=False)
                retval+=str(index) + ': ' + str(info_dict.get('title', None)) +  ', **added by ' + (str(song.author.name) if str(song.author.nick) == 'None' else str(song.author.nick)) + '**\n'
                index += 1
            return retval
    except:
        return
        


async def pause(message):
    try:  
        voice_clients[message.guild.id].pause()
        isPaused[message.guild.id] = True
        return('Paused')
    except Exception as err:
        print(err)

async def resume(message):
    try:
        voice_clients[message.guild.id].resume()
        isPaused[message.guild.id] = False
        return('Resuming')
    except Exception as err:
        print(err)

async def skip(message):
    try:
        voice_clients[message.guild.id].stop()
        return('Skipping')
    except Exception as err:
        print(err)

async def stop(message):
    try:
        voice_clients[message.guild.id].stop()
        musicQueue[message.guild.id] = [message]
        await message.guild.me.edit(nick='Helper')
        await voice_clients[message.guild.id].disconnect()
        musicQueue[message.guild.id] = []
        return('Stopped')
    except Exception as err:
        print(err)

def isInteger(string):
    try:
        int(string)
        return True
    except:
        return False


def createMessagesFile():
    f = open('messages.json', 'w')
    data = {}
    json.dump(data, f, indent=2)
    f.close()


def loadMessages():
    try:
        f = open('messages.json', 'r')
    except:
        createMessagesFile()
        f = open('messages.json', 'r')

    data = json.load(f)
    f.close()
    return data


def saveMessages(data):
    f = open('messages.json', 'w')
    json.dump(data, f, indent=2)
    f.close()
    getScheduledTime()


def listMessage(message):
    data = loadMessages()
    serverid = str(message.guild.id)
    userid = str(message.author.id)
    try:
        if (len(data[serverid][userid]) == 0):
            raise Exception
        else:
            retval = 'You have the following scheduled messages: \n'
            index = 1
            for scheduledMessage in data[serverid][userid]:
                if (scheduledMessage["Active"]):
                    retval = retval + str(index) + ':```' + scheduledMessage["Message"] + '``` is scheduled at ' + (
                        datetime.datetime.strptime(scheduledMessage["Schedule Time"], '%d/%m/%Y %H:%M')).strftime(
                        '%d-%B-%Y %H:%M') + ' in <#' + scheduledMessage["Channel"] + '>\n'
                index += 1
            return retval

    except:
        return 'You have no scheduled messages'


def delMessage(message):
    data = loadMessages()
    serverid = str(message.guild.id)
    userid = str(message.author.id)
    try:
        lastIndex = len(data[serverid][userid])
        if (len(message.content.split(' ')) != 2):
            return 'Incorrect format used. Use ```-help``` to learn more '
        else:
            if (isInteger(message.content.split(' ')[1])):
                try:
                    if (int(message.content.split(' ')[1]) < 1):
                        raise Exception
                    data[serverid][userid].pop(int(message.content.split(' ')[1]) - 1)
                    saveMessages(data)
                    return 'Deleted!'
                except:
                    return 'Index out of range'
            else:
                return 'Incorrect format used. Use ```-help``` to learn more '
    except:
        return 'You have no scheduled messages'


def scheduleMessage(message):
    serverid = str(message.guild.id)
    userid = str(message.author.id)
    try:
        if (len(message.content.split("'''")) != 3):
            raise Exception

        schMessage = message.content.split("'''")[1]
        if (message.content.split("'''")[0] != '-schedule '):
            raise Exception

        args = message.content.split("'''")[2].split(' ')
        if (args[0] == ''):
            args.pop(0)
        numArgs = len(args)
        if (not (numArgs == 2 or numArgs == 3 or numArgs == 4)):
            raise Exception

        time = datetime.datetime.strptime(args[0] + ' ' + args[1], '%d/%m/%Y %H:%M')
        channel = str(message.channel.id)
        delayInMins = 0

        if (numArgs > 2):
            if (args[2][0:2] == '<#' and args[2][-1] == '>'):
                channel = args[2][2:-1]
                if (numArgs == 4):
                    delayInMins = int(args[3])
            else:
                channel = str(message.channel.id)
                delayInMins = int(args[2])

        while '```' in schMessage:
            i = schMessage.find('```')
            schMessage = schMessage[0:i] + schMessage[i + 3:]

        while schMessage[0] == '`':
            schMessage = schMessage[1:]

        while schMessage[len(schMessage) - 1] == '`':
            schMessage = schMessage[0:len(schMessage) - 2]

        newschedule = {
            "Message": schMessage,
            "Channel": channel,
            "Active": True,
            "Schedule Time": time.strftime('%d/%m/%Y %H:%M'),
            "isRepetitive": ((delayInMins >= 360) and (delayInMins <= 5256000)),
            "Repetition Time in minutes": delayInMins
        }

        messageData = loadMessages()

        if (serverid in messageData.keys()):
            if (userid in messageData[serverid].keys()):
                messageData[serverid][userid].append(newschedule)
            else:
                messageData[serverid][userid] = [newschedule]
        else:
            newuser = {
                userid: [newschedule]
            }
            messageData[serverid] = newuser

        if (len(messageData[serverid][userid]) < 10):
            saveMessages(messageData)
            return 'Message Scheduled'

        else:
            return 'Message Limit Reached'

    except:
        return 'Incorrect format, use -help to know more'


async def sendmessage(channel, message):
    channel = client.get_channel(int(channel))
    await channel.send(message)


async def parseCommand(message):
    command = message.content
    info = '''
        ```Message scheduler for discord by bjsbrar
        https://github.com/bjsbrar/DiscordMessageScheduler
        Waring: Bad Code``` 
    '''
    help = '''
```Command List:
  -help     : List Commands
  -info     : Bot Information
  -list     : Provides a list of all scheduled messages
  -schedule : Schedules a message\n''' + "              Usage: -schedule '''[message text]''' [Schedule Date (format: DD/MM/YYYY)] [Schedule Time (format: HH:MM)] *[#message channel] *[Repetetion time in minutes]\n" + '''
              * Optional Parameters
              Repetetion time must be 6 hours (360 minutes) or more to avoid spamming 
  -delete   : Deletes a scheduled message at a given index 
              Usage: -delete [index]
  -time     : Displays server time```'''

    if (command.split(' ')[0] == '-help'):
        await sendmessage(message.channel.id, help)
    elif (command.split(' ')[0] == '-delete'):
        await sendmessage(message.channel.id, delMessage(message))
    elif (command.split(' ')[0] == '-list'):
        await sendmessage(message.channel.id, listMessage(message))
    elif (command.split(' ')[0] == '-schedule'):
        await sendmessage(message.channel.id, scheduleMessage(message))
    elif (command.split(' ')[0] == '-info'):
        await sendmessage(message.channel.id, info)
    elif (command.split(' ')[0] == '-time'):
        await sendmessage(message.channel.id, datetime.datetime.now().strftime('%d-%B-%Y %H:%M'))
    elif (command.split(' ')[0] == '-play'):
        await sendmessage(message.channel.id, await play(message, 'new'))
    elif (command.split(' ')[0] == '-pause'):
        await sendmessage(message.channel.id, await pause(message))
    elif (command.split(' ')[0] == '-resume'):
        await sendmessage(message.channel.id, await resume(message))
    elif (command.split(' ')[0] == '-skip'):
        await sendmessage(message.channel.id, await skip(message))
    elif(command.split(' ')[0] == '-queue'):
        await sendmessage(message.channel.id, await queue(message))
    elif (command.split(' ')[0] == '-stop'):
        print(message.channel)
        await sendmessage(message.channel.id, await stop(message))


def getScheduledTime():
    data = loadMessages()
    for serverid in data.keys():
        for userid in data[serverid].keys():
            index = 0
            for message in data[serverid][userid]:
                try:
                    timeDict[(message["Schedule Time"])].append([serverid, userid, index])
                except:
                    timeDict[(message["Schedule Time"])] = [[serverid, userid, index]]
                index = index + 1


async def sendScheduledMessage(timeInfo):
    print('Sending Message')
    data = loadMessages()
    for messageInfo in timeInfo:
        serverid, userid, index = messageInfo
        if data[serverid][userid][index]["Active"]:
            await sendmessage(data[serverid][userid][index]["Channel"], data[serverid][userid][index]["Message"])
            if data[serverid][userid][index]["isRepetitive"]:
                now = datetime.datetime.strptime(data[serverid][userid][index]["Schedule Time"], '%d/%m/%Y %H:%M')
                now += datetime.timedelta(minutes=data[serverid][userid][index]["Repetition Time in minutes"])
                data[serverid][userid][index]["Schedule Time"] = now.strftime('%d/%m/%Y %H:%M')
            else:
                data[serverid][userid].pop(index)
    saveMessages(data)


async def idle():
    global timeDict
    global commandQueue
    getScheduledTime()

    while True:
        now = datetime.datetime.now()
        now = now.strftime('%d/%m/%Y %H:%M')
        try:
            await sendScheduledMessage(timeDict[now])
        except:
            try:
                message = commandQueue.pop(0)
                await parseCommand(message)
            except:
                await asyncio.sleep(1)
            try:    
                for guild in musicQueue.keys():
                    try:    
                        song = musicQueue[guild].pop(0)
                        await sendmessage(song.channel.id,await play(song, 'old'))
                    except:
                        await asyncio.sleep(0.1)
            except:
                await asyncio.sleep(1)


@client.event
async def on_ready():
    await idle()


@client.event
async def on_message(message):
    global commandQueue
    if (message.author.id != ID):
        print(message.content + ' in ' + str(client.get_channel(message.channel.id)))
        if ((str(message.content).split(' '))[0] in commandlist):
            try:
                commandQueue.append(message)
            except:
                commandQueue = [message]
        

client.run(TOKEN)

