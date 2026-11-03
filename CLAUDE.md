
## Project index

Python CLI. Parses free-format daily work-hours log, pushes worklogs to Jira, Redmine, or internal office reporting system.

```
main.py - entry point: CLI args, project settings, sync loop per project
daily_parser/parser.py - log parser (time ranges, project keys, notes) -> list of dicts
daily_parser/reports.py - sync targets: internal office system, Jira worklog, Redmine time entry
projects.yaml - per-project sync settings (type internal/jira/redmine, urls, keys, main task) (not in git, see projects.yaml.sample)
projects.txt - special projects list, one per line (not in git, see projects.txt.sample)
.env - internal office system credentials (not in git, see env.sample)
requirements.txt - Python dependencies
.python-version - Python version (3.13)
run.sh - local run shortcut (sync of Downloads/Working hours.txt)
logs/ - run logs, one file per sync run (not in git)
README.md - usage
save_report.py, redmine-*.py, check_tasks_status.py, yaml_read.py, tests.py - old standalone helper/experiment scripts (not in git, not used by main.py)
```

## How to build and run - short overview

```bash
# setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp env.sample .env                       # fill office credentials
cp projects.yaml.sample projects.yaml    # fill project settings
cp projects.txt.sample projects.txt

# run
python3 main.py logs.txt                 # parse and show only
python3 main.py < logs.txt               # same, from stdin
python3 main.py logs.txt -sync           # sync for yesterday
python3 main.py logs.txt -sync=YYYY-MM-DD  # sync for given date
```

## Notes

- Use AskUserQuestion tool if you want to ask questions.

## Constraints

- do not commit to git automatically
- make specification for features concise
- make implementation plan for features also concise, focus on architecture and key tech implementation decisions
- always stop your run test services when all is checked

## Explanations

- For technical report use ASD-STE100 standard. But follow only ~80% of it, so feedback still stays human-ready.
– Instead of long explanation generate diagram or a picture.
– For complex explanations and topics generate interactive HTML page with visualisation and animations.
