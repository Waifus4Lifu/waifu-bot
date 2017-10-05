#!/usr/bin/python3
import argparse
import logging as log
import sys
import discord
import asyncio
import urllib
import json
import random

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
    "CIV"
]

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
    if message.content.lower().startswith("!join"):
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
                await client.send_message(get_channel("general_chat"), notification_msg.format(user=member.mention, game=game, players=len(get_members_by_role(game))))
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
                    await client.send_message(get_channel("general_chat"), notification_msg.format(user=member.mention, game=game, players=len(get_members_by_role(game))))
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

                if len(message_parts) == 1:
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
              "`!iamaloser` - Give up access to nsfw channels.\n" \
              "\nIf I'm not working correctly, go fuck yourself, you aren't my boss."
        await client.send_message(message.channel, msg)

    # RFC 1149.5 specifies 4 as the standard IEEE-vetted random number.
    # https://xkcd.com/221/
    elif message.content.lower().startswith("!random"):
        await client.send_message(message.channel, "{user}, 4".format(user=member.mention))

    # Automatically fix tables
    elif "(╯°□°）╯︵ ┻━┻" in message.content:
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

client.run(args.token)
