import requests
from app.config import SLACK_BOT_TOKEN
from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from random import choice
from datetime import datetime, timedelta

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def log_brew(user_id, user_name, channel):
    # Log the brewing activity in the database
    supabase.table("brewing_logs").insert({
        "user_id": user_id,
        "user_name": user_name,
        "channel": channel
    }).execute()

    # Schedule the follow-up message
    supabase.table("brewing_jobs").insert({
        "user_id": user_id,
        "user_name": user_name,
        "channel": channel,
        "schedule_at": datetime.utcnow() + timedelta(minutes=10)
    }).execute()


def send_message(channel, text):
    """
    Sends a message to the specified Slack channel.
    """
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "channel": channel,
        "text": text
    }
    response = requests.post(url, headers=headers, json=data)

    if not response.ok:
        print(f"Failed to send message: {response.text}")


def get_channel_users(channel_id):
    """
    Fetch all non-bot users in a Slack channel.
    """
    url = "https://slack.com/api/conversations.members"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
    }
    params = {"channel": channel_id}
    response = requests.get(url, headers=headers, params=params).json()

    if not response.get("ok"):
        print(f"Error fetching channel members: {response}")
        return []

    members = response.get("members", [])
    non_bot_users = []

    for user_id in members:
        user_info = requests.get(
            "https://slack.com/api/users.info",
            headers=headers,
            params={"user": user_id}
        ).json()

        if user_info.get("ok") and not user_info["user"]["is_bot"]:
            user = user_info["user"]
            non_bot_users.append({
                "id": user["id"],
                "name": user["name"],  # Slack username
                "real_name": user.get("real_name")  # Display name
            })

    return non_bot_users


def pick_random_brewer(channel_id):
    """
    Pick a random user from the channel who has not been picked on the current day.
    """
    # Fetch all users in the channel
    all_users = get_channel_users(channel_id)

    # Get today's date
    today = datetime.utcnow().date()

    # Fetch users who have been selected today
    selected_today = supabase.table("selected_brewers")\
        .select("user_id, timestamp")\
        .eq("channel_id", channel_id)\
        .execute()

    selected_user_ids_today = {
        row["user_id"] for row in selected_today.data if datetime.fromisoformat(row["timestamp"]).date() == today
    }

    # Filter eligible users
    eligible_users = [user for user in all_users if user["id"] not in selected_user_ids_today]

    return choice(eligible_users) if eligible_users else None


def log_selected_brewer(user_id, user_name, channel_id):
    """
    Log the selected brewer in the database.
    """
    supabase.table("selected_brewers").insert({
        "user_id": user_id,
        "user_name": user_name,
        "channel_id": channel_id
    }).execute()


def log_last_cup(user_id, user_name, channel_id):
    """
    Log the user who took the last cup of coffee into Supabase.
    """
    supabase.table("last_cup_logs").insert({
        "user_id": user_id,
        "user_name": user_name,
        "channel_id": channel_id
    }).execute()


def log_accusation(accuser_id, accuser_name, accused_id, accused_name, channel_id):
    """
    Log an accusation into the Supabase database.
    """
    supabase.table("accusations").insert({
        "accuser_id": accuser_id,
        "accuser_name": accuser_name,
        "accused_id": accused_id,
        "accused_name": accused_name,
        "channel_id": channel_id
    }).execute()


def get_leaderboard_data(leaderboard_type):
    """
    Query the Supabase database for leaderboard data based on the specified type.
    """
    if leaderboard_type == "accused_leaderboard":
        query = """
            SELECT accused_name AS user_name, COUNT(*)::INTEGER AS count
            FROM accusations
            GROUP BY accused_name
            ORDER BY count DESC
            LIMIT 3;
        """
    elif leaderboard_type == "accuser_leaderboard":
        query = """
            SELECT accuser_name AS user_name, COUNT(*)::INTEGER AS count
            FROM accusations
            GROUP BY accuser_name
            ORDER BY count DESC
            LIMIT 3;
        """
    elif leaderboard_type == "brew_leaderboard":
        query = """
            SELECT user_name, COUNT(*)::INTEGER AS count
            FROM brewing_logs
            GROUP BY user_name
            ORDER BY count DESC
            LIMIT 3;
        """
    else:
        return []

    # Call the Supabase function
    response = supabase.rpc("execute_raw_sql", {"sql": query}).execute()

    # Debugging: Log the response
    print(f"Supabase RPC Response: {response}")

    # Check for errors in the response
    if not response.data:
        print(f"Supabase RPC Error: {response}")
        return []

    # Return the data
    return response.data
