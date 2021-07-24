# Hosting on your own machine
## Installation
Download all 'main.py', 'requirements.txt', 'users.csv' and 'hw.csv' into a directory.
Run the following command below
```bash
pip install requirements.txt
```

## Telegram Token
On Telegram, search for Botfather and send '/newbot'. Specify your bot's name and username to obtain an API Token.
On line 13 of main.py, insert your token into the `TOKEN`. For example, `TOKEN="123456789"`.

## Starting the Bot
Botfather would have a link to your bot on its creation. Click on it and send /start to begin interacting.

### More Information
Our team, dionysus.io (Team ID 079) chose the education theme in order to improve learning in this post-covid age.

We decided to leverage Telegram and its ability to create bots in order to come up with a solution on a platform many are familiar with.

We used BotFather to create the telegram chat bot and proceeded to write it in python, its features include a task-manager esque list where teachers can input information and students can refer to. We also implemented a "pomodoro" feature that acts like a timer, students can input a task and a duration of their choosing. When the time is up the bot will then send a notification to the student.

We used the 'python-telegram-bot' module taught by NUS Hackers in one of LifeHack's workshop in order come up with a bot for both teachers and users. We had also refered to other projects involving telegram bots on github such as the conversationbot.py and inlinekeyboard.py by bibo-joshi. We used Pandas' Dataframes as our store for information as it is lightweight and flexible. Teachers can specify their subject and add homework to the dataframes which will then be accessible to the user. We made us of the modules features like job queues in order to send timed updates, and automatically remove old homework tasks.

One can use the link: http://t.me/dionysus_hw_bot to access our bot, there are further instructions within the bot to guide the user along.
