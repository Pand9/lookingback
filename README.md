# Easytrack

A time-tracking tool kit, currently a mess.

## Functionality

Time tracking while focusing on work can be off putting.

- Make time entering maximally simple & natural
- Assist you in remembering what you've been up to (by tracking & showing you your OS activity)
- Guide you to a setup where you are always one keystroke from opening a time tracking window.
- Set up regular reminders for you

You type your entries into a window, as a text. The Easyaccess framework deals with everything else.

- Access the VSCode session with a single keystroke.
- Add entries just by typing.
- Get reminder after an hour of not entering anything.
- Remember what you are doing by looking at system activity, such as focused windows and idle time. The data is being gathered in the background as you work.
- Be honest in your entries, then redact them and send to e.g. Toggl.

## Technical details
- Supported setup for event gatherer: x11 + i3 wm. If you have a different setup - DIY, it's easy enough!
- - See [doc/plan.tasks] to monitor the progress

## How to use it

- Requires linux with x11 (almost any linux) and i3 (almost noone uses it; I might remove this dependency later)
- Some keyboard shortcuts are on you
- Some entries go to crontab - also on you
- Need to install vscode
- Setup a venv & set an env variable (i'll get to it when it's implemented)
- That's it!

# Guides

## Example on how to setup background processes

Configure to run this on login.

```bash
# recreate screens that maintain background process

# send screen-specific "quit" command to last session to clean it up
screen -S easytrack-remind -X quit
# create the new session from scratch, in detached state
screen -dmS easytrack-remind
# use screen-specific "stuff" command to send
# the command into the detached session
screen -S easytrack-remind -X stuff 'watch -n300 /home/ks/personal/easyinsert/src/bash/run.sh remind\n'


# send screen-specific "quit" command to last session to clean it up
screen -S easytrack-monitor -X quit
# create the new session from scratch, in detached state
screen -dmS easytrack-monitor
# use screen-specific "stuff" command to send
# the command into the detached session
screen -S easytrack-monitor -X stuff 'watch -n60 /home/ks/personal/easyinsert/src/bash/run.sh monitor --ticks 60\n'
```