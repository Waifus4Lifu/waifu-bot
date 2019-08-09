import re
import os
import sys
import yaml
import random
import sqlite3
import discord
import logging as log
import hashlib as hash
from datetime import datetime

def load_yaml(yaml_file_name):
    with open(os.path.join(sys.path[0], yaml_file_name), "r", encoding="utf8") as yaml_file:
        return yaml.safe_load(yaml_file)

def paginate(text):
    pages = []
    lines = text.split("\n")
    page = ""
    for line in lines:
        if len(page + line + "\n") < 1024:
            page = page + line + "\n"
        else:
            pages.append(page)
            page = line + "\n"
    pages.append(page)
    return pages

def sha_256(file):
    BLOCKSIZE = 65536
    sha = hash.sha256()
    file_buffer = file.read(BLOCKSIZE)
    while len(file_buffer) > 0:
        sha.update(file_buffer)
        file_buffer = file.read(BLOCKSIZE)
    file.close()
    return sha.hexdigest()

def spongify(text):
    sponged_text = ""
    for character in text:
        if random.choice([True, False]):
            sponged_text = sponged_text + character.upper()
        else:
            sponged_text = sponged_text + character.lower()
    return sponged_text

def sentence_case(text):
    return ". ".join(i.capitalize() for i in text.split(". "))

def chance(percent):
    return random.randint(0, 99) < percent

def replace_ignore_case(text, find, replace):
    pattern = re.compile(find, re.IGNORECASE)
    return pattern.sub(replace, text)

def ascii_only(text):
    stripped = (c for c in text if 0 < ord(c) < 127)
    return ''.join(stripped)

def format_delta_long(delta):
    years = int(delta.days / 365)
    days = int(delta.days % 365)
    hours = int(delta.seconds / 3600)
    minutes = int((delta.seconds % 3600) / 60)
    seconds = int(delta.seconds % 60)
    formatted_delta = ""
    if years == 1:
        formatted_delta = formatted_delta + f"{years} Year, "
    elif years > 1:
        formatted_delta = formatted_delta + f"{years} Years, "
    if days == 1:
        formatted_delta = formatted_delta + f"{days} Day, "
    elif days > 1:
        formatted_delta = formatted_delta + f"{days} Days, "
    if hours == 1:
        formatted_delta = formatted_delta + f"{hours} Hour, "
    elif hours > 1:
        formatted_delta = formatted_delta + f"{hours} Hours, "
    if minutes == 1:
        formatted_delta = formatted_delta + f"{minutes} Minute, "
    elif minutes > 1:
        formatted_delta = formatted_delta + f"{minutes} Minutes, "
    if seconds == 1:
        formatted_delta = formatted_delta + f"{seconds} Second"
    else:
        formatted_delta = formatted_delta + f"{seconds} Seconds"
    return formatted_delta

def format_delta(delta):
    years = int(delta.days / 365)
    days = int(delta.days % 365)
    hours = int(delta.seconds / 3600)
    minutes = int((delta.seconds % 3600) / 60)
    seconds = int(delta.seconds % 60)
    formatted_delta = ""
    if years != 0:
        formatted_delta = formatted_delta + f"{years}y "
    if days != 0:
        formatted_delta = formatted_delta + f"{days}d "
    if hours != 0:
        formatted_delta = formatted_delta + f"{hours}h "
    if minutes != 0:
        formatted_delta = formatted_delta + f"{minutes}m "
    formatted_delta = formatted_delta + f"{seconds}s"
    return formatted_delta

def format_countdown(delta):
    years = int(delta.days / 365)
    days = int(delta.days % 365)
    hours = int(delta.seconds / 3600)
    minutes = int((delta.seconds % 3600) / 60)
    formatted_delta = ""
    if years != 0:
        formatted_delta = formatted_delta + f"{years}Y_"
    if days != 0:
        formatted_delta = formatted_delta + f"{days}D_"
    formatted_delta = formatted_delta + f"{hours}H_"
    formatted_delta = formatted_delta + f"{minutes}M"
    return formatted_delta

def time_since(date_time):
    return (datetime.utcnow() - date_time)

def time_until(date_time):
    return (date_time - datetime.utcnow())

def date_time_from_str(timestamp):
    timestamp = re.sub('[^0-9]','', timestamp)[:14]
    return datetime.strptime(timestamp[:19], "%Y%m%d%H%M%S")

def seconds_since(then):
    return abs((datetime.utcnow() - then).total_seconds())

def open_database():
    return sqlite3.connect(database_file_path)

def store_hash(bytes_hash, message):
    with open_database() as database:
        cursor = database.cursor()
        date_time = message.created_at.strftime("%Y%m%d%H%M%S")
        author_id = message.author.id
        author_name = message.author.display_name
        channel_name = message.channel.name
        channel_category = message.channel.category.name

        sql = """
            INSERT
            INTO hashes
            VALUES (?,?,?,?,?,?,?)
            """
        cursor.execute(sql, (None, bytes_hash, date_time, author_id, author_name, channel_name, channel_category))
        database.commit()
        return

def get_hashes(bytes_hash, channel_category):
    with open_database() as database:
        cursor = database.cursor()
        sql = """
            SELECT *
            FROM hashes
            WHERE hash = ?
            AND channel_category = ?
            ORDER BY date_time DESC
            """
        cursor.execute(sql, (bytes_hash, channel_category))
        return cursor.fetchall()

