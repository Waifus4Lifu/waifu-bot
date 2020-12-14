from datetime import datetime, timedelta
from functions import open_database


class VoiceActivity(object):
    """A class to store voice channel activity and calculate total voice channel participation."""

    def __init__(self, member_id, member_name, date_time, channel_name, status):
        self.member_id = member_id
        self.member_name = member_name
        self.date_time = date_time
        self.channel_name = channel_name
        self.status = status
        if isinstance(self.date_time, str):
            self.date_time = datetime.fromisoformat(self.date_time)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        class_name = self.__class__.__name__
        return f"{class_name}({self.member_id}, {self.member_name}, {self.date_time}, {self.channel_name}, {self.status})"

    def __store(self):
        """Store VoiceActivity instance in database."""
        with open_database() as database:
            cursor = database.cursor()
            sql = """INSERT 
                INTO voice_activity
                VALUES (?,?,?,?,?,?)"""
            values = [None,
                      self.member_id,
                      self.member_name,
                      self.date_time,
                      self.channel_name,
                      self.status]
            cursor.execute(sql, values)
            database.commit()
        return self

    @classmethod
    def check_in(cls, member_id, member_name, channel_name):
        """Validate previous records of VoiceActivity for member in database and create/store new VoiceActivity (connected)."""
        date_time = datetime.now()
        last_activity = cls.get_last(member_id)
        if last_activity is not None:
            # Check if the bot has no record of a valid check-out
            if last_activity.status == True:
                # Create missing check-out
                last_date_time = last_activity.date_time + timedelta(hours=2)
                last_channel_name = last_activity.channel_name
                cls(member_id, member_name, last_date_time, last_channel_name, False).__store()
        # Finally, check in
        return cls(member_id, member_name, date_time, channel_name, True).__store()

    @classmethod
    def check_out(cls, member_id, member_name, channel_name):
        """Validate previous records of VoiceActivity for member in database and create/store new VoiceActivity (disconnected)."""
        date_time = datetime.now()
        last_activity = cls.get_last(member_id)
        # Check if the bot has no record of a valid check-in
        if getattr(last_activity, "status", False) == False:
            last_date_time = date_time - timedelta(hours=2)
            cls(member_id, member_name, last_date_time, channel_name, True).__store()
        elif last_activity.status == True:
            # Check if the most-recent check-in channel does not match check-out channel
            if last_activity.channel_name != channel_name:
                # Create missing check-out
                last_date_time = last_activity.date_time + timedelta(hours=2)
                last_channel_name = last_activity.channel_name
                cls(member_id, member_name, last_date_time, last_channel_name, False).__store()
                # Create missing check-in
                last_date_time = date_time - timedelta(hours=2)
                cls(member_id, member_name, last_date_time, channel_name, True).__store()
        # Finally, check out
        return cls(member_id, member_name, date_time, channel_name, False).__store()

    @classmethod
    def get_first(cls):
        """Fetch oldest VoiceActivity record from database."""
        with open_database() as database:
            cursor = database.cursor()
            sql = """SELECT member_id, member_name, date_time, channel_name, status
                FROM voice_activity
                ORDER BY id
                LIMIT 1"""
            cursor.execute(sql)
            result = cursor.fetchone()
            if result is None:
                return None
            return cls(*result)

    @classmethod
    def get_last(cls, member_id):
        """Fetch most recent VoiceActivity record for member from database."""
        with open_database() as database:
            cursor = database.cursor()
            sql = """SELECT member_id, member_name, date_time, channel_name, status
                FROM voice_activity
                WHERE member_id = ?
                ORDER BY id DESC
                LIMIT 1"""
            cursor.execute(sql, (member_id,))
            result = cursor.fetchone()
            if result is None:
                return None
            return cls(*result)

    @classmethod
    def get_all(cls, member_id, start, end):
        """Fetch all VoiceActivity records for member in database within [start, end] datetime interval."""
        with open_database() as database:
            cursor = database.cursor()
            sql = """SELECT member_id, member_name, date_time, channel_name, status
                FROM voice_activity
                WHERE member_id = ?
                AND date_time >= ?
                AND date_time <= ?
                ORDER BY id"""
            cursor.execute(sql, (member_id, start, end))
            results = cursor.fetchall()
            voice_activities = []
            for result in results:
                voice_activities.append(cls(*result))
            return voice_activities

    @classmethod
    def total_seconds(cls, member_id, start=datetime.min, end=datetime.max):
        """Add up all valid (non AFK, skip broken) VoiceActivity intervals for member in database within optional [start, end] interval"""
        total_seconds = 0
        activities = cls.get_all(member_id, start, end)
        if len(activities) == 0:
            return total_seconds
        # Create dummy start/end activities if search interval split first and/or last voice activity intervals
        if activities[0].status == False:
            activities.insert(0, cls(None, None, start, None, True))
        if activities[0].status == True:
            activities.insert(-1, cls(None, None, end, None, None))
        for index, activity in enumerate(activities):
            if activity.status == True:
                continue
            interval_start = activities[index - 1]
            interval_end = activity
            if "AFK" in [interval_start.channel_name, interval_end.channel_name]:
                continue
            total_seconds += (interval_end.date_time - interval_start.date_time).total_seconds()
        return total_seconds
