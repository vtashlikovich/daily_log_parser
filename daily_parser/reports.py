import os
import datetime
from pytz import timezone
import html
import requests

requests.packages.urllib3.disable_warnings()

SIMULATE_SYNC = False

INTERNAL_URL = os.getenv("INTERNAL_URL")
INTERNAL_AUTH = os.getenv("INTERNAL_AUTH")
INTERNAL_USER = os.getenv("INTERNAL_USER")
INTERNAL_PASSWORD = os.getenv("INTERNAL_PASSWORD")
INTERNAL_USER_ID = os.getenv("INTERNAL_USER_ID")
DIFFERENCE_PL_BY = 2

def create_internal_report(date: str, time: str, project: int,
                           duration: float, comment: str):
    headers = {
        "Authorization": "Basic " + str(INTERNAL_AUTH)
    }
    
    time = offset_to_belarus_time(time)

    comment = html.escape(comment)
    url = f"{INTERNAL_URL}?mode=json&cmd=saveReport&login={INTERNAL_USER}&pswd={INTERNAL_PASSWORD}&reportDate={date}&reportTime={time}&reportUser={INTERNAL_USER_ID}&reportProject={project}&duration={duration}&description={comment}"
    
    if SIMULATE_SYNC:
        print(f'... create internal report {date=} {time=} {duration=}')
        return False
    else:
        requests.post(url, headers=headers, verify=False)


def create_jira_report(jira, issue: str, date: str, time: str, duration: float,
                       comment: str):
    date_parsed = date.split("-")
    time_parsed = time.split(":")

    time_seconds = convert_time_to_seconds(duration)

    tzinfo = datetime.timezone(datetime.timedelta(hours=2, minutes=0, seconds=0))

    log_datetime = datetime.datetime(year=int(date_parsed[0]), month=int(date_parsed[1]),
                                     day=int(date_parsed[2]),
                                     hour=int(time_parsed[0]), minute=int(time_parsed[1]), second=0, microsecond=0,
                                     tzinfo=tzinfo)
                                     # tzinfo=datetime.tzinfo.utcoffset(1))
                                     # tzinfo=timezone('Europe/Warsaw'))

    if SIMULATE_SYNC:
        print(f'... create Jira report {date=} {time=} {time_seconds=} {issue=}')
        print(f'... {log_datetime=}')
        return False
    else:
        jira.add_worklog(issue=issue, timeSpentSeconds=time_seconds, comment=comment,
            started=log_datetime)


def convert_time_to_seconds(time=float):
    return int(round(time * 3600))

def offset_to_belarus_time(time: str):
    time_list = time.split(':')
    hour = int(time_list[0])
    hour += DIFFERENCE_PL_BY
    if hour > 23: hour = 0
    time = str(hour)
    if hour < 10: time = '0' + time
    time += ':' + time_list[1] + ':' + time_list[2]

    return time