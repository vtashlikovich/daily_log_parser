import os
import datetime
import html
import requests
from loguru import logger
import urllib.parse

requests.packages.urllib3.disable_warnings()

SIMULATE_SYNC = False
SIMULATE_REDMINE_SYNC = False

INTERNAL_URL = os.getenv("INTERNAL_URL")
INTERNAL_AUTH = os.getenv("INTERNAL_AUTH")
INTERNAL_USER = os.getenv("INTERNAL_USER")
INTERNAL_PASSWORD = os.getenv("INTERNAL_PASSWORD")
INTERNAL_USER_ID = os.getenv("INTERNAL_USER_ID")
DIFFERENCE_PL_BY = 2


def create_internal_report(
    date: str, time: str, project: int, duration: float, comment: str
):

    headers = {"Authorization": "Basic " + str(INTERNAL_AUTH)}

    time = offset_to_belarus_time(time)

    comment = urllib.parse.quote(comment)
    password = urllib.parse.quote(INTERNAL_PASSWORD)

    url = f"{INTERNAL_URL}?mode=json&cmd=saveReport&login={INTERNAL_USER}&pswd={password}\
&reportDate={date}&reportTime={time}&reportUser={INTERNAL_USER_ID}&reportProject={project}\
&duration={duration}&description={comment}"

    # print(url)
    if SIMULATE_SYNC:
        logger.info(
            f"... create internal report {date=} {time=} {duration=} {comment=}"
        )
        return False
    else:
        requests.post(url, headers=headers, verify=False)


def create_jira_report(
    jira, issue: str, date: str, time: str, duration: float, comment: str
):
    date_parsed = date.split("-")
    time_parsed = time.split(":")

    time_seconds = convert_time_to_seconds(duration)

    tzinfo = datetime.timezone(datetime.timedelta(hours=2, minutes=0, seconds=0))

    log_datetime = datetime.datetime(
        year=int(date_parsed[0]),
        month=int(date_parsed[1]),
        day=int(date_parsed[2]),
        hour=int(time_parsed[0]),
        minute=int(time_parsed[1]),
        second=0,
        microsecond=0,
        tzinfo=tzinfo,
    )

    if SIMULATE_SYNC:
        logger.info(
            f"... create Jira report {date=} {time=} {time_seconds=} {issue=} {comment=}"
        )
        logger.info(f"... {log_datetime=}")
        return False
    else:
        jira.add_worklog(
            issue=issue,
            timeSpentSeconds=time_seconds,
            comment=comment,
            started=log_datetime,
        )


def sync_external_redmine_system(
    redmine,
    date: str,
    start_time: str,
    task_id: str,
    activity_id: int,
    duration_hours: str,
    note: str,
):
    time_entry_data = {
        "issue_id": task_id,
        "hours": duration_hours,
        "comments": note,
    }

    if not activity_id:
        activity_id = 8

    time_entry_data["activity_id"] = activity_id

    if date:
        time_entry_data["spent_on"] = date

    if SIMULATE_REDMINE_SYNC:
        logger.info(
            f"... create external report {date=} {duration_hours=} {task_id=} {activity_id=} {note=}"
        )
        return False
    else:
        time_entry = redmine.time_entry.create(**time_entry_data)


def convert_time_to_seconds(time=float):
    return int(round(time * 3600))


def offset_to_belarus_time(time: str):
    time_list = time.split(":")
    hour = int(time_list[0])
    hour += DIFFERENCE_PL_BY
    if hour > 23:
        hour = 0
    time = str(hour)
    if hour < 10:
        time = "0" + time
    time += ":" + time_list[1] + ":" + time_list[2]

    return time
