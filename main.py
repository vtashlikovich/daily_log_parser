"""Daily logs parser checker."""

import sys
import os
from loguru import logger
from daily_parser.parser import parse_log_file, parse_log_stream
import yaml
from yaml.loader import SafeLoader
from datetime import date, timedelta
import requests
import datetime
import html
from pytz import timezone
from jira import JIRA
from dotenv import load_dotenv

load_dotenv()

requests.packages.urllib3.disable_warnings()

INTERNAL_URL = os.getenv("INTERNAL_URL")
INTERNAL_AUTH = os.getenv("INTERNAL_AUTH")
INTERNAL_USER = os.getenv("INTERNAL_USER")
INTERNAL_PASSWORD = os.getenv("INTERNAL_PASSWORD")
INTERNAL_USER_ID = os.getenv("INTERNAL_USER_ID")
TIME_DELTA_MINSK = 0


def remove_dash(line: str) -> str:
    if line.find("-") == 0:
        return line[1:].strip()
    else:
        return line


def single_line_notes(notes_list: list) -> str:
    processed_notes = [remove_dash(note) for note in notes_list]
    return "; ".join(processed_notes)


def convert_time_to_seconds(time=float):
    return int(round(time * 3600))


def create_internal_report(date: str, time: str, project: int,
                           duration: float, comment: str):
    headers = {
        "Authorization": "Basic " + INTERNAL_AUTH
    }

    comment = html.escape(comment)
    url = f"{INTERNAL_URL}?mode=json&cmd=saveReport&login={INTERNAL_USER}&pswd={INTERNAL_PASSWORD}&reportDate={date}&reportTime={time}&reportUser={INTERNAL_USER_ID}&reportProject={project}&duration={duration}&description={comment}"
    # print(url)
    requests.post(url, headers=headers, verify=False)


def create_jira_report(jira, issue: str, date: str, time: str, duration: float,
                       comment: str):
    date_parsed = date.split("-")
    time_parsed = time.split(":")

    time_seconds = convert_time_to_seconds(duration)

    log_datetime = datetime.datetime(year=int(date_parsed[0]), month=int(date_parsed[1]),
                                     day=int(date_parsed[2]),
                                     hour=int(time_parsed[0]), minute=int(time_parsed[1]), second=0, microsecond=0,
                                     tzinfo=timezone('CET'))

    jira.add_worklog(issue=issue, timeSpentSeconds=time_seconds, comment=comment,
                     started=log_datetime)


def read_special_projects() -> list[str]:
    result = []
    with open("projects.txt") as projects_file:
        for line in projects_file:
            result.append(line.lower().replace("\n", ""))

    return result


def format_minsk_time(log_time: str) -> str:
    time_split = log_time.split(":")
    hour = str(int(time_split[0]) + TIME_DELTA_MINSK)
    if len(hour) < 2:
        hour = "0" + hour
    time_split[0] = hour

    return ":".join(time_split)


def read_project_settings(projects_settings: dict, project_key: str | int):

    current_settings = None
    settings_dict = {}

    try:
        current_settings = projects_settings[str(project_key)]
    except KeyError:
        pass

    if not current_settings:
        current_settings = projects_settings[int(project_key)]

    if current_settings:
        for setting in current_settings:
            for key, value in setting.items():
                settings_dict[key] = value

    return settings_dict


# >>>>> GO!

parsed_logs = None
sync_enabled = False
day_to_sync = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
# day_to_sync = "2023-02-17"

# parse file name from args
if sys.stdin.isatty():
    file_name = None
    if len(sys.argv) > 1:
        file_name = sys.argv[1]

        if len(sys.argv) > 2:
            sync_cmd = "-sync"
            sync_enabled = sys.argv[2].startswith(sync_cmd)
            if len(sys.argv[2]) > len(sync_cmd):
                day_to_sync = sys.argv[2][len(sync_cmd) + 1:]
            if sync_enabled:
                logger.info(f"{sync_enabled=} {day_to_sync=}")

        logger.info(f"parse a log file {file_name}")
        parsed_logs = parse_log_file(file_name)
    else:
        logger.error("no incoming file is found")

# read file from the input stream
else:
    logger.info("read logs stream")
    parsed_logs = parse_log_stream(sys.stdin)


# if sync is enabled we need to read projects settings from yaml file
projects_settings = None

if sync_enabled:
    with open("projects.yaml") as f:
        projects_settings = yaml.load(f, Loader=SafeLoader)

total_hours = 0
if parsed_logs:
    projects_in_minsk = read_special_projects()

    for project in parsed_logs:
        project_start = project["start"]
        if project["project"].lower() in projects_in_minsk:
            project_start = format_minsk_time(project_start)

        print(project_start)
        print(project["project"])
        print(project["time"])

        for note in project["notes"]:
            if not note.startswith("-"):
                note = "- " + note
            print(note)
        print()

        # sync reports if needed
        if sync_enabled:
            project_key = project["project"].lower()

            current_settings = read_project_settings(
                projects_settings, project_key)

            project_start = project_start + ":00"
            duration = float(project["time"])

            note = single_line_notes(project["notes"])

            if current_settings["type"] == "internal":
                create_internal_report(day_to_sync, project_start,
                                       current_settings["id"], str(duration), note)
            elif current_settings["type"] == "jira":
                jira = JIRA(server=current_settings["url"],
                            basic_auth=(current_settings["user"], current_settings["api_key"]))

                create_jira_report(
                    jira, current_settings["main_task"], day_to_sync, project_start, duration, note)
            else:
                logger.error(
                    "ERROR: cannot sync project, type is unrecognized!")

        if project["time"]:
            total_hours += float(project["time"])

    print(f"Total hours: {total_hours}")
    logger.success("done")
