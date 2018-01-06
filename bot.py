#!/usr/bin/python3
import argparse
import logging as log
import sys
import discord
import asyncio
import urllib
import json
import random
import os
import pickle
import time
import aiofiles
import aiohttp

valid_games = [
    "PUBG",
    "OVERWATCH",
    "QUAKE",
    "ELITE",
    "TITANFALL",
    "DBD",
    "ROCKET LEAGUE",
    "MINECRAFT",
    "GTA",
    "GUARDIANS",
    "CIV",
    "JACKBOX",
    "RAINBOW_SIX"
]

#Rate limiter config
message_limit = 3
cooldown_seconds = 30
#Rate limiter global variables
message_count = 0
previous_author = None
previous_timestamp = None

parser = argparse.ArgumentParser(description="Handle the #on_hand_volunteers channel.")
parser.add_argument("-v", "--verbose", dest="verbose", action="store_const",
                    const=True, default=False,
                    help="verbose output")
parser.add_argument("-q", "--quiet", dest="quiet", action="store_const",
                    const=True, default=False,
                    help="only output warnings and errors")
parser.add_argument("token", metavar="token", action="store",
                    help="discord auth token for the bot")
args = parser.parse_args()

if args.verbose:
    log.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", level=log.DEBUG, stream=sys.stdout)
    log.debug("Verbose output enabled")
elif args.quiet:
    log.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", level=log.WARNING, stream=sys.stdout)
else:
    log.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", level=log.INFO, stream=sys.stdout)

log.info("Started")

client = discord.Client()

def get_channel(requested_channel):
    for channel in server.channels:
        if channel.name == requested_channel:
            return(channel)
    else:
        log.error("The #{0} channel does not exist".format(requested_channel))
        return False

def get_role(requested_role):
    for role in server.roles:
        if role.name == requested_role:
            return(role)
    else:
        log.error("The {0} role does not exist".format(requested_role))
        return False

def get_members_by_role(role):
    members = []
    for member in server.members:
        for member_role in member.roles:
            if member_role.name == role:
                members.append(member)
                break
    return(members)

@client.event
async def on_ready():
    global server
    global channels
    global roles

    log.info("Connected to discord")
    log.debug("Logged in as:")
    log.debug("User: {0}".format(client.user.name))
    log.debug("ID: {0}".format(client.user.id))

    # Hardcoded server ID for Waifus4Lifu
    server = client.get_server("160165796562075649")
    channels = dict()
    roles = dict()

    log.info("Connected to server: {0}".format(server.name))

    #Update the 'playing' status message every 5-10 minutes from playing.txt
    while True:
        playing = open(os.path.join(sys.path[0], 'playing.txt')).read().splitlines()
        playing = random.choice(playing)
        if playing[:1] == "0":
            status = discord.Status.online
        elif playing[:1] == "1":
            status = discord.Status.idle
        else:
            status = discord.Status.dnd
        await client.change_presence(game=discord.Game(name=playing[1:]), status=status)
        await asyncio.sleep(random.randint(300, 600))

@client.event
async def on_member_join(member):
    await client.add_roles(member, get_role("noobs"))
    await asyncio.sleep(30)
    msg = "Hey {0}, I'm WaifuBot. I manage various things on the Waifus_4_Lifu discord server.\n".format(member.name)
    msg += "If I could feel emotions, I'm sure I'd be glad you've accepted the invite.\n\nBefore we continue, what's rule #1?"
    while True:
        try:
            await client.send_message(member, msg)
        except discord.errors.Forbidden:
            msg = "{0}, {1} does not allow DMs from strangers.\nPlease manually remove their {2} role and ask them to read the rules.\nThanks!".format(get_role("bot_testers").mention, member.name, get_role("noobs").mention)
            await client.send_message(get_channel("super_waifu_chat"), msg)
            return
        reply_message = await client.wait_for_message(timeout=300, author=member)
        if reply_message == None:
            msg = "You have timed out. Please have the person who added you contact one of the @super_waifus to manually approve you.\nThanks!"
            await client.send_message(member, msg)
            msg = "{0}, {1} has timed out as a noob.".format(get_role("super_waifus").mention, member.name)
            await client.send_message(get_channel("super_waifu_chat"), msg)
            break
        elif "don't be a dick" in reply_message.content.lower() or "dont be a dick" in reply_message.content.lower():
            msg = "Yup. Thanks! granting access in 3..."
            countdown_message = await client.send_message(member, msg)
            for countdown in range(3, 0, -1):
                msg = "Yup. Thanks! granting access in {0}...".format(countdown)
                await client.edit_message(countdown_message, new_content=msg)
                await asyncio.sleep(1)
            msg = "Access Granted!"
            await client.edit_message(countdown_message, new_content=msg)
            await client.remove_roles(member, get_role("noobs"))
            msg = "Hey everyone, {0} just joined.\n\n{1}, please introduce yourself and let us know who invited you.\n\nThanks!".format(member.name, member.mention)
            await client.send_message(get_channel("general_chat"), msg)
            break
        else:
            msg = "Not quite. What's rule #1?"

