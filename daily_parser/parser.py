"""Reads daily job logs and parses them into the structured data."""

from sys import argv as sys_argv
from loguru import logger

LOG_START = 10
LOG_NOTES = 20
LOG_END = 30

def is_time_format(time: str) -> bool:
    """Checks if time format hh:mm was used."""
    result = False

    try:
        time_list = time.split(':')
        result = (len(time) > 2 and len(time_list) == 2 and
            int(time_list[0]) >= 0 and int(time_list[1]) >= 0)
    except ValueError:
        pass
        # print('Error while parsing time ' + time)

    return result

def is_log_start(pline: str) -> bool:
    """Determines if log starts at this line."""

    line_parts = pline.split('/')
    result = len(line_parts) > 1 and is_time_format(line_parts[0]) \
        or is_time_format(pline)

    return result

def is_log_end(pline: str) -> bool:
    """Determines if log ends at this line."""
    result = False
    try:
        parsed_val = float(pline)
        result = parsed_val > 0
    except ValueError:
        pass

    return result

def get_log_type(pline: str) -> int:
    """Determines the line log type."""

    line_type = LOG_NOTES

    if is_log_start(pline):
        line_type = LOG_START
    elif is_log_end(pline):
        line_type = LOG_END

    return line_type

def parse_log_time(pline: str) -> str:
    """Returns time from the log start."""
    pline_splited = pline.split('/')
    return pline_splited[0].strip() if len(pline_splited) > 1 else pline

def parse_log_project(pline: str) -> str:
    """Parse project title."""
    project_title = ''.join(pline.split('/')[1:]).strip()
    complex_title = project_title.split(',')
    if len(complex_title) > 1:
        project_title = complex_title[0].strip()

    return project_title

def parse_log_notes(pline: str, notes: list[str]) -> None:
    """Find and store note after the project title if any"""
    complex_title = pline.split(',')
    if len(complex_title) > 1:
        anote = ''.join(complex_title[1:]).strip()
        anote = anote.replace('\n', '')
        if len(anote) > 0:
            notes.append(anote)

def get_time_min(pline: str) -> int:
    """Gets time from the string and returns time in minutes."""
    time = parse_log_time(pline)
    time_split = time.split(':')

    if len(time_split) > 1:
        return int(time_split[0]) * 60 + int(time_split[1])

    return 0

def convert_time2hours(time: int) -> str:
    """Convert time integer to hours (min 0.5)."""

    time_div = divmod(time, 60)
    hours = time_div[0]

    if time_div[1] > 30:
        hours += 1
    elif time_div[1] >= 10:
        hours += 0.5

    return str(hours)

def calc_log_end(cur_log_start, pline) -> str:
    """Calculate the length of the logged job"""
    log_time = None

    try:
        time1 = get_time_min(cur_log_start)
        time2 = get_time_min(pline)
        log_time = convert_time2hours(time2 - time1)
    except ValueError:
        pass

    return log_time

def parse_log_stream(stream) -> list[dict]:
    """Parses incoming file stream and searches for logs."""
    result = []

    cur_log_start = None
    cur_log_project = None
    cur_log_notes = []
    cur_log_time = None

    for line in stream:
        if line.startswith('--------'):
            break

        line = line.replace('\n', '')
        log_type = get_log_type(line)

        if ((log_type == LOG_START or log_type == LOG_END) and
            not cur_log_project is None and cur_log_project):

            if log_type == LOG_END:
                cur_log_time = line

            if log_type == LOG_END and is_time_format(line):
                result.append({
                    'start': cur_log_start,
                    'project': cur_log_project,
                    'notes': cur_log_notes,
                    'time': calc_log_end(cur_log_start, line).replace('\n', '')
                })
            else:
                result.append({
                    'start': cur_log_start,
                    'project': cur_log_project,
                    'notes': cur_log_notes,
                    'time': (cur_log_time if cur_log_time is not None \
                        else calc_log_end(cur_log_start, line)).replace('\n', '')
                })

            if log_type == LOG_END:
                cur_log_start = None
                cur_log_project = None
                cur_log_notes = []
                cur_log_time = None
            else:
                cur_log_start = parse_log_time(line)
                cur_log_project = parse_log_project(line)
                cur_log_notes = []
                parse_log_notes(line, cur_log_notes)
                cur_log_time = None
        elif log_type == LOG_START:
            cur_log_start = parse_log_time(line)
            cur_log_project = parse_log_project(line)
            parse_log_notes(line, cur_log_notes)
        elif log_type == LOG_NOTES:
            proc_line = line.replace('\n', '')
            if len(proc_line) > 0:
                cur_log_notes.append(proc_line)
        elif log_type == LOG_END:
            cur_log_time = line

        # print(f'{log_type}: {line}', end='')

    if cur_log_start is not None and cur_log_project:
        logger.error('Working finish time is not set!')

    return result

def parse_log_file(file_to_path: str) -> list[dict]:
    with open(file_to_path) as daily_file:
        parsed_log_dict = parse_log_stream(daily_file)

    return parsed_log_dict

# ================================================

if __name__ == '__main__':
    if len(sys_argv) > 1:
        file_name = sys_argv[1]

        parsed_logs = parse_log_file(file_name)

        total_hours = 0
        for project in parsed_logs:
            print(project)
            if project['time']:
                total_hours += float(project['time'])

        print(f'{total_hours=}')
