# codeql-installer

Install & Update CodeQL easily

## How To Install

```bash
git clone https://github.com/realgam3/codeql-installer.git "codeql-home"
cd "codeql-home"
pip install -r "requirements.txt"
python codeql-installer.py
```

## How To Update

Create ScheduleTask / CronJob for `python codeql-installer.py`.
