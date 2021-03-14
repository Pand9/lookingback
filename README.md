
# Easytrack

A time-tracking tool designed to optimize success of tracking.

## Functionality

Time tracking is boring. It's not your job.
Meticulous, systematic tracking is probably optional for you - not many companies are so strict as to enforce it.
So it's expected that you're not very motivated to it.
But - at the same time - the longer you ignore it, the harder it is to go back and fill missing entries.
Dealing with it is what makes it very difficult to keep up with your time entries.

This tool intends to address this problem, by
- making time entering extremely simple & natural
- assisting you in remembering (by tracking & showing you your OS activity)
- setting regular reminders for you

You type your entries into VSCode window, as a text. The Easyaccess framework deals with everything else.

- Access the VSCode session with a single keystroke.
- Add entries just by typing.
- Get reminder after an hour of not entering anything.
- Remember what you are doing by looking at system activity, such as focused windows and idle time. The data is being gathered in the background as you work.
- Be honest in your entries, then redact them and send to Toggl.

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

## Why the name

It was my first thought, it wasn't rational! However, the project's name works pretty well with its goal, as a time tracking tool - accessibility and ease of use.
