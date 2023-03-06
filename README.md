# Daily log parser

It parses daily hours logs in a free manual format, pushes them into the appropriate Jira projects or internal offic system

## How to run

```bash
# just displays the content of the log
python3 check.py logs.txt
OR
python3 check.py < logs.txt

# syncs with appropriate projects for yesterday
python3 check.py logs.txt -sync

# syncs with appropriate projects for the specified data
python3 check.py logs.txt -sync=YYYY-MM-DD
```