def store_invite_details(invite, inviter, reason, event):
    with open_database() as database:
        cursor = database.cursor()
        id = invite.id
        date_time_created = invite.created_at
        date_time_used = None
        inviter_id = inviter.id
        inviter_name = str(inviter)
        invitee_id = None
        invitee_name = None
        sql = """
            INSERT
            INTO invites
            VALUES (?,?,?,?,?,?,?,?,?)
            """
        cursor.execute(sql, (id, date_time_created, date_time_used, inviter_id, inviter_name, invitee_id, invitee_name, reason, event))
        database.commit()
        return

def get_invite_details(invite):
    with open_database() as database:
        cursor = database.cursor()
        id = invite.id
        sql = """
            SELECT *
            FROM invites
            WHERE id = ?
            """
        cursor.execute(sql, (id,))
        return cursor.fetchone()

def update_invite_details(invite, invitee):
    with open_database() as database:
        cursor = database.cursor()
        id = invite.id
        date_time_used = datetime.utcnow()
        invitee_id = invitee.id
        invitee_name = str(invitee)
        sql = """
            UPDATE invites
            SET date_time_used = ?, invitee_id = ?, invitee_name = ?
            WHERE id = ?
            """
        cursor.execute(sql, (date_time_used, invitee_id, invitee_name, id))
        database.commit()
        return

def quote_exists(id):
    with open_database() as database:
        cursor = database.cursor()
        sql = """
            SELECT *
            FROM quotes
            WHERE id = ?
            """
        cursor.execute(sql, (id,))
        if cursor.fetchone() == None:
            return False
        return True

def store_quote(message, ctx):
    with open_database() as database:
        cursor = database.cursor()
        id = message.id
        channel_name = message.channel.name
        date_time = datetime.now().isoformat()
        author_id = message.author.id
        author_name = str(message.author.display_name)
        stored_by_id = ctx.author.id
        stored_by_name = str(ctx.author.display_name)
        quote_text = message.clean_content.replace("\"", "'")
        if quote_text[:1] == "'" and quote_text[-1:] == "'":
            quote_text = quote_text[1:-1]
        sql = """
            INSERT
            INTO quotes
            VALUES (?,?,?,?,?,?,?,?)
            """
        cursor.execute(sql, (id, channel_name, date_time, author_id, author_name, stored_by_id, stored_by_name, quote_text))
        database.commit()
        return quote_text

def get_quote(channel, phrase):
    with open_database() as database:
        channel_name = channel.name
        cursor = database.cursor()
        if phrase == None:
            sql = """
                SELECT *
                FROM quotes
                WHERE channel_name = ?
                ORDER BY RANDOM()
                LIMIT 1
                """
            cursor.execute(sql, (channel_name,))
        else:
            pattern = "%" + phrase + "%"
            sql = """
                SELECT *
                FROM quotes
                WHERE (quote_text LIKE ? OR author_name LIKE ?)
                AND channel_name = ?
                ORDER BY RANDOM()
                LIMIT 1
                """
            cursor.execute(sql, (pattern, pattern, channel_name))
        return cursor.fetchone()

def delete_quote(id):
    with open_database() as database:
        cursor = database.cursor()
        sql = """
            SELECT *
            FROM quotes
            WHERE id = ?
            """
        cursor.execute(sql, (id,))
        quote = cursor.fetchone()
        sql = """
            DELETE
            FROM quotes
            WHERE id=?
            """
        cursor.execute(sql, (id,))
        database.commit()
        return quote
        
def veto_quote(id):
    with open_database() as database:
        cursor = database.cursor()
        sql = """
            UPDATE quotes
            SET channel_name = 'vetoed'
            WHERE id = ?
            """
        cursor.execute(sql, (id,))
        database.commit()
        return

def create_database():
    if os.path.isfile(database_file_path):
        log.info(f"Database {database_file_name} found.")
    else:
        log.error(f"Database {database_file_name} not found.")
    with open_database() as database:
        cursor = database.cursor()
        sql = """
            CREATE TABLE IF NOT EXISTS "invites" (
                "id"	TEXT,
                "date_time_created"	TEXT,
                "date_time_used"	TEXT,
                "inviter_id"	INTEGER,
                "inviter_name"	TEXT,
                "invitee_id"	INTEGER,
                "Invitee_name"	TEXT,
                "reason"	TEXT,
                "event"     TEXT,
                PRIMARY KEY("id")
                )
            """
        cursor.execute(sql)
        database.commit()
        sql = """
            ALTER TABLE invites ADD COLUMN event TEXT;
            """
        try:
            cursor.execute(sql)
            database.commit()
        except:
            database.rollback()
        sql = """
            CREATE TABLE IF NOT EXISTS "quotes" (
                "id"	INTEGER,
                "channel_name"	TEXT,
                "date_time"	TEXT,
                "author_id"	INTEGER,
                "author_name"	TEXT,
                "stored_by_id"	INTEGER,
                "stored_by_name"	TEXT,
                "quote_text"	TEXT,
                PRIMARY KEY("id")
                )
            """
        cursor.execute(sql)
        database.commit()
        sql = """
            CREATE TABLE IF NOT EXISTS "hashes" (
                "id"	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                "hash"	INTEGER,
                "date_time"	TEXT,
                "author_id"	INTEGER,
                "author_name"	TEXT,
                "channel_name"	TEXT,
                "channel_category"	TEXT
                )
            """
        cursor.execute(sql)
        database.commit()
        return

log.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", level=log.INFO, stream=sys.stdout)
config = load_yaml("config.yaml")
strings = load_yaml("strings.yaml")
waifu_pink = discord.Color.from_rgb(255, 63, 180)
database_file_name = config['discord']['database']
database_file_path = os.path.join(sys.path[0], "sqlite", database_file_name)
