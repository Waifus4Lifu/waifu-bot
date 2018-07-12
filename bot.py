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
import datetime
import yaml
import textwrap
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

#Rate limiter global variables
message_count = 0
previous_author = None
previous_timestamp = None

parser = argparse.ArgumentParser(description="Handle the various automation functions for a discord server.")
parser.add_argument("-v", "--verbose", dest="verbose", action="store_const",
                    const=True, default=False,
                    help="verbose output")
parser.add_argument("-q", "--quiet", dest="quiet", action="store_const",
                    const=True, default=False,
                    help="only output warnings and errors")
args = parser.parse_args()

if args.verbose:
    log.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", level=log.DEBUG, stream=sys.stdout)
    log.debug("Verbose output enabled")
elif args.quiet:
    log.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", level=log.WARNING, stream=sys.stdout)
else:
    log.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", level=log.INFO, stream=sys.stdout)

log.info("Started")

with open(os.path.join(sys.path[0], 'config.yaml'), "r") as f:
    config = yaml.load(f)

with open(os.path.join(sys.path[0], 'playing.txt'), "r") as f:
    playing_messages = f.read().splitlines()

# TODO: Validate that required entries exist

#Rate limiter config
try:
    message_limit = config['rate_limit']['message_limit']
except KeyError:
    # Default to 3
    message_limit = 3

try:
    cooldown_seconds = config['rate_limit']['cooldown_seconds']
except KeyError:
    # Default to 30
    cooldown_seconds = 30

#Stream detection variables
on_cooldown = {}
try:
    stream_cooldown = config['stream']['stream_cooldown']
except KeyError:
    # Default to 7200
    stream_cooldown = 7200

#Sensitive channels
try:
    sensitive_channels = config['channels']['sensitive']
except KeyError:
    # Default
    sensitive_channels = ["super_waifu_chat",
                          "serious_business"]

#Affirmative answers
try:
    answers_yes = config['answers']['yes']
except KeyError:
    # Default
    answers_yes = ["yes",
                   "yeah"]

#no_problem messages
try:
    no_problem = config['bot_phrases']['no_problem']
except KeyError:
    # Default
    no_problem = ["No problemo",
                   "Anytime"]

client = discord.Client()

def is_super_waifu(member):
    for author_role in member.roles:
        if author_role.name == "super_waifus":
            return True
    return False

def is_mod(member):
    for author_role in member.roles:
        if author_role.name == "mods":
            return True
    return False

def get_games():
    try:
        with open(os.path.join(sys.path[0], 'games.dat'), 'rb') as fp:
            return pickle.load(fp)
    except FileNotFoundError:
        return False
        
def get_game_servers():
    try:
        with open(os.path.join(sys.path[0], 'game_servers.dat'), 'rb') as fp:
            return pickle.load(fp)
    except FileNotFoundError:
        return False

def get_roles():
    try:
        with open(os.path.join(sys.path[0], 'roles.dat'), 'rb') as fp:
            return pickle.load(fp)
    except FileNotFoundError:
        return False

def get_role_bans():
    try:
        with open(os.path.join(sys.path[0], 'role_bans.dat'), 'rb') as fp:
            return pickle.load(fp)
    except FileNotFoundError:
        return False

def get_channel(requested_channel):
    for channel in server.channels:
        if channel.name == requested_channel:
            return(channel)
    else:
        return False

def get_role(requested_role):
    for role in server.roles:
        if role.name == requested_role:
            return(role)
    else:
        return False

def get_members_by_role(role):
    members = []
    for member in server.members:
        for member_role in member.roles:
            if member_role.name == role:
                members.append(member)
                break
    return(members)

def get_quotes():
    try:
        with open(os.path.join(sys.path[0], 'quotes.dat'), 'rb') as fp:
            return pickle.load(fp)
    except FileNotFoundError:
        return []

def create_quote_image(quote, name):
    text = "\"{}\"".format(quote)
    name = "- {}".format(name)
    file = random.choice(os.listdir(os.path.join(sys.path[0], 'images')))
    img = Image.open(os.path.join(sys.path[0], 'images', file))
    draw = ImageDraw.Draw(img)
    img_size = img.size
    font = ImageFont.truetype("impact.ttf", 180)
    border = 5
    multi_line = ""
    for line in textwrap.wrap(text, width=40):
        multi_line += line + "\n"
    text_size = draw.multiline_textsize(text=multi_line, font=font)
    name_size = draw.textsize(text=name, font=font)

    #Draw quote
    x = (img_size[0]/2) - (text_size[0]/2)
    y = (img_size[1]/2) - (text_size[1]/2) - name_size[1]
    #Border
    draw.multiline_text((x-border,y),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x-border,y-border),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x,y-border),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x+border,y-border),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x+border,y),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x+border,y+border),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x,y+border),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x-border,y+border),multi_line,font=font, align='center', fill='black')
    #Text
    draw.multiline_text((x,y),multi_line,font=font, align='center', fill='white')

    #Draw name
    x += text_size[0] - name_size[0]
    y += text_size[1]
    #Border
    draw.text((x-border,y),name,font=font, align='right', fill='black')
    draw.text((x-border,y-border),name,font=font, align='right', fill='black')
    draw.text((x,y-border),name,font=font, align='right', fill='black')
    draw.text((x+border,y-border),name,font=font, align='right', fill='black')
    draw.text((x+border,y),name,font=font, align='right', fill='black')
    draw.text((x+border,y+border),name,font=font, align='right', fill='black')
    draw.text((x,y+border),name,font=font, align='right', fill='black')
    draw.text((x-border,y+border),name,font=font, align='right', fill='black')
    #Text
    draw.text((x,y),name,font=font, align='right', fill='white')

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    out_file = "tmp/{}.jpg".format(timestamp)
    img.save(os.path.join(sys.path[0], out_file))
    return out_file

