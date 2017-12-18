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

@client.event
async def on_message(message):
    #Prevent WaifuBot from responding to itself
    if message.author == client.user:
        return
    member = server.get_member_named(str(message.author))

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

    # grant access to nfsw-shitposting
    elif message.content.lower().startswith("!iamapervert"):
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

    elif message.content.lower().startswith("!iamaloser"):
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
    elif message.content.lower().startswith("!wtf"):
        log.info("[{0}] Requested information about us".format(member.name))
        msg = "Fuck you, I'm a bot for managing various automatic rules and features of the Waifus_4_Lifu Discord chat server.\n\n" \
              "I understand the following commands:\n\n" \
              "`!wtf` - This about message.\n" \
              "`!games` - Show a list of supported games.\n" \
              "`!players` - Who is available to play a game. Example: `!players PUBG`\n" \
              "`!join` - Add yourself to the list of people who want to play a game. Example: `!join PUBG`\n" \
              "`!leave` - Remove yourself from the list of people who want to play a game.\n" \
              "`!8ball` - Ask the magic 8 ball a question.\n" \
              "`!random` - Request a random number, chosen by fair dice roll.\n" \
              "`!yeah`\n" \
              "`!shrug`\n" \
              "`!catfact`\n" \
              "`!google`\n" \
              "`!iamapervert` - Gain access to nsfw channels.\n" \
              "`!iamaloser` - Give up access to nsfw channels.\n\n" \
              "These seasonal commands may also be used:\n\n" \
              "`!naughty` - Join the W4L secret santa gift exchange.\n" \
              "`!nice` - Leave the W4L secret santa gift exchange.\n" \
              "`!hailsanta` - Show the current naughty list.\n" \
              "`!itsbeginningtolookalotlikechristmas` - Process the list and DM participants. (admin)\n" \
              "`!noticemesanta` - Send reminder DMs to all participants. (admin)\n" \
              "`!christmasdaddy` - Ask me to remind you of your secret child by DM.\n" \
              "\nIf I'm not working correctly, go fuck yourself, you aren't my boss."
        await client.send_message(message.channel, msg)

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

        message_parts = message.content.split(' ', 3)

        if len(message_parts) == 1 or message_parts[1] == "":
            # display shitlist
            reply_msg = "There are {count} people on sanicxx's shitlist.\n\n".format(count=len(shitlist))
            for shithead in shitlist:
                if shithead['name'] == 'aceat64' and random.randint(1, 3) == 1:
                    reply_msg += ("@aceat64: Too god damn awesome for his own good\n")
                elif not shithead['reason']:
                    reply_msg += ("@{0}\n".format(shithead['name']))
                else:
                    reply_msg += ("@{0}: {1}\n".format(shithead['name'], shithead['reason']))
            await client.send_message(message.channel, reply_msg)
        else:
            if member.id not in authorized_users:
                msg = "{user}, you aren't authorized to do this, keep trying and you might end up on sanicxx's shitlist"
                await client.send_message(message.channel, msg.format(user=member.mention))
                return

            # check if user is real
            try:
                shithead = server.get_member(message_parts[2][2:-1])
            except IndexError:
                msg = "{user}, add/remove who? I'm not a fucking mind reader."
                await client.send_message(message.channel, msg.format(user=member.mention))
                return

            if not shithead:
                msg = "{user}, you have to specify a user (with a mention), this isn't rocket science..."
                await client.send_message(message.channel, msg.format(user=member.mention))
                return

            if message_parts[1].lower() == "add":
                # check if they are already on the shitlist
                for existing_shit in shitlist:
                    if shithead.name == existing_shit['name']:
                        msg = "{user}, that shithead {shithead} is already on the shitlist. They must have really fucked up if you are trying to add them again."
                        await client.send_message(message.channel, msg.format(user=member.mention, shithead=shithead.name))
                        return

                # Add them to the shitlist and write to file
                try:
                    shitlist.append({
                        'name': shithead.name,
                        'reason': message_parts[3]
                    })
                except IndexError:
                    shitlist.append({
                        'name': shithead.name,
                        'reason': None
                    })

                with open(os.path.join(sys.path[0], 'shitlist.dat'), 'wb') as fp:
                    pickle.dump(shitlist, fp)

                msg = "{user}, I've added {shithead} to the shitlist."
                await client.send_message(message.channel, msg.format(user=member.mention, shithead=shithead.name))
                return
            elif message_parts[1].lower() == "remove":
                # check if they are actually on the shitlist
                for existing_shit in shitlist:
                    if shithead.name == existing_shit['name']:
                        break
                else:
                    msg = "{user}, that fucker {shithead} isn't on the shitlist... yet."
                    await client.send_message(message.channel, msg.format(user=member.mention, shithead=shithead.name))
                    return

                # Remove them to the shitlist and write to file
                shitlist[:] = [d for d in shitlist if d.get('name') != shithead.name]

                with open(os.path.join(sys.path[0], 'shitlist.dat'), 'wb') as fp:
                    pickle.dump(shitlist, fp)

                msg = "{user}, I've removed {shithead} from the shitlist."
                await client.send_message(message.channel, msg.format(user=member.mention, shithead=shithead.name))
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
        cat_facts = open(sys.path[0] + '/cat_facts.txt').read().splitlines()
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

    #Add self to naughty_list
    elif message.content.lower().startswith("!naughty"):
        #Check for existing role
        for author_role in member.roles:
            if author_role.name == "naughty_list":
                #They already have the role
                msg = "{user}, you are already on the naughty list."
                await client.send_message(message.channel, msg.format(user=member.mention))
                log.info("[{0}] Role already assigned".format(member))
                break
        else:
            #They didn't have the role, assign it to them
            role = get_role("naughty_list")
            if not role:
                return
            await client.add_roles(member, role)
            log.info("[{0}] Role added".format(member))
            reply = "{user}, you have been added to the naughty list."
            await client.send_message(message.channel, reply.format(user=member.mention))

    #Remove self from secret santa
    elif message.content.lower().startswith("!nice"):
        #Check for existing role
        for author_role in member.roles:
            if author_role.name == "naughty_list":
                #They have the role, revoke it
                await client.remove_roles(member, author_role)
                msg = "{user}, you managed to take yourself off the naughty list but we all know you'll be back on it soon."
                await client.send_message(message.channel, msg.format(user=member.mention))
                log.info("[{0}] Role removed".format(member))
                break
        else:
            #They didn't have the role, berate them and do nothing
            msg = "{user}, are you stupid? You weren't on the list, but I can think of another list where you belong..."
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{0}] Role removed".format(member))

    #Request current naughty_list
    elif message.content.lower().startswith("!hailsanta"):
        log.info("[{0}] Requested the naughty list".format(member.name))
        elves = get_members_by_role("naughty_list")
        if len(elves) == 1:
            reply_msg = "There is 1 naughty elf or your shelf.\n\n"
        else:
            reply_msg = "There are {count} naughty elves on your shelves.\n\n".format(count=len(elves))
        for elf in elves:
            reply_msg += ("{0}\n".format(elf.name))
        await client.send_message(message.channel, reply_msg)

    #Process list and assign santas
    elif message.content.lower().startswith("!itsbeginningtolookalotlikechristmas"):
        authorized_users = [
            "115183069555589125", # aceat64
            "221162619497611274", # HungryNinja
            "130586766754316288"  # PeasAndClams
        ]
        if member.id not in authorized_users:
            await client.send_file(message.channel, 'dennis.gif')
            msg = "Just what do you think you're doing, cucko?\nYou're not the boss of me."
            await client.send_message(message.channel, msg)
            return
        log.info("[{0}] Requested processing the list".format(member.name))

        #Make sure there are at least two naughty elves
        elves = get_members_by_role("naughty_list")
        if len(elves) < 2:
            log.info("Not enough naughty elves")
            msg = "YOU MUST CONSTRUCT ADDITIONAL ELVES"
            await client.send_message(message.channel, msg)
        else:
            #Deputize naughty elves as Santas
            santas = []
            children = []
            for elf in elves:
                santas.append(elf)
                children.append(elf)
            santas1 = []
            children1 = []
            #Randomly assign giver/receiver pairs
            while len(santas) > 0:
                santa = random.choice(santas)
                child = random.choice(children)
                #If the pair is valid or is the last option, store giver/receiver to arrays
                if child != santa or len(santas) == 1:
                    santas1.append(santa)
                    children1.append(child)
                    santas.remove(santa)
                    children.remove(child)
            #If the last participant is assigned to themselves, switch the last and second-last receiver
            if santas1[-1] == children1[-1]:
                temp = children1[-1]
                children1[-1] = children1[-2]
                children1[-2] = temp
            #Log results with pickle and DM each deputy santa the name of their child
            naughtylist = []
            for index, santa in enumerate(santas1):
                log.info(santa.name + ", your child is " + children1[index].name + ".")
                msg = "Deputy Santa " + santa.name + ", your secret child (I know that sounds weird) is " + children1[index].name
                try:
                    await client.send_message(santa, msg)
                except:
                    log.error("Bot is on naughty_list")
                try:
                    naughtylist.append(santa)
                    naughtylist.append(children1[index])
                except IndexError:
                    log.error("Santa index error")
            with open(os.path.join(sys.path[0], 'naughtylist.dat'), 'wb') as fp:
                pickle.dump(naughtylist, fp)
            msg = "Dear degenerates on the {0}, I've slid into your DMs and let's just say I left a little something in your stockings.".format(get_role("naughty_list").mention)
            await client.send_message(message.channel, msg)


    elif message.content.lower().startswith("!christmasdaddy"):
        log.info("[{0}] requested a private secret santa reminder".format(member))
        try:
            with open(os.path.join(sys.path[0], 'naughtylist.dat'), 'rb') as fp:
                naughtylist = pickle.load(fp)
        except FileNotFoundError:
            # No assigned pairs yet
            await client.send_file(message.channel, 'dennis.gif')
            msg = "Whoa Rudolph, you're getting ahead of the game here.\nThe list hasn't even been processed yet."
            await client.send_message(message.channel, msg)
            return
        msg = "{user}, check your DMs. I've heard that's where it's going down."
        await client.send_message(message.channel, msg.format(user=member.mention))
        while len(naughtylist)>1:
            santa = naughtylist.pop(0)
            child = naughtylist.pop(0)
            if santa == message.author:
                msg = "Some Santa you are, " + santa.name + ". You forgot about " + child.name + "."
                log.info(msg)
                await client.send_message(message.author, msg)
                return
        #Their name was not found
        msg = "Looks like you fucked up, " + message.author.name + ", your name isn't on the list.\nBetter luck next year!"
        await client.send_message(message.author, msg)

    #Send reminder DMs to all participants
    elif message.content.lower().startswith("!noticemesanta"):
        log.info("[{0}] requested mass reminder".format(member))
        authorized_users = [
            "115183069555589125", # aceat64
            "221162619497611274", # HungryNinja
            "130586766754316288"  # PeasAndClams
        ]
        if member.id not in authorized_users:
            await client.send_file(message.channel, 'dennis.gif')
            msg = "Just what do you think you're doing, cucko?\nYou're not the boss of me."
            await client.send_message(message.channel, msg)
            return
        try:
            with open(os.path.join(sys.path[0], 'naughtylist.dat'), 'rb') as fp:
                naughtylist = pickle.load(fp)
        except FileNotFoundError:
            #No assigned pairs yet
            msg = "You must have forgotten that there is nothing to remember."
            await client.send_message(message.channel, msg)
            return
        while len(naughtylist)>1:
            santa = naughtylist.pop(0)
            child = naughtylist.pop(0)
            msg = "Hey " + santa.name + ", just a reminder, if you are mailing your gift, it should be sent with enough time to arrive by December 20th.\nAlso, I'm sure you are well aware, but your secret child is " + child.name + "."
            await client.send_message(santa, msg)
        return

    #Did someone say hungry?
    lower = message.content.lower()
    if "m hungry" in lower or "s hungry" in lower or "e hungry" in lower or "y hungry" in lower:
        log.info("[{0}] said someone is/was hungry".format(member))
        if random.randint(1, 3) != 1:
            msg = "No, <@221162619497611274> is hungry."
            await client.send_file(message.channel, 'dennis.gif')
            await client.send_message(message.channel, msg)

    #Rate limiter
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
            
client.run(args.token)