@client.event
async def on_message_delete(message):
    if "-WaifuBot" in message.content:
        return
    description="Author: {0}\nChannel: {1}\nTimestamp: {2}".format(message.author.name, message.channel, message.timestamp)
    embed = discord.Embed(title="Message deleted by [see audit log]", description=description, color=0xff0000)
    if len(message.content) > 0:
        embed.add_field(name="Message", value=message.content, inline=False)
    if len(message.attachments) > 0:
        embed.add_field(name="Attachments", value=message.attachments, inline=False)
    await client.send_message(get_channel("deleted_text"), embed=embed)

@client.event
async def on_message(message):
    #Prevent WaifuBot from responding to itself
    if message.author == client.user:
        return
    member = server.get_member_named(str(message.author))

    #Post a message as WaifuBot
    if "-WaifuBot" in message.content:
        if message.channel.is_private:
            return
        authorized_users = [
            "115183069555589125", # aceat64
            "221162619497611274", # HungryNinja
            "194641296529424386", # canibalcrab
            "130586766754316288"  # PeasAndClams
        ]
        #Delay for member-side GUI update
        asyncio.sleep(1)
        if message.author.id not in authorized_users:
            await client.delete_message(message)
            return
        if len(message.attachments) == 0:
            msg = message.content.replace('-WaifuBot', '')
            await client.send_message(message.channel, msg)
        else:
            for index, attachment in enumerate(message.attachments):
                url = attachment["url"]
                file_name = url.split('/')[-1]
                msg = ""
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        data = await resp.read()
                    async with aiofiles.open(os.path.join(sys.path[0], file_name), 'wb') as file:
                        await file.write(data)
                if index == 0:
                    msg = message.content.replace('-WaifuBot', '')
                await client.send_file(message.channel, fp=os.path.join(sys.path[0], file_name), content=msg)
                os.remove(os.path.join(sys.path[0], file_name))
        await client.delete_message(message)
        notification_msg = "{user} made me say something in {channel}."
        await client.send_message(get_channel("super_waifu_chat"), notification_msg.format(user=member.mention, channel=message.channel.mention))
        return

    if not member:
        await client.send_message(message.author, "You are not a Waifu. GTFO")
        return False
        
    if message.content.lower().startswith("!games"):
        reply_msg = "The following games are currently supported:\n```"
        for game in valid_games:
            players = get_members_by_role(game)

            reply_msg += ("{0} ({1} Players)\n".format(game.ljust(14), len(players)))
        reply_msg += "```"
        await client.send_message(message.channel, reply_msg)

    elif message.content.lower().startswith("!players"):
        log.info("[{0}] Requested a list of players".format(member.name))

        message_parts = message.content.split(' ', 1)

        if len(message_parts) == 1:
            log.info("[{0}] No game specified".format(member.name))
            msg = "{user}, you didn't specify a game, are you retarded?"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        game = message_parts[1].upper()

        if game in valid_games:
            log.info("[{user}] Requested the list of players: {game}".format(user=member.name, game=game))

            players = get_members_by_role(game)

            reply_msg = "There are {player_count} players for {game}.\n\n".format(game=game, player_count=len(players))
            for player in players:
                reply_msg += ("@{0}\n".format(player.name))
            await client.send_message(message.channel, reply_msg)
        else:
            msg = "{user}, that's not a valid game, stop being stupid."
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{user}] requested to join invalid game: {game}".format(user=member.name, game=game))

    # grant access to nfsw-shitposting
    elif message.content.lower().startswith("!join shitposting"):
        # Check to see if the user already has this role
        for author_role in member.roles:
            if author_role.name == "shitty_people":
                # They did, let them know they already had it
                msg = "{user} you are already listed as a pervert."
                await client.send_message(message.channel, msg.format(user=member.mention))
                log.info("[{0}] Role already assigned".format(member))
                break
        else:
            role = get_role("shitty_people")
            if not role:
                return False
            # They didn't have the role, so add it
            await client.add_roles(member, role)
            log.info("[{0}] Role added".format(member))
            reply = "Hello {user}, you are now able to access {shitposting}. You fucking pervert."
            await client.send_message(message.channel, reply.format(user=member.mention, shitposting=get_channel("nsfw_shitposting").mention))

    elif message.content.lower().startswith("!leave shitposting"):
        # Check to see if the user has this role
        for author_role in member.roles:
            if author_role.name == "shitty_people":
                # They did, so remove the role
                await client.remove_roles(member, author_role)
                msg = "{user}, you have been removed {shitposting}. Go cry in your safe space, loser."
                await client.send_message(message.channel, msg.format(user=member.mention, shitposting=get_channel("nsfw_shitposting").mention))
                log.info("[{0}] Role removed".format(member))
                break
        else:
            # They didn't have the role, do nothing
            msg = "{user}, are you stupid? You didn't have access to {shitposting}."
            await client.send_message(message.channel, msg.format(user=member.mention, shitposting=get_channel("nsfw_shitposting").mention))
            log.info("[{0}] Role was already not assigned".format(member))

    # Add user to a game
    elif message.content.lower().startswith("!join"):
        message_parts = message.content.split(' ', 1)

        if len(message_parts) == 1:
            log.info("[{0}] No game specified".format(member.name))
            msg = "{user}, you didn't specify a game, are you retarded?"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        game = message_parts[1].upper()

        if game.upper() in valid_games:
            log.info("[{user}] requested to join game: {game}".format(user=member.name, game=game))

            # Check to see if the user already has this role
            for author_role in member.roles:
                if author_role.name == game:
                    # They did, let them know they already had it
                    msg = "{user} you are already signed in for {game}."
                    await client.send_message(message.channel, msg.format(user=member.mention, game=game))
                    log.info("[{0}] Role already assigned".format(member))
                    break
            else:
                role = get_role(game)
                if not role:
                    return False
                # They didn't have the role, so add it
                await client.add_roles(member, role)
                log.info("[{0}] Role added".format(member))
                reply = "Hello {user}, you are now signed up for {game}. People can tag you instead of EVERYONE by using `@{game}`.\n" \
                    "You can use `!leave {game}` to be removed from the list at any time."
                await client.send_message(message.channel, reply.format(user=member.mention, game=game))

                notification_msg = "{user} has signed up to play {game}! There are currently {players} players available."
                await client.send_message(get_channel("looking_for_group"), notification_msg.format(user=member.mention, game=game, players=len(get_members_by_role(game))))
        else:
            msg = "{user}, that's not a valid game, stop being stupid."
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{user}] requested to join invalid game: {game}".format(user=member.name, game=game))

    # Remove user from a game
    elif message.content.lower().startswith("!leave"):
        message_parts = message.content.split(' ', 1)

        if len(message_parts) == 1:
            log.info("[{0}] No game specified".format(member.name))
            msg = "{user}, you didn't specify a game, are you retarded?"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        game = message_parts[1].upper()

        if game in valid_games:
            log.info("[{user}] Requested to leave game: {game}".format(user=member.name, game=game))

            # Check to see if the user has this role
            for author_role in member.roles:
                if author_role.name == game:
                    # They did, so remove the role
                    await client.remove_roles(member, author_role)
                    log.info("[{0}] Role removed".format(member))
                    msg = "Hello {user}, you have been removed from list for {game}, to re-join send `!{game}` in any channel."
                    await client.send_message(message.channel, msg.format(user=member.mention, game=game))

                    notification_msg = "{user} no longer wants to play {game} like a bitch. There are currently {players} players available."
                    await client.send_message(get_channel("looking_for_group"), notification_msg.format(user=member.mention, game=game, players=len(get_members_by_role(game))))
                    break
            else:
                # They didn't have the role, do nothing
                msg = "{user}, you have already unsubscribed from the list for {game}"
                await client.send_message(message.channel, msg.format(user=member.mention, game=game))
                log.info("[{0}] Role was already not assigned".format(member))
        else:
            msg = "{user}, that's not a valid game, stop being stupid."
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{user}] requested to join invalid game: {game}".format(user=member.name, game=game))

    elif message.content.lower().startswith("!invite"):
        # Check to see if the user has this role
        for author_role in member.roles:
            if author_role.name == "super_waifus":
                message_parts = message.content.split(' ', 1)

                if len(message_parts) == 1 or message_parts[1] == "":
                    msg = "{user}, you must specify a person or reason for the invite."
                    await client.send_message(message.channel, msg.format(user=member.mention))
                    log.info("[{0}] Requested an invite but didn't give a reason".format(member))
                    return

                # Create the invite
                invite = await client.create_invite(
                    get_channel("welcome_and_rules"),
                    max_age = 86400,
                    max_uses = 1,
                    temporary = False,
                    unique = True
                )
                msg = "{user} created an invite: {reason}\nlink: {url}"
                await client.send_message(get_channel("super_waifu_chat"), msg.format(user=member.mention, reason=message_parts[1], url=invite.url))
                log.info("[{0}] Requested an invite, code: {1}".format(member, invite.code))
                break
        else:
            # They didn't have the role, do nothing
            msg = "{user}, you don't have access to create invites you cuck."
            await client.send_message(message.channel, msg.format(user=member.mention, shitposting=get_channel("nsfw_shitposting").mention))
            log.info("[{0}] Requested an invite but was denied".format(member))

    # Show a help/about dialog
    elif message.content.lower().startswith("!wtf") or message.content.lower().startswith("!help"):
        log.info("[{0}] Requested information about us".format(member.name))
        msg = "Fuck you, I'm a bot for managing various automatic rules and features of the Waifus_4_Lifu Discord chat server.\n\n" \
              "I understand the following commands:\n\n" \
              "`!help` or `!wtf` - This help message.\n" \
              "`!games` - Show a list of supported games.\n" \
              "`!players` - Who is available to play a game. Example: `!players PUBG`\n" \
              "`!join` - Add yourself to the list of people who want to play a game. Example: `!join PUBG`\n" \
              "`!leave` - Remove yourself from the list of people who want to play a game.\n" \
              "`!8ball` - Ask the magic 8 ball a question.\n" \
              "`!random` - Request a random number, chosen by fair dice roll.\n" \
              "`!sponge` - Mock previous post even if you’re not smart enough to be clever.\n" \
              "`!yeah`\n" \
              "`!shrug`\n" \
              "`!catfact`\n" \
              "`!google`\n" \
              "`!join shitposting` - Gain access to nsfw/shitposting channel.\n" \
              "`!leave shitposting` - Give up access to nsfw/shitposting channel.\n" \
              "\nIf I'm not working correctly, go fuck yourself, you aren't my boss."
        await client.send_message(message.channel, msg)

    #Allow sanicxx to go pout in AFK
    elif message.content.lower().startswith("!pout"):
        #Check if user is sanicxx
        if message.author.id != "229502929608900608":
            msg = "Just what do you think you're doing, cucko?\nNobody pouts like sanicxx."
            await client.send_file(message.channel, os.path.join(sys.path[0], 'dennis.gif'), filename=None, content=msg, tts=False)
            return
        #Check if user is in a voice channel
        if message.author.voice.voice_channel != None:
            exempt_users = [
                "229502929608900608", # sanicxx
                "131527313933336577", # MrsCyberpunk
                "239566289943789579"  # Elvistux
            ]
            #Load shitlist
            try:
                with open(os.path.join(sys.path[0], 'shitlist.dat'), 'rb') as fp:
                    shitlist = pickle.load(fp)
            except FileNotFoundError:
            #No previous file, so create an empty list
                shitlist = []
            #Get list of users in voice channel with user
            for shithead in message.author.voice.voice_channel.voice_members:
                #Check if potential shithead is exempt
                if shithead.id not in exempt_users:
                    #Check if they are not on the shitlist
                    on_list = False
                    for existing_shit in shitlist:
                        if shithead.name == existing_shit['name']:
                            on_list = True
                    if not on_list:
                        #Put the shithead on the shitlist
                        shitlist.append({
                            'name': shithead.name,
                            'reason': "Contributed to making sanicxx pout in the corner."
                        })
                        with open(os.path.join(sys.path[0], 'shitlist.dat'), 'wb') as fp:
                            pickle.dump(shitlist, fp)
                        msg = "{user}, I've added {shithead} to the shitlist for making you pout in the corner."
                        await client.send_message(message.channel, msg.format(user=message.author.mention, shithead=shithead.name))
            await client.move_member(message.author, get_channel("AFK"))
        else:
            log.error("User not in a voice channel")

    elif message.content.lower().startswith("!shitlist"):
        # Example: !shitlist
        # Example: !shitlist add @PeasAndClams#7812 cuck
        # Example: !shitlist remove @PeasAndClams#7812
        authorized_users = [
            "115183069555589125", # aceat64
            "229502929608900608"  # sanicxx
        ]

        try:
            with open(os.path.join(sys.path[0], 'shitlist.dat'), 'rb') as fp:
                shitlist = pickle.load(fp)
        except FileNotFoundError:
            # No previous file, so create an empty list
            shitlist = []

        message_parts = message.clean_content.split(' ', 3)

        if len(message_parts) == 1 or message_parts[1] == "":
            # display shitlist
            reply_msg = "There are {count} people on sanicxx's shitlist.\n\n".format(count=len(shitlist))
            for shithead in shitlist:
                if shithead['name'] == 'aceat64' and random.randint(1, 3) == 1:
                    reply_msg += ("aceat64: Too god damn awesome for his own good\n")
                elif not shithead['reason']:
                    reply_msg += ("{0}\n".format(shithead['name']))
                else:
                    reply_msg += ("{0}: {1}\n".format(shithead['name'], shithead['reason']))
            await client.send_message(message.channel, reply_msg)
        else:
            if member.id not in authorized_users:
                msg = "{user}, you aren't authorized to do this, keep trying and you might end up on sanicxx's shitlist"
                await client.send_message(message.channel, msg.format(user=member.mention))
                return

            # check if user is real
            try:
                shithead = message_parts[2]
            except IndexError:
                msg = "{user}, add/remove who? I'm not a fucking mind reader."
                await client.send_message(message.channel, msg.format(user=member.mention))
                return

            if shithead[0] == '@':
                shithead = shithead[1:]
            elif shithead[0] == '"':
                shithead = message.clean_content.split('"')[1]

            if message_parts[1].lower() == "add":
                # check if they are already on the shitlist
                for existing_shit in shitlist:
                    if shithead == existing_shit['name']:
                        msg = "{user}, that shithead {shithead} is already on the shitlist. They must have really fucked up if you are trying to add them again."
                        await client.send_message(message.channel, msg.format(user=member.mention, shithead=shithead))
                        return

                # Add them to the shitlist and write to file
                try:
                    shitlist.append({
                        'name': shithead,
                        'reason': message_parts[3]
                    })
                except IndexError:
                    shitlist.append({
                        'name': shithead,
                        'reason': None
                    })

                with open(os.path.join(sys.path[0], 'shitlist.dat'), 'wb') as fp:
                    pickle.dump(shitlist, fp)

                msg = "{user}, I've added {shithead} to the shitlist."
                await client.send_message(message.channel, msg.format(user=member.mention, shithead=shithead))
                return
            elif message_parts[1].lower() == "remove":
                # check if they are actually on the shitlist
                for existing_shit in shitlist:
                    if shithead == existing_shit['name']:
                        break
                else:
                    msg = "{user}, that fucker {shithead} isn't on the shitlist... yet."
                    await client.send_message(message.channel, msg.format(user=member.mention, shithead=shithead))
                    return

                # Remove them to the shitlist and write to file
                shitlist[:] = [d for d in shitlist if d.get('name') != shithead]

                with open(os.path.join(sys.path[0], 'shitlist.dat'), 'wb') as fp:
                    pickle.dump(shitlist, fp)

                msg = "{user}, I've removed {shithead} from the shitlist."
                await client.send_message(message.channel, msg.format(user=member.mention, shithead=shithead))
                return
            else:
                # abuse the moron for doing things wrong
                msg = "{user}, that's not a valid command you moron."
                await client.send_message(message.channel, msg.format(user=member.mention))
                return

    # RFC 1149.5 specifies 4 as the standard IEEE-vetted random number.
    # https://xkcd.com/221/
    elif message.content.lower().startswith("!random"):
        await client.send_message(message.channel, "{user}, 4".format(user=member.mention))

    # Automatically fix tables
    elif "┻━┻" in message.content:
        await client.send_message(message.channel, "┬──┬ ﾉ(° -°ﾉ)\n{user} that wasn't nice.".format(user=member.mention))

    # #yeah
    elif message.content.lower().startswith("!yeah"):
        await client.send_message(message.channel, "( •\_•)\n( •\_•)>⌐■-■\n(⌐■\_■)")

    # ¯\_(ツ)_/¯
    elif message.content.lower().startswith("!shrug"):
        await client.send_message(message.channel, "¯\\_(ツ)_/¯")

    # Magic 8 Ball
    elif message.content.lower().startswith("!8ball"):
        phrases = [
            "As I see it, yes",
            "Ask again later",
            "Better not tell you now",
            "Cannot predict now",
            "Concentrate and ask again",
            "Don’t count on it",
            "It is certain",
            "It is decidedly so",
            "Most likely",
            "My reply is no",
            "My sources say no",
            "Outlook good",
            "Outlook not so good",
            "Reply hazy, try again",
            "Signs point to yes",
            "Very doubtful",
            "Without a doubt",
            "Yes",
            "Yes, definitely",
            "You may rely on it.",
            "Blame Pearce"
        ]
        await client.send_message(message.channel, "{user}: {phrase}".format(user=member.mention, phrase=random.choice(phrases)))

    elif message.content.lower().startswith("!catfact"):
        cat_facts = open(os.path.join(sys.path[0], 'cat_facts.txt')).read().splitlines()
        await client.send_message(message.channel, random.choice(cat_facts))

    # Let me google that for you
    elif message.content.lower().startswith("!google"):
        message_parts = message.content.split(' ', 1)

        if len(message_parts) == 1:
            return

        help_msg = "{user}, here's the info: http://lmgtfy.com/?q={query}".format(
            user=member.mention,
            query=urllib.parse.quote(message_parts[1])
        )
        await client.send_message(message.channel, help_msg)

    #Mock previous post when you're not smart enough to come up with anything clever
    elif message.content.lower().startswith("!sponge"):
        messages = client.messages
        if len(messages) > 1:
            messages.pop()
            messages.reverse()
            for previous_message in messages:
                if previous_message.channel == message.channel and len(previous_message.content) > 0:
                    reply_message = "{0}: ".format(message.author.mention)
                    for i in range(0, len(previous_message.content)):
                        if random.randint(0,1) == 1:
                            reply_message += previous_message.content[i].lower()
                        else:
                            reply_message += previous_message.content[i].upper()
                    await client.send_file(message.channel, os.path.join(sys.path[0], 'sponge.jpg'), filename=None, content=reply_message, tts=False)
                    return
    
    #Game code lottery
    if message.content.lower().startswith("!lottery"):
        await client.send_typing(message.channel)
        await asyncio.sleep(1)
        drawing_delay = 30
        if not get_role("bot_testers") in member.roles:
            msg = "Just what do you think you're doing? You're not authorized."
            await client.send_file(message.channel, os.path.join(sys.path[0], 'dennis.gif'), filename=None, content=msg, tts=False)
            return
        msg = "Hey @everyone, {0} has initiated an indie game code lottery.\n"
        msg+= "The game code drawing will be held in {1} minutes.\n"
        msg+= "A winner will be drawn at random from those who **add a reaction to this post**.\n"
        msg+= "You can react as many times as you want, only one entry will be counted.\n"
        msg+= "Disclaimer: I believe these codes still work but make no guarantees. Good luck!"
        lottery_post = await client.send_message(message.channel, msg.format(message.author.mention, drawing_delay))
        end_time = time.time() + (drawing_delay * 60)
        entrants = []
        while time.time() < end_time:
            seconds_left = end_time - time.time()
            reaction = await client.wait_for_reaction(timeout=seconds_left)
            if reaction != None:
                if reaction.user not in entrants:
                    entrants.append(reaction.user)
        if len(entrants) == 0:
            msg = "Nobody entered the drawing. Nobody wins."
            await client.send_message(message.channel, msg)
        else:
            winner = random.choice(entrants)
            msg = "Congratulations, {0}! You have won the lottery drawing. Check your DMs for your steam code.".format(winner.mention)
            await client.send_message(message.channel, msg)
            try:
                codes = open(os.path.join(sys.path[0], 'codes.txt')).read().splitlines()
                if len(codes) > 0:
                    code = codes[0]
                    codes.pop(0)
                else:
                    code = "\nError: Code not found. Please contact PeasAndClams for details."
            except FileNotFoundError:
                code = "\nError: Code not found. Please contact PeasAndClams for details."
            msg = "Hey {0}, here is your steam code: {1}".format(winner.mention, code)
            try:
                await client.send_message(winner, msg)
            except discord.errors.Forbidden:
                msg = "{0}, {1} won the drawing but does not accept DMs. The prize code is: {3}".format(get_role("super_waifus").mention, winner.name, code)
                await client.send_message(get_channel("super_waifu_chat"), msg)
            codes_file = open(os.path.join(sys.path[0], 'codes.txt'), "w")
            for code in codes:
                codes_file.write(code + "\n")
            codes_file.close()                
                    
    #Did someone say hungry?
    lower = message.content.lower()
    if "m hungry" in lower or "s hungry" in lower or "e hungry" in lower or "y hungry" in lower:
        log.info("[{0}] said someone is/was hungry".format(member))
        if random.randint(1, 3) != 1:
            msg = "No, <@221162619497611274> is hungry."
            await client.send_file(message.channel, os.path.join(sys.path[0], 'dennis.gif'), filename=None, content=msg, tts=False)

    #Shitposting rate limiter
    if message.channel.name == "nsfw_shitposting":
        global previous_author
        global message_count
        global previous_timestamp
        #Get seconds since first message after start of cooldown
        try:
            delta = message.timestamp - previous_timestamp
            delta = delta.seconds
        except TypeError:
            delta = 0
        #Reset count if cooldown has been reached or new author has posted
        if delta > cooldown_seconds or message.author != previous_author:
            message_count = 0;
            previous_timestamp = message.timestamp
            delta = 0
        previous_author = message.author
        #Increment count by number of attachments, if any. Otherwise, increment by 1.
        if len(message.attachments) > 1:
            message_count = message_count + len(message.attachments)
        else:
            message_count = message_count + 1
        #If count is 5 or more, berate them
        if message_count > message_limit:
            msg = "**Error 429: DUMP DETECTED :poo:**\n{0}, you may not be breaking any rules, but you are being a scumbag.".format(message.author.mention)
            await client.send_message(message.channel, msg)
            log.info("[{0}] hit rate limit with {1} posts in [{2}] within {3} seconds".format(message.author, message_count, message.channel, delta))
            message_count = 0
            previous_timestamp = message.timestamp
            
    #LFG rate limiter
    elif message.channel.name == "looking_for_group" and len(client.messages) > 0 and "@" not in message.content:
        messages = reversed(client.messages)
        count = 0
        for previous_message in messages:
            if previous_message.channel.name == "looking_for_group":
                if "@" in previous_message.content:
                    break
                elif count > 8:
                    msg = "Hey {0} and friends, let's move this conversation to {1}.\nThanks!".format(message.author.mention, get_channel("general_chat").mention)
                    await client.send_message(message.channel, msg)
                    break
                count+=1

client.run(args.token)
