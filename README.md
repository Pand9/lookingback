

# Easyaccess

Time tracking is not your main focus, so if you're supposed to do it, it must be super simple.

This tool is doing its best to make time tracking

- easy to do
- easy to keep at (hard to forget about doing it)
- easy to catch up when you stop
- comfortable & honest

You type your entries into VSCode window, as a text. The Easyaccess framework deals with everything else.

- Access the VSCode session with a single keystroke.
- Add entries just by typing.
- Get reminder after an hour of not entering anything.
- Remember what you are doing by looking at system activity, such as focused windows and idle time. The data is being gathered in the background as you work.
- Be honest in your entries, then redact them and send to Toggl.

## Motivation

The hard parts about time tracking are:
- doing the actual boring chore (entering time)
- not forgetting about it
- remembering what you were doing - esp. if you forgot about doing it regularly
- being honest with yourself about your activity

The toolset won't solve your difficulties, but especially with honesty, but it's a good start.
Main principles are:

#### Accessibility (for developers)!

The process of entering a time entry is always the same - use your shortcut, and then type "HH:MM - HH:MM (Human-readable description)". No varation, no web-interfaces, no mouse-pointing, no dropdowns.

#### (Try to) observe yourself

Self-observation is very hard, especially if something doesn't go right and you're not happy with yourself.

If I had to name a single goal of this project, is to promote self-observation.

- Look at your worklog often
- Write your entry with your own words
- Be honest, because it's private - if you need to export it, Easyaccess will help you rewrite it
- Don't stress if you forget to log - system logs will help you get back on track
- Be honest, again. Lack of observation is blocker to improvement. Feel even free to enter 8 hours of "leisure time", because noone else will see it, and it will help you be honest with yourself about it.

Taking a honest look at your process is a first step in improving productivity and estimation skill, and is important to being a honest & happy developer.

## Technical details
- Supported setup for event gatherer: x11 + i3 wm. If you have a different setup - DIY, it's easy!
- - See [doc/plan.tasks] to monitor the progress

## How to use it

- Requires linux with x11 (almost any linux) and i3 (almost noone uses it; I might remove this dependency later)
- Some keyboard shortcuts are on you
- Some entries go to crontab - also on you
- Need to install vscode
- Setup a venv & set an env variable (i'll get to it when it's implemented)
- That's it!