@client.event
async def on_ready():
    global server
    global channels
    global roles

    server = client.get_server(config['discord']['server_id'])
    channels = dict()
    roles = dict()

    log.info("Connected to server: {}".format(server.name))
    log.debug("Logged in as:")
    log.debug("User: {0}".format(client.user.name))
    log.debug("ID: {0}".format(client.user.id))

    loop = asyncio.get_event_loop()
    status_task = loop.create_task(change_status())

#Update the 'playing' status message every 5-10 minutes from playing.txt
@asyncio.coroutine
async def change_status():
    while True:
        playing = random.choice(playing_messages)
        if playing[:1] == "0":
            status = discord.Status.online
        elif playing[:1] == "1":
            status = discord.Status.idle
        else:
            status = discord.Status.dnd
        await client.change_presence(game=discord.Game(name=playing[1:]), status=status)
        await asyncio.sleep(random.randint(300, 600))

#Post message in promote_a_stream when a member starts streaming
@client.event
async def on_member_update(before, after):
    if before.game != after.game:
        if after.game != None:
            # Streaming
            if after.game.type == 1:
                if after.id in on_cooldown:
                    delta = (datetime.datetime.now() - on_cooldown[after.id]).total_seconds()
                    cooldown_remaining = stream_cooldown - delta
                    if delta < stream_cooldown:
                        log.info("{} is streaming {}. Cooldown remaining: {}s".format(after.name, after.game.name, round(cooldown_remaining)))
                        return
                msg = "Hey {}, {} is streaming {}!\n{}".format(get_role("creeps").mention, after.name, after.game.name, after.game.url)
                await client.send_message(get_channel("promote_a_stream"), msg)
                on_cooldown[after.id] = datetime.datetime.now()
    return

