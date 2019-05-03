import re
import os
import sys
import yaml
import random
import sqlite3
from datetime import datetime

def load_yaml(yaml_file_name):
    with open(os.path.join(sys.path[0], yaml_file_name), "r", encoding="utf8") as yaml_file:
        return yaml.safe_load(yaml_file)

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
    
def seconds_since(then):
    return abs((datetime.utcnow() - then).total_seconds())
    
def open_database():
    file_name = config['discord']['database']
    file_path = os.path.join(sys.path[0], "sqlite", file_name)
    return sqlite3.connect(file_path)
    
def store_invite_details(invite, inviter, reason):
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
            VALUES (?,?,?,?,?,?,?,?)
            """
        cursor.execute(sql, (id, date_time_created, date_time_used, inviter_id, inviter_name, invitee_id, invitee_name, reason))
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
                WHERE channel_name = ?
                AND quote_text LIKE ?
                ORDER BY RANDOM()
                LIMIT 1
                """
            cursor.execute(sql, (channel_name, pattern))
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

def create_database(config, log):
    file_name = config['discord']['database']
    file_path = os.path.join(sys.path[0], "sqlite", file_name)
    if os.path.isfile(file_path):
        log.info(f"Database {file_name} found.")
        return
    log.error(f"Database {file_name} not found. Creating now...")
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
                PRIMARY KEY("id")
                )
            """
        cursor.execute(sql)
        database.commit()
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
            CREATE TABLE "hashes" (
                "hash"	INTEGER,
                "date_time"	TEXT,
                "author_id"	INTEGER,
                "author_name"	TEXT,
                PRIMARY KEY("hash")
            );
            """
        cursor.execute(sql)
        database.commit()
        return
        
config = load_yaml("config.yaml")
strings = load_yaml("strings.yaml")