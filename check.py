from daily_parser.parser import parse_log_file

parsed_logs = parse_log_file('logs/daily-jobs-for-posting-2.txt')

projects_file = 'projects.txt'

total_hours = 0
for project in parsed_logs:
    print(project)
    if project['time']:
        total_hours += float(project['time'])

print(f'total hours: {total_hours}')

