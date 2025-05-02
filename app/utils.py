import requests
from app.config import SLACK_BOT_TOKEN, SUPABASE_SERVICE_KEY
from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from random import choice
from datetime import datetime, timedelta

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def log_brew(user_id, user_name, channel):
    """
    Logs the brewing activity in the database and schedules a follow-up message.
    """

    # Log the brewing activity
    supabase.table("brewing_logs").insert({
        "user_id": user_id,
        "user_name": user_name,
        "channel": channel,
        "timestamp": datetime.utcnow().isoformat()  # Add a timestamp
    }).execute()

    print("Brewing activity logged and follow-up message scheduled.")


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
    Log an accusation into the Supabase database and return the generated accusation ID.
    """
    result = supabase.table("accusations").insert({
        "accuser_id": accuser_id,
        "accuser_name": accuser_name,
        "accused_id": accused_id,
        "accused_name": accused_name,
        "channel_id": channel_id,
        "timestamp": datetime.utcnow().isoformat()  # timestamp for filtering
    }).execute()

    # Return the accusation ID from the result
    return result.data[0]["id"]


def get_leaderboard_data(leaderboard_type):
    """
    Query Supabase for leaderboard data using predefined views or raw SQL.
    """
    if leaderboard_type == "accused_leaderboard":
        query = "SELECT accused_name AS user_name, accusations AS count FROM public.acussed_leaderboard LIMIT 3;"

    elif leaderboard_type == "accuser_leaderboard":
        query = "SELECT accuser_name AS user_name, accusations_made AS count FROM public.acusser_leaderboard LIMIT 3;"

    elif leaderboard_type == "brew_leaderboard":
        query = "SELECT user_name, brew_count::INTEGER AS count FROM public.brew_leaderboard LIMIT 3;"

    elif leaderboard_type == "brew_leaderboard_all_time":
        query = """
            SELECT user_name, COUNT(*)::INTEGER AS count
            FROM brewing_logs
            GROUP BY user_name
            ORDER BY count DESC
            LIMIT 3;
        """

    elif leaderboard_type == "restock_leaderboard":
        query = "SELECT user_name, count FROM public.restock_leaderboard;"

    elif leaderboard_type == "restock_leaderboard_all_time":
        query = """
            SELECT user_name, SUM(points)::INTEGER AS count
            FROM restock_logs
            GROUP BY user_name
            ORDER BY count DESC
            LIMIT 3;
        """

    elif leaderboard_type == "last_cup_leaderboard":
        query = "SELECT user_name, times_last_cup AS count FROM public.last_cup_leaderboard LIMIT 3;"

    elif leaderboard_type == "brewer_monthly_winners":
        response = supabase.table("brewer_monthly_winners").select("month_name, summary").order("month").execute()
        return response.data if response.data else []

    elif leaderboard_type == "restock_monthly_winners":
        response = supabase.table("restock_monthly_winners").select("month_name, summary").order("month").execute()
        return response.data if response.data else []

    else:
        return []

    # Execute the query using Supabase RPC
    response = supabase.rpc("execute_raw_sql", {"sql": query}).execute()

    # Log and handle errors
    print(f"Supabase RPC Response: {response}")
    if not response.data:
        print(f"Supabase RPC Error: {response}")
        return []

    return response.data


def log_refutation(accusation_id, channel_id):
    """
    Logs a refutation anonymously into the Supabase database using the accusation ID.
    """
    # Fetch accusation details from the database
    accusation = supabase.table("accusations").select("*").eq("id", accusation_id).execute()

    if not accusation.data:
        raise ValueError(f"Accusation with ID {accusation_id} not found.")

    accused_id = accusation.data[0]["accused_id"]
    accused_name = accusation.data[0]["accused_name"]

    # Insert the refutation record
    result = supabase.table("refutations").insert({
        "accusation_id": accusation_id,
        "accused_id": accused_id,
        "accused_name": accused_name,
        "channel_id": channel_id,
        "timestamp": datetime.utcnow().isoformat()
    }).execute()

    if not result.data:
        raise ValueError("Failed to log refutation: No data returned from the database.")
    return result.data[0]["id"]


def log_restock(user_id, user_name, item, quantity):
    item = item.lower()
    item_points = {
        "creamer": 2,
        "coffee": 3,
        "filters": 3,
        "syrup": 1
    }

    if item not in item_points:
        raise ValueError(f"Unknown item type: {item}")

    points = item_points[item] * quantity

    supabase.table("restock_logs").insert({
        "user_id": user_id,
        "user_name": user_name,
        "item": item,
        "quantity": quantity,
        "points": points,
        "timestamp": datetime.utcnow().isoformat()
    }).execute()

    return points