@client.event
async def on_member_join(member):
    if member.bot:
        return
    await client.add_roles(member, get_role("noobs"))
    await asyncio.sleep(15)
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
            if get_role('noobs') not in member.roles:
                msg = "{}, you have been manually approved. Please make sure you read the posts in welcome_and_rules.".format(member.name)
                await client.send_message(member, msg)
                msg = "{} has been manually approved.".format(member.name)
                await client.send_message(get_channel("super_waifu_chat"), msg)
                return
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
    if "!lottery" in message.content or message.channel.is_private:
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
    if message.content.lower().startswith("!say"):
        if not message.channel.is_private and is_super_waifu(member):
            message_parts = message.content.split(' ', 2)
            if len(message.channel_mentions) == 1 and (len(message_parts) == 3 or len(message.attachments) > 0):
                channel = message.channel_mentions[0]
                if len(message.attachments) == 0:
                    msg = ""
                    if len(message_parts) == 3:
                        msg = message_parts[2]
                    await client.send_message(channel, msg)
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
                            if len(message_parts) == 3:
                                msg = message_parts[2]
                        await client.send_file(channel, fp=os.path.join(sys.path[0], file_name), content=msg)
                        os.remove(os.path.join(sys.path[0], file_name))
                notification_msg = "{user} made me say something in {channel}."
                await client.send_message(get_channel("super_waifu_chat"), notification_msg.format(user=member.mention, channel=channel.mention))
            else:
                msg = "Please use the following syntax: `!say [channel_mention] [message_body]`"
                await client.send_message(message.channel, msg)
        else:
            msg = "Just what do you think you're doing? You're not authorized."
            await client.send_file(message.channel, os.path.join(sys.path[0], 'dennis.gif'), filename=None, content=msg, tts=False)
        return

    if not member:
        await client.send_message(message.author, "You are not a Waifu. GTFO")
        return False

    #Reply to human thankfullness
    if 'thank' in message.content.lower() and client.user in message.mentions:
        reply_msg = random.choice(no_problem)
        await client.send_message(message.channel, reply_msg)
        return

    #Save a quote for later inspiration
    if message.content.lower().startswith("!quoth"):
        if len(message.mentions) == 1:
            if message.author == message.mentions[0]:
                msg = "No {}, you cannot quote yourself. Just how conceited are you?".format(message.author.mention)
                log.info("{} tried to save their own quote.".format(message.author))
                await client.send_message(message.channel, msg)
                return
            async for previous_message in client.logs_from(message.channel, limit=100):
                if previous_message.author == message.mentions[0]:
                    if len(previous_message.content) > 0:
                        #Store previous_message.content
                        quotes = get_quotes()
                        for quote in quotes:
                            if quote.id == previous_message.id:
                                msg = "Can you not read? That quote has already been saved."
                                log.info("Quote already exists")
                                await client.send_message(message.channel, msg)
                                return
                        #Ask for confirmation
                        if message.channel.name in sensitive_channels:
                            msg = "Hey uh, {}, this is a sensitive_channel™.\nAre you sure you want to do this?".format(message.author.mention)
                            await client.send_message(message.channel, msg)
                            reply_msg = await client.wait_for_message(timeout=60, author=message.author, channel=message.channel)
                            if reply_msg is None:
                                msg = "I'm going to take your silence as a 'no'."
                                await client.send_message(message.channel, msg)
                                return
                            if reply_msg.content.lower() not in answers_yes:
                                msg = "I'm glad you came to your senses."
                                await client.send_message(message.channel, msg)
                                return
                        quotes.append(previous_message)
                        with open(os.path.join(sys.path[0], 'quotes.dat'), 'wb') as fp:
                            pickle.dump(quotes, fp)
                        msg = "Message by {} successfully stored in quotes.".format(message.mentions[0].name)
                        log.info(msg)
                        await client.send_message(message.channel, msg)
                        return
                    else:
                        #Zero-length messages cannot be quotes
                        msg = "Zero-length messages cannot be quotes. Duh."
                        log.info(msg)
                        await client.send_message(message.channel, msg)
                        return
            #No messages found in channel by specified author
            msg = "No recent messages by {} exist in {}."
            log.info(msg.format(message.mentions[0].name, message.channel))
            await client.send_message(message.channel, msg.format(message.mentions[0].name, message.channel.mention))
            return
        else:
            #Too many or no mention provided
            msg = "You must provide 1 user mention. Not {}, dumbass.".format(len(message.mentions))
            log.info(msg)
            await client.send_message(message.channel, msg)
            return

    #Draw and post image from inspirational quote database
    if message.content.lower().startswith("!inspire"):
        await client.send_typing(message.channel)
        quotes = get_quotes()
        if len(quotes) < 1:
            #No quotes found
            msg = "No inspirational quotes found. Not surprising honestly."
            log.error("No quotes found")
            await client.send_message(message.channel, msg)
            return
        quote = random.choice(quotes)
        content = quote.content
        if len(quote.mentions) > 0:
            for member in quote.mentions:
                content = content.replace(member.mention, member.name)
        quote_image = create_quote_image(content, quote.author.name)
        await client.send_file(message.channel, os.path.join(sys.path[0], quote_image), filename=None, tts=False)
        os.remove(os.path.join(sys.path[0], quote_image))
        return

    #View quotes (super_waifus)
    if message.content.lower().startswith("!viewquotes"):
        if not is_super_waifu(member):
            msg = "{user}, you are not authorized to do that!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return
        quotes = get_quotes()
        if len(quotes) < 1:
            msg = "No quotes found."
            log.error(msg)
            await client.send_message(message.channel, msg)
            return
        reply_msg = ""
        for i, quote in enumerate(quotes):
            quote_info = "ID: {}\nAuthor: {}\nQuote: {}".format(quote.id, quote.author.name, quote.content)
            if len(quote_info) > 190:
                reply_msg += quote_info[:187] + "...\n\n"
            else:
                reply_msg += quote_info + "\n\n"
            if (i%10 == 0 and i != 0) or i == len(quotes) - 1:
                await client.send_message(message.channel, reply_msg)
                await asyncio.sleep(3)
                reply_msg = ""
        return

    #Delete quote (super_waifus)
    if message.content.lower().startswith("!deletequote"):
        if not is_super_waifu(member):
            msg = "{user}, you are not authorized to do that!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return
        quote_id = message.content[13:]
        quotes = get_quotes()
        for i, quote in enumerate(quotes):
            if quote.id == quote_id:
                quotes.pop(i)
                with open(os.path.join(sys.path[0], 'quotes.dat'), 'wb') as fp:
                    pickle.dump(quotes, fp)
                msg = "Quote {} successfully deleted.".format(quote_id)
                log.info(msg)
                await client.send_message(message.channel, msg)
                return
        #Quote not found
        msg = "Quote {} not found.".format(quote_id)
        log.info(msg)
        await client.send_message(message.channel, msg)
        return

    if message.content.lower().startswith("!roleban"):
        if not is_mod(member):
            msg = "{user}, you are not authorized to do that!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{user}] requested to use !roleban but is not authorized.".format(user=member.name))
            return

        if not (message.channel.name in ('super_waifu_chat', 'admin_chat', 'bot_testing', 'mod_chat') or message.channel.is_private):
            msg = "{user}, this ain't the place for this kind of shit!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{user}] requested to use !roleban in an inappropriate channel: {channel}".format(user=member.name, channel=message.channel))
            return

        message_parts = message.content.split(' ')
        if len(message_parts) != 3:
            msg = "{user}, you must supply two arguments: `!roleban user_id role_name`"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        banned = server.get_member(message_parts[1])
        if banned == None:
            msg = "{user}, that is not a valid ID for a member of this server."
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        role_name = message_parts[2]
        if not get_role(role_name):
            msg = "{user}, that is not a valid role name in this server."
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        role_bans = get_role_bans()
        if not role_bans:
            role_bans = {}

        if banned.id in role_bans:
            if role_name in role_bans[banned.id]:
                msg = "{user} is already banned from that role."
                await client.send_message(message.channel, msg.format(user=banned.name))
                return
            role_bans[banned.id].append(role_name)
        else:
            role_bans[banned.id] = [role_name]

        with open(os.path.join(sys.path[0], 'role_bans.dat'), 'wb') as fp:
                pickle.dump(role_bans, fp)

        # Check to see if the user has this role
        msg = "{banned} did not have the role so I didn't have to remove it\n".format(banned=banned.name)
        for banned_user_role in banned.roles:
            if banned_user_role.name == role_name:
                try:
                    await client.remove_roles(banned, banned_user_role)
                    msg = "{banned} had the role but it has been removed\n".format(banned=banned.name)
                    log.info("{banned} had the role but it has been removed".format(banned=banned.name))
                except discord.errors.Forbidden:
                    msg = "{banned} has the role but I am not able to remove it\n".format(banned=banned.name)
                    log.info("{banned} has the role but I am not able to remove it".format(banned=banned.name))

        msg = msg + "{user} is now banned from {role}".format(user=banned.name, role=role_name)
        await client.send_message(message.channel, msg)
        log.info("[{mod}] has banned {user} from {role}".format(mod=member.name, user=banned.name, role=role_name))
        return

    if message.content.lower().startswith("!viewrolebans"):
        if not is_mod(member):
            msg = "{user}, you are not authorized to do that!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{user}] requested to use !viewrolebans but is not authorized.".format(user=member.name))
            return

        if not (message.channel.name in ('super_waifu_chat', 'admin_chat', 'bot_testing', 'mod_chat') or message.channel.is_private):
            msg = "{user}, this ain't the place for this kind of shit!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{user}] requested to use !viewrolebans in an inappropriate channel: {channel}".format(user=member.name, channel=message.channel))
            return

        role_bans = get_role_bans()
        msg = ""
        for banned_id in role_bans:
            msg = msg + "{user}: ".format(user=server.get_member(banned_id).name)
            for index, role_name in enumerate(role_bans[banned_id]):
                if index > 0:
                    msg += ', '
                msg += role_name
            msg += "\n"
        await client.send_message(message.channel, msg)
        log.info("[{mod}] has requested a list of role bans.".format(mod=member.name))
        return

    if message.content.lower().startswith("!roleunban"):
        if not is_mod(member):
            msg = "{user}, you are not authorized to do that!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{user}] requested to use !roleunban but is not authorized.".format(user=member.name))
            return

        if not (message.channel.name in ('super_waifu_chat', 'admin_chat', 'bot_testing', 'mod_chat') or message.channel.is_private):
            msg = "{user}, this ain't the place for this kind of shit!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{user}] requested to use !roleunban in an inappropriate channel: {channel}".format(user=member.name, channel=message.channel))
            return

        message_parts = message.content.split(' ')
        if len(message_parts) != 3:
            msg = "{user}, you must supply two arguments: `!roleunban user_id role_name`"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        unbanned = server.get_member(message_parts[1])
        if unbanned == None:
            msg = "{user}, that is not a valid ID for a member of this server."
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        role_name = message_parts[2]
        if not get_role(role_name):
            msg = "{user}, that is not a valid role name in this server."
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        role_bans = get_role_bans()
        if not role_bans:
            role_bans = {}

        if unbanned.id in role_bans:
            if role_name in role_bans[unbanned.id]:
                role_bans[unbanned.id].remove(role_name)
            else:
                msg = "{user} is not banned from {role}."
                await client.send_message(message.channel, msg.format(user=unbanned.name, role=role_name))
                return
        else:
            msg = "{user} is not banned from any roles."
            await client.send_message(message.channel, msg.format(user=unbanned.name))
            return

        with open(os.path.join(sys.path[0], 'role_bans.dat'), 'wb') as fp:
                pickle.dump(role_bans, fp)

        msg = "{user} is now unbanned from {role}"
        await client.send_message(message.channel, msg.format(user=unbanned.name, role=role_name))
        log.info("[{mod}] has unbanned {user} from {role}".format(mod=member.name, user=unbanned.name, role=role_name))
        return

    if message.content.lower().startswith("!addgame"):
        if not is_super_waifu(member):
            msg = "{user}, you are not authorized to do that!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        message_parts = message.content.split(' ', 1)

        if len(message_parts) == 1:
            msg = "{user}, you didn't specify a game, are you a moron?"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        game = message_parts[1].upper()

        # Verify that the role exists and is all caps
        if not get_role(game):
            # Create the role
            await client.create_role(server, name=game, mentionable=True)

        games = get_games()
        if not games:
            games = []

        # Add the role to the savefile
        games.append(game)

        with open(os.path.join(sys.path[0], 'games.dat'), 'wb') as fp:
            pickle.dump(games, fp)

        msg = "{user}, I have added {game} to the list of games."
        await client.send_message(message.channel, msg.format(user=member.mention, game=game))
        
    if message.content.lower().startswith("!addserver"):
        if not is_super_waifu(member):
            msg = "{user}, you are not authorized to do that!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return
        
        message_parts = message.content.split(' ', 1)
        if len(message_parts) == 1:
            msg = "{user}, you didn't specify a game, dummy?"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return
        
        game_server = message_parts[1]
        
        game_servers = get_game_servers()
        if not game_servers:
            game_servers = []
            
        game_servers.append(game_server)
        with open(os.path.join(sys.path[0], 'game_servers.dat'), 'wb') as fp:
            pickle.dump(game_servers, fp)

        msg = "{user}, it will be done."
        await client.send_message(message.channel, msg.format(user=member.mention))
        return
        
    if message.content.lower().startswith("!servers"):
        if get_game_servers():
            reply_msg = "The following servers may be available:\n```"
            for game_server in get_game_servers():
                reply_msg += ("{game_server}\n".format(game_server = game_server))
            reply_msg += "```"
        else:
            reply_msg = "There are no servers in the savefile!"
        await client.send_message(message.channel, reply_msg)
        return
        
    if message.content.lower().startswith("!removeserver"):
        if not is_super_waifu(member):
            msg = "{user}, you are not authorized to do that!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        message_parts = message.content.split(' ', 1)

        if len(message_parts) == 1:
            msg = "{user}, you didn't specify a server. I'm not surprised given your track record."
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        game_server_name = message_parts[1]

        # Check if the role is in the savefile, if it is delete it
        game_servers = get_game_servers()
        if not game_servers:
            msg = "{user}, there are no servers in the savefile."
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        for game_server in game_servers:
            if game_server.lower().startswith(game_server_name.lower()):
                game_servers.remove(game_server)
                with open(os.path.join(sys.path[0], 'game_servers.dat'), 'wb') as fp:
                    pickle.dump(game_servers, fp)
                msg = "{user}, it will be done."
                await client.send_message(message.channel, msg.format(user=member.mention))
                return

        msg = "{user}, that server isn't listed. How'd you fuck that up?"
        await client.send_message(message.channel, msg.format(user=member.mention))
        return    

    if message.content.lower().startswith("!addrole"):
        if not is_super_waifu(member):
            msg = "{user}, you are not authorized to do that!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        message_parts = message.content.split(' ', 1)

        if len(message_parts) == 1:
            msg = "{user}, you didn't specify a role, are you a moron?"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        role = message_parts[1].lower()

        forbidden_roles = [
            'admin',
            'bots',
            'super_waifus',
            'waifu_4_lifu',
            'announcements',
            'noobs'
        ]

        if role in forbidden_roles:
            msg = "{user}, go fuck yourself I'm not doing that!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        # Verify that the role exists and is all caps
        if not get_role(role):
            # Create the role
            await client.create_role(server, name=role, mentionable=True)

        roles = get_roles()
        if not roles:
            roles = []

        # Add the role to the savefile
        roles.append(role)

        with open(os.path.join(sys.path[0], 'roles.dat'), 'wb') as fp:
            pickle.dump(roles, fp)

        msg = "{user}, I have added {role} to the list of roles."
        await client.send_message(message.channel, msg.format(user=member.mention, role=role))

    if message.content.lower().startswith("!removegame"):
        if not is_super_waifu(member):
            msg = "{user}, you are not authorized to do that!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        message_parts = message.content.split(' ', 1)

        if len(message_parts) == 1:
            msg = "{user}, you didn't specify a game, are you a moron?"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        game = message_parts[1].upper()

        # Check if the role is in the savefile, if it is delete it
        games = get_games()
        if not games:
            msg = "{user}, there are no games in the savefile."
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        if game in games:
            # remove game from list and update savefile
            games.remove(game)
            with open(os.path.join(sys.path[0], 'games.dat'), 'wb') as fp:
                pickle.dump(games, fp)
            msg = "{user}, I have removed {game} from the list of games."
            await client.send_message(message.channel, msg.format(user=member.mention, game=game))
            await client.delete_role(server, get_role(game))
        else:
            msg = "{user}, that game isn't listed. How'd you fuck that up?"
            await client.send_message(message.channel, msg.format(user=member.mention))

        return

    if message.content.lower().startswith("!removerole"):
        if not is_super_waifu(member):
            msg = "{user}, you are not authorized to do that!"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        message_parts = message.content.split(' ', 1)

        if len(message_parts) == 1:
            msg = "{user}, you didn't specify a role, are you a moron?"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        role = message_parts[1].lower()

        # Check if the role is in the savefile, if it is delete it
        roles = get_roles()
        if not roles:
            msg = "{user}, there are no roles in the savefile."
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        if role in roles:
            # remove role from list and update savefile
            roles.remove(role)
            with open(os.path.join(sys.path[0], 'roles.dat'), 'wb') as fp:
                pickle.dump(roles, fp)
            msg = "{user}, I have removed {role} from the list of roles."
            await client.send_message(message.channel, msg.format(user=member.mention, role=role))
            await client.delete_role(server, get_role(role))
        else:
            msg = "{user}, that role isn't listed. How'd you fuck that up?"
            await client.send_message(message.channel, msg.format(user=member.mention))

        return

    if message.content.lower().startswith("!games"):
        if get_games():
            reply_msg = "The following games are currently supported:\n```"
            for game in get_games():
                players = get_members_by_role(game)

                reply_msg += ("{0} ({1} Players)\n".format(game.ljust(20), len(players)))
            reply_msg += "```"
        else:
            reply_msg = "There are no games in the savefile!"
        await client.send_message(message.channel, reply_msg)
        return

    if message.content.lower().startswith("!roles"):
        if get_roles():
            reply_msg = "The following roles are currently supported:\n```"
            for role in get_roles():
                players = get_members_by_role(role)

                reply_msg += ("{0} ({1} members)\n".format(role.ljust(20), len(players)))
            reply_msg += "```"
        else:
            reply_msg = "There are no roles in the savefile!"
        await client.send_message(message.channel, reply_msg)
        return

    elif message.content.lower().startswith("!players"):
        log.info("[{0}] Requested a list of players".format(member.name))

        message_parts = message.content.split(' ', 1)

        if len(message_parts) == 1:
            log.info("[{0}] No game specified".format(member.name))
            msg = "{user}, you didn't specify a game, are you a moron?"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        game = message_parts[1].upper()

        if game in get_games():
            log.info("[{user}] Requested the list of players: {game}".format(user=member.name, game=game))

            players = get_members_by_role(game)

            reply_msg = "There are {player_count} players for {game}.\n\n".format(game=game, player_count=len(players))
            for player in players:
                reply_msg += ("@{0}\n".format(player.name))
            await client.send_message(message.channel, reply_msg)
        else:
            msg = "{user}, that's not a valid game, stop being stupid."
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{user}] requested to list invalid game: {game}".format(user=member.name, game=game))
        return

    # Add user to a game/role
    elif message.content.lower().startswith("!join"):
        message_parts = message.content.split(' ', 1)

        if len(message_parts) == 1:
            log.info("[{0}] No game/role specified".format(member.name))
            msg = "{user}, you didn't specify a game/role, are you a moron?"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        role = message_parts[1]
        #Legacy support for old geezers
        if role.lower() == "shitposting":
            role = "shitty_people"
        if role.lower() == "promote_a_stream":
            role = "creeps"

        if role.upper() in get_games():
            role = role.upper()
        elif role.lower() in get_roles():
            role = role.lower()
        else:
            msg = "{user}, that's not a valid game/role, stop being stupid."
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{user}] requested to join invalid game/role: {role}".format(user=member.name, role=role))
            return

        # Check if user is banned from role
        role_bans = get_role_bans()
        if member.id in role_bans:
            if role in role_bans[member.id]:
                msg = "{user}, I am unable to add that role. Please contact one of the {role}."
                await client.send_message(message.channel, msg.format(user=member.mention, role=get_role('mods').mention))
                log.info("[{user}] requested to join {role} but is banned.".format(user=member.name, role=role))
                return

        log.info("[{user}] requested to join game/role: {role}".format(user=member.name, role=role))

        # Check to see if the user already has this role
        for author_role in member.roles:
            if author_role.name == role:
                # They did, let them know they already had it
                msg = "{user} you are already a member of {role}."
                await client.send_message(message.channel, msg.format(user=member.mention, role=role))
                log.info("[{0}] Role already assigned".format(member))
                break
        else:
            role = get_role(role)
            if not role:
                return False

            # They didn't have the role, so add it
            await client.add_roles(member, role)
            log.info("[{0}] Role added".format(member))

            if role.name in get_games():
                reply = "Hello {user}, you are now signed up for {role}. People can tag you instead of EVERYONE by using `@{role}`.\n" \
                    "You can use `!leave {role}` to be removed from the list at any time.".format(user=member.mention, role=role.name)
                notification_msg = "{user} has signed up to play {role}! There are currently {players} players available."
                await client.send_message(get_channel("looking_for_group"), notification_msg.format(user=member.mention, role=role, players=len(get_members_by_role(role.name))))
            elif role.name == "shitty_people":
                reply = "Hello {user}, you are now able to access {channel}. You fucking pervert.".format(user=member.mention, channel=get_channel("nsfw_shitposting").mention)
            elif role.name == "creeps":
                reply = "Ok {user}, you will now be notified in {channel} when a stream goes live. You're a piece of work.".format(user=member.mention, channel=get_channel("promote_a_stream").mention)
            else:
                reply = "Ok {user}, you have been added to {role}.".format(user=member.mention, role=role)
            await client.send_message(message.channel, reply)

    # Remove user from a game/role
    elif message.content.lower().startswith("!leave"):
        message_parts = message.content.split(' ', 1)

        if len(message_parts) == 1:
            log.info("[{0}] No game/role specified".format(member.name))
            msg = "{user}, you didn't specify a game/role, are you a moron?"
            await client.send_message(message.channel, msg.format(user=member.mention))
            return

        role = message_parts[1]
        #Legacy support for old geezers
        if role.lower() == "shitposting":
            role = "shitty_people"
        if role.lower() == "promote_a_stream":
            role = "creeps"

        if role.upper() in get_games():
            role = role.upper()
        elif role.lower() in get_roles():
            role = role.lower()
        else:
            msg = "{user}, that's not a valid game/role, stop being stupid."
            await client.send_message(message.channel, msg.format(user=member.mention))
            log.info("[{user}] requested to join invalid game/role: {role}".format(user=member.name, role=role))
            return

        log.info("[{user}] requested to leave game/role: {role}".format(user=member.name, role=role))

        # Check to see if the user has this role
        for author_role in member.roles:
            if author_role.name == role:
                # They did, so remove the role
                await client.remove_roles(member, author_role)
                log.info("[{0}] Role removed".format(member))
                if role in get_games():
                    reply = "Hello {user}, you have been removed from list for {role}, to re-join send `!join {role}` in any channel.".format(user=member.mention, role=role)
                    notification_msg = "{user} no longer wants to play {role} like a bitch. There are currently {players} players available."
                    await client.send_message(get_channel("looking_for_group"), notification_msg.format(user=member.mention, role=role, players=len(get_members_by_role(role))))
                elif role == "shitty_people":
                    reply = "Alright {user}, I see how it is. {channel} is now off-limits to you.".format(user=member.mention, channel=get_channel("nsfw_shitposting").mention)
                elif role == "creeps":
                    reply = "Ok {user}, you will no longer be notified of live streams.".format(user=member.mention)
                else:
                    reply = "Ok {user}, you have been stripped of the {role} role. We all knew you wouldn't last.".format(user=member.name, role=role)
                await client.send_message(message.channel, reply)
                break
        else:
            # They didn't have the role, do nothing
            msg = "{user}, you have already unsubscribed from the list for {role}"
            await client.send_message(message.channel, msg.format(user=member.mention, role=role))
            log.info("[{0}] Role was already not assigned".format(member))
        return

    elif message.content.lower().startswith("!invite"):
        # Check to see if the user has this role
        if is_super_waifu(member):
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
        else:
            # They didn't have the role, do nothing
            msg = "{user}, you don't have access to create invites you cuck."
            await client.send_message(message.channel, msg.format(user=member.mention, shitposting=get_channel("nsfw_shitposting").mention))
            log.info("[{0}] Requested an invite but was denied".format(member))
        return

    # Show a help/about dialog
    elif message.content.lower().startswith("!wtf") or message.content.lower().startswith("!help"):
        log.info("[{0}] Requested information about us".format(member.name))
        msg = "Fuck you, I'm a bot for managing various automatic rules and features of the Waifus_4_Lifu Discord chat server.\n\n" \
            "I understand the following commands:\n\n" \
            "`!help` or `!wtf` - This help message.\n" \
            "`!games` - Show a list of games you can join for LFG notifications.\n" \
            "`!roles` - Show a list of roles/groups you can join.\n" \
            "`!servers` - Show a list of game servers you can access.\n" \
            "`!players` - Who is available to play a game. Example: `!players PUBG`\n" \
            "`!join` - Add yourself to a role or the list of people who want to play a game. Example: `!join PUBG`\n" \
            "`!leave` - Remove yourself from a role or the list of people who want to play a game.\n" \
            "`!8ball` - Ask the magic 8 ball a question.\n" \
            "`!random` - Request a random number, chosen by fair dice roll.\n" \
            "`!sponge` - Mock previous post even if you’re not smart enough to be clever.\n" \
            "`!color` - Get the hex and RGB values for Waifu Pink.\n" \
            "`!quoth` - Save most recent message by @mention to inspirational quotes.\n" \
            "`!inspire` - Request a random quote for inspiration.\n" \
            "`!yeah`\n" \
            "`!shrug`\n" \
            "`!catfact`\n" \
            "`!google`\n" \
            "`!join shitposting` - Gain access to nsfw/shitposting channel.\n" \
            "`!leave shitposting` - Give up access to nsfw/shitposting channel.\n" \
            "`!lottery [channel_name] [prize_code] [minutes] [prize_name]` - Self-explanatory (DM WaifuBot).\n" \
            "`!superwtf` - Show commands available only to super waifus (mods).\n" \
            "\nIf I'm not working correctly, go fuck yourself, you aren't my boss."
        await client.send_message(message.channel, msg)
        return

    elif message.content.lower().startswith("!superwtf"):
        if is_super_waifu(member):
            msg = "Oh shit it's a mod, everyone pretend like you aren't fucking shit up.\n\n" \
                "I understand the following commands:\n\n" \
                "`!superwtf` - This help message.\n" \
                "`!addgame` - Add a game to the list of games people can subscribe to for LFG notifications.\n" \
                "`!removegame` - Remove a game from the list.\n" \
                "`!addserver` - Add game server info to the list of dedicated game servers.\n" \
                "`!removeserver` - Remove game server info from the list of dedicated game servers.\n" \
                "`!addrole` - Add a role people can join.\n" \
                "`!removerole` - Remove a role from the list.\n" \
                "`!viewquotes` - View list of partial quotes.\n" \
                "`!deletequote` - Delete a quote by providing quote ID.\n" \
                "`!roleban` - Ban a member from joining a specific role (removes role if applicable).\n" \
                "`!roleunban` - Undo the ban imposed by !roleban (does not add role back).\n" \
                "`!viewrolebans` - View list of role bans. Kinda obvious.\n" \
                "`!say [channel_mention] [message_body]` - Make me say something.\n" \
                "\nIf I'm not working correctly, talk to aceat64 or HungryNinja."
        else:
            msg = "{user}, you aren't a super waifu! Access denied.".format(user=member.mention)
        await client.send_message(message.channel, msg)
        return

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
        return

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
                elif shithead['name'] == 'canibalcrab' and random.randint(1, 2) == 1:
                    reply_msg += ("canibalcrab: drawin' dicks all over the shitlist 8=====D 8==D 8============D")
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
        return

    elif message.content.lower().startswith("!favorites"):
        # Example: !favorites
        # Example: !favorites add @PeasAndClams#7812 so nice
        # Example: !favorites remove @PeasAndClams#7812
        authorized_users = [
            "115183069555589125", # aceat64
            "194703127868473344"  # King Of The Rats
        ]

        try:
            with open(os.path.join(sys.path[0], 'favorites.dat'), 'rb') as fp:
                favorites = pickle.load(fp)
        except FileNotFoundError:
            # No previous file, so create an empty list
            favorites = []

        message_parts = message.clean_content.split(' ', 3)

        if len(message_parts) == 1 or message_parts[1] == "":
            # display favorites
            reply_msg = "Ash has {count} favorite people.\n\n".format(count=len(favorites))
            for bless_you in favorites:
                if not bless_you['reason']:
                    reply_msg += ("{0}\n".format(bless_you['name']))
                else:
                    reply_msg += ("{0}: {1}\n".format(bless_you['name'], bless_you['reason']))
            await client.send_message(message.channel, reply_msg)
        else:
            if member.id not in authorized_users:
                msg = "{user}, you aren't authorized to do this."
                await client.send_message(message.channel, msg.format(user=member.mention))
                return

            # check if user is real
            try:
                bless_you = message_parts[2]
            except IndexError:
                msg = "{user}, add/remove who?"
                await client.send_message(message.channel, msg.format(user=member.mention))
                return

            if bless_you[0] == '@':
                bless_you = bless_you[1:]
            elif bless_you[0] == '"':
                bless_you = message.clean_content.split('"')[1]

            if message_parts[1].lower() == "add":
                # check if they are already on the favorites
                for existing_bless in favorites:
                    if bless_you == existing_bless['name']:
                        msg = "{user}, that person {bless_you} is already on the favorites. They must be exceptional if you are trying to add them again."
                        await client.send_message(message.channel, msg.format(user=member.mention, bless_you=bless_you))
                        return

                # Add them to the favorites and write to file
                try:
                    favorites.append({
                        'name': bless_you,
                        'reason': message_parts[3]
                    })
                except IndexError:
                    favorites.append({
                        'name': bless_you,
                        'reason': None
                    })

                with open(os.path.join(sys.path[0], 'favorites.dat'), 'wb') as fp:
                    pickle.dump(favorites, fp)

                msg = "{user}, I've added {bless_you} to the favorites."
                await client.send_message(message.channel, msg.format(user=member.mention, bless_you=bless_you))
                return
            elif message_parts[1].lower() == "remove":
                # check if they are actually on the favorites
                for existing_bless in favorites:
                    if bless_you == existing_bless['name']:
                        break
                else:
                    msg = "{user}, {bless_you} isn't on the favorites list."
                    await client.send_message(message.channel, msg.format(user=member.mention, bless_you=bless_you))
                    return

                # Remove them to the favorites and write to file
                favorites[:] = [d for d in favorites if d.get('name') != bless_you]

                with open(os.path.join(sys.path[0], 'favorites.dat'), 'wb') as fp:
                    pickle.dump(favorites, fp)

                msg = "{user}, I've removed {bless_you} from the favorites."
                await client.send_message(message.channel, msg.format(user=member.mention, bless_you=bless_you))
                return
            else:
                # let them know that's not a valid command
                msg = "{user}, that's not a valid command, bless your heart."
                await client.send_message(message.channel, msg.format(user=member.mention))
                return
        return

    # RFC 1149.5 specifies 4 as the standard IEEE-vetted random number.
    # https://xkcd.com/221/
    elif message.content.lower().startswith("!random"):
        await client.send_message(message.channel, "{user}, 4".format(user=member.mention))
        return

    # Automatically fix tables
    elif "┻━┻" in message.content:
        await client.send_message(message.channel, "┬──┬ ﾉ(° -°ﾉ)\n{user} that wasn't nice.".format(user=member.mention))
        return

    # #yeah
    elif message.content.lower().startswith("!yeah"):
        await client.send_message(message.channel, "( •\_•)\n( •\_•)>⌐■-■\n(⌐■\_■)")
        return

    # ¯\_(ツ)_/¯
    elif message.content.lower().startswith("!shrug"):
        await client.send_message(message.channel, "¯\\_(ツ)_/¯")
        return

    # Waifu Pink!
    elif message.content.lower().startswith("!color"):
        if message.author.id == "221162619497611274":
            msg = "{user}, you are not authorized to see in color."
        else:
            msg = "{user}, Waifu Pink uses hex code: `#ff3fb4`, also known as Red: 255, Green: 63, Blue: 180"
        await client.send_message(message.channel, msg.format(user=member.mention))
        return

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
        return

    elif message.content.lower().startswith("!catfact"):
        cat_facts = open(os.path.join(sys.path[0], 'cat_facts.txt')).read().splitlines()
        cat_fact = random.choice(cat_facts)
        if random.randint(1, 4) == 1:
            cat_fact = cat_fact.replace('cat', 'catgirl')
        await client.send_message(message.channel, cat_fact)
        return

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
        return

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
        return

    #Game code lottery
    elif message.content.lower().startswith("!lottery"):
        if not message.channel.is_private:
            await client.delete_message(message)
            msg = "{}, for that you'll need to slide into my DMs. I've gone ahead and deleted your message in case it contained a prize code.".format(member.mention)
            await client.send_message(message.channel, msg)
            return
        command_parts = message.content.split(' ', 4)
        if len(command_parts) != 5:
            msg = "I know you can do better: `!lottery [channel_name] [prize_code] [minutes] [prize_name]`"
            await client.send_message(message.channel, msg)
            return
        channel = get_channel(command_parts[1])
        if not channel:
            msg = "That's not a valid channel, dummy."
            await client.send_message(message.channel, msg)
            return
        prize_code = command_parts[2]
        try:
            minutes = int(command_parts[3])
        except ValueError:
            msg = "The value for minutes must be a positive integer."
            await client.send_message(message.channel, msg)
            return
        prize_name = command_parts[4]
        msg = "Hey @everyone, {0} has initiated a lottery for [{1}]. The drawing will be held in {2} minute"
        if minutes != 1:
            msg += "s"
        msg += ". The winner will be drawn at random from those who **add a reaction to this post**. "
        msg += "You can react as many times as you want, only one entry will be counted. "
        msg += "**Disclaimer: The prize code isn't mine. Blame {0} if it doesn't work.**\n\nGood luck!"
        lottery_post = await client.send_message(channel, msg.format(member.mention, prize_name, minutes))
        end_time = time.time() + (minutes * 60)
        entrants = []
        while time.time() < end_time:
            seconds_left = end_time - time.time()
            reaction = await client.wait_for_reaction(timeout=seconds_left)
            if reaction != None:
                if reaction.user not in entrants and reaction.user != member:
                    entrants.append(reaction.user)
        if len(entrants) == 0:
            msg = "{}, nobody entered your drawing. Nobody wins.".format(member.mention)
            await client.send_message(channel, msg)
        else:
            winner = random.choice(entrants)
            try:
                msg = "Hey {0}, here is your prize code: {1}".format(winner.mention, prize_code)
                await client.send_message(winner, msg)
                msg = "Congratulations, {0}! You have won the lottery drawing. Check your DMs for your prize code.".format(winner.mention)
                await client.send_message(channel, msg)
            except discord.errors.Forbidden:
                msg = "Hey {0}, {1} won your drawing but does not accept DMs from *strangers* like me :elacry:. Y'all work it out amongst yourselves.".format(member.mention, winner.mention)
                await client.send_message(channel, msg)
        return

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
    return

client.run(config['discord']['token'])
