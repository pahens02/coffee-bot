# A Slack Coffee-Bot for Drama and Glory
This is a project I made so that the 2nd floor of my office could track our coffee pot and have a more consistent brewing schedule

However, 
I also wanted to gamify the proccess and capitalize on naturally occuring drama surrounding the coffee pot. 
Who took the last cup? Who always brews but never gets credit? Who in the office even drinks coffee? Are those creamer pods moldy and should we throw them out?

All important questions that could be answered with a system built on self reported behavior and a love of the game

(Except the last one... I already threw out the creamer pods)

**Table of Contents**:

- [Setup](#setup)
  - [Slack](#slack)
  - [Supabase](#supabase)
  - [Vercel](#vercel)
  - [Slack Again](#slack-again)
- [Slack Files](app)
- [Supabase Files](supabase)
- [Rollout Process](Documentation/Rollout_Process)
- [What it Looks Like in Action](Documentation/In_Action)

## Setup
This coffee bot is entirely built using the free tiers of several platforms. 
The project uses the slack api / bot creation online features, Supabase for storing data and long running background 
proccesses, and Vercel for deployment and to get a real URL for our slack endpoints

### Slack
Vist https://api.slack.com/quickstart for a guide on how to build this specific type of slack app that utilizes *webhooks*, after you have created your app you need to get the following variables:
- SLACK_BOT_TOKEN
- SIGNING_SECRET
- COFFEE_CHANNEL_ID (the channel id for where you want the bot to post, if you need a first floor coffee-bot and a second floor coffee-bot you will need two of these)
- A webhook for the channel where you want your bot to post (if you need a first floor coffee-bot and a second floor coffee-bot you will need two of these)

In the Documentation folder of this project there is a detailed README from Slack that walks you though how to start a project from scratch and run it locally.

However this repo already has the necessary project structure and files, so the main portion you will need is:

```zsh
# Run app locally
$ slack run

Connected, awaiting events
```
For local testing
### Supabase
Visit https://supabase.com/docs, sign up, and create a new project. After creating the project you will need the following variables:
- SUPABASE_URL
- SUPABASE_SERVICE_KEY

Then check out the supabase_enabled_extensions file and make sure you have everything installed.
To install, go to Database and then Extensions.

The next step is to run **all** of the queries in the [supabase_setup.sql](Documentation/supabase/supabase_setup.sql) file. I recommend breaking the Tables, Views, Functions, 
and Cron Jobs queries into separate snippets and make sure to sub in any placeholder values like webhooks

### Vercel
Visit https://vercel.com/, sign up, and connect your coffee-bot github repo to your account. 

Before deploying you will have a chance to set environment variables and you will need the following:
- SLACK_BOT_TOKEN
- SIGNING_SECRET
- COFFEE_CHANNEL_ID
- SUPABASE_URL
- SUPABASE_SERVICE_KEY

After you have those proceed with deployment, now you will have an external URL that you can use for your slack commands!

### Slack Again
Now that you have an external URL you can go back to your slack app project and add the following commands:
- /brew
  - Request URL: https://your-coffee-bot.vercel.app/brew (replace with your url and change the / at the end for each command)
  - Description: Starts brewing timer
- /pick-brewer
  - Randomly pick someone to brew the next pot
- /running-low
  - Notify the channel that coffee is running low
- /last-cup
  - Anonymously informs the channel that the pot is empty
- /accuse
  - Accuse someone of taking the last cup of coffee
- /leaderboard
  - Display the top 3 users for a specified leaderboard.
  - Usage Hint: brew_leaderboard
- /liar
  - Dispute the most recent /accuse
- /judge
  - Record your vote on the accusation
- /call_vote
  - Sum up the votes for the most recent accusation
