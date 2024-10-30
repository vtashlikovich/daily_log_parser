"""Daily logs parser checker."""

import sys
from datetime import date, timedelta, datetime
from loguru import logger
import yaml
from yaml.loader import SafeLoader
from jira import JIRA
from dotenv import load_dotenv
from redminelib import Redmine
from enum import Enum

load_dotenv()

from daily_parser.parser import parse_log_file, parse_log_stream
from daily_parser.reports import (
    create_internal_report,
    create_jira_report,
    sync_external_redmine_system,
)


# Redmine activities list
class Activities(Enum):
    Design = 8
    Dev = 9
    BA = 10
    Test = 11
    Code_Review = 12
    Documentation = 13
    Non_dev = 14


logger.remove()
log_level = "DEBUG"
log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS zz}</green> | <level>{level}</level> | <b>{message}</b>"
logger.add(sys.stdout, level="INFO", format=log_format, colorize=True, backtrace=True, diagnose=True)

# -1 when in PL and DST is on (1 hour difference)
# 0 when in PL and DST is off (2 hours difference)
TIME_DELTA_MINSK = -1


def remove_dash(line: str) -> str:
    if line.find("-") == 0:
        return line[1:].strip()
    else:
        return line


def single_line_notes(notes_list: list) -> str:
    processed_notes = [remove_dash(note) for note in notes_list]
    return "; ".join(processed_notes)


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


def note_is_meeting(note: str) -> bool:
    return "meet" in note or "meeting" in note or "discussion" in note


def read_project_settings(projects_settings: dict, project_key: str | int):

    current_settings = None
    settings_dict = {}

    try:
        current_settings = projects_settings[str(project_key)]
    except KeyError:
        pass

    try:
        if not current_settings:
            current_settings = projects_settings[int(project_key)]
    except ValueError:
        pass

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

with open("projects.yaml") as f:
    projects_settings = yaml.load(f, Loader=SafeLoader)

if sync_enabled:
    now = datetime.now()
    logger.add("logs/" + now.strftime("%m.%d.%Y-%H.%M.%S") + ".log", level=log_level, format=log_format,
               colorize=False, backtrace=True, diagnose=True)

total_hours = 0
hours_by_projects = {}
project_switch_num = 0
last_project = ""
if parsed_logs:
    projects_in_minsk = read_special_projects()

    for project in parsed_logs:
        start_time = project["start"]
        project_key = project["project"].lower()
        task_id = project["task"]
        if project_key in projects_in_minsk:
            start_time = format_minsk_time(start_time)

        logger.info(start_time)
        logger.info(task_id)
        logger.info(project_key)
        logger.info(project["time"])

        for note in project["notes"]:
            if not note.startswith("-"):
                note = "- " + note
            logger.info(note)
        logger.info("")

        current_settings = read_project_settings(
            projects_settings, project_key)

        if "type" not in current_settings:
            logger.error(f'project key "{project_key}" not found in configuration')

        # gather statistics of total hours by projects
        if project_key in hours_by_projects:
            hours_by_projects[project_key] += float(project["time"])
        else:
            hours_by_projects[project_key] = float(project["time"])

        # count project switches
        if last_project != project_key:
            if last_project != "":
                project_switch_num += 1
            last_project = project_key

        # sync reports if needed
        if sync_enabled:

            start_time = start_time + ":00"
            duration = float(project["time"])

            note = single_line_notes(project["notes"])

            if current_settings["type"] == "internal":

                # custom start
                activity_id = Activities.Dev.value

                if task_id is None and "main_task" in current_settings:
                    task_id = current_settings["main_task"]
                    if "meet_task" in current_settings and note_is_meeting(note):
                        task_id = current_settings["meet_task"]
                        activity_id = Activities.Non_dev.value
                # custom end

                internal_note = note

                if "format_note" in current_settings:
                    internal_note = f"#{task_id} {note}"

                create_internal_report(
                    day_to_sync,
                    start_time,
                    current_settings["id"],
                    str(duration),
                    internal_note,
                )

                if "sync" in current_settings:
                    if current_settings["sync"] == "redmine":
                        redmine = Redmine(
                            current_settings["url"], key=current_settings["apikey"]
                        )

                        sync_external_redmine_system(
                            redmine,
                            day_to_sync,
                            start_time,
                            task_id,
                            activity_id,
                            str(duration),
                            note,
                        )

            elif current_settings["type"] == "jira":
                jira = JIRA(server=current_settings["url"],
                            basic_auth=(current_settings["user"], current_settings["api_key"]))

                jira_task = current_settings["main_task"]
                if "meet_task" in current_settings and note_is_meeting(note):
                    jira_task = current_settings["meet_task"]

                create_jira_report(
                    jira, jira_task, day_to_sync, start_time, duration, note
                )
            else:
                logger.error(
                    "ERROR: cannot sync project, type is unrecognized!")

        if project["time"]:
            total_hours += float(project["time"])

    # print total logs count
    logger.info(f"Logs count: {len(parsed_logs)}")

    # print total project switches
    logger.info(f"Project switches: {project_switch_num}")

    # print statistics of total hours by projects
    for project, hours in hours_by_projects.items():
        logger.info(f"- {project}: {hours}")

    logger.info(f"")
    logger.info(f"--Total hours: {total_hours}")

    logger.success("done")
