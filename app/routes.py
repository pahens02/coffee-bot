from flask import Blueprint, request, jsonify
import requests
from datetime import datetime, timedelta
from app.utils import (
    supabase,
    send_message,
    log_brew,
    get_channel_users,
    pick_random_brewer,
    log_selected_brewer,
    log_last_cup,
    log_accusation,
    get_leaderboard_data,
    log_refutation
)
from app.config import SLACK_BOT_TOKEN, COFFEE_CHANNEL_ID

routes = Blueprint('routes', __name__)


def handle_dm(data, handler_function):
    """
    Handles commands sent via direct message (DM) and routes them to the appropriate handler function.
    Posts results to the channel.
    """
    user_id = data.get("user_id")
    user_name = data.get("user_name")
    text = data.get("text", "").strip()

    # Pass data to the handler function
    return handler_function(user_id, user_name, text)


@routes.route('/brew', methods=['POST'])
def brew():
    def handler(user_id, user_name, _):
        # Log the brewing activity
        log_brew(user_id, user_name, COFFEE_CHANNEL_ID)

        # Notify the channel
        initial_message = f"*{user_name}* has started brewing!"
        send_message(COFFEE_CHANNEL_ID, initial_message)

        return {"text": "Brewing timer started! The coffee channel will be notified."}

    return jsonify(handle_dm(request.form, handler))


@routes.route('/pick-brewer', methods=['POST'])
def pick_brewer():
    def handler(_, __, ___):
        # Fetch a user who has not been picked today
        selected_user = pick_random_brewer(COFFEE_CHANNEL_ID)
        if not selected_user:
            return {"text": "No eligible users found in the coffee channel!"}

        # Notify the channel
        user_name = selected_user["name"]
        message = f"@{user_name} you've been picked to brew!"
        send_message(COFFEE_CHANNEL_ID, message)

        # Log the selected brewer
        log_selected_brewer(selected_user["id"], user_name, COFFEE_CHANNEL_ID)
        return {"text": message}

    return jsonify(handle_dm(request.form, handler))


@routes.route('/running-low', methods=['POST'])
def running_low():
    def handler(_, __, ___):
        message = "☕ There's only one cup of coffee left! Get it while it's hot!"
        send_message(COFFEE_CHANNEL_ID, message)
        return {"text": "The coffee channel has been notified."}

    return jsonify(handle_dm(request.form, handler))


@routes.route('/last-cup', methods=['POST'])
def last_cup():
    def handler(user_id, user_name, _):
        # Log the user who took the last cup
        log_last_cup(user_id, user_name, COFFEE_CHANNEL_ID)

        # Notify the channel
        message = "☕ Coffee pot is empty!"
        send_message(COFFEE_CHANNEL_ID, message)

        return {"text": "The coffee channel has been notified."}

    return jsonify(handle_dm(request.form, handler))


@routes.route('/accuse', methods=['POST'])
def accuse():
    """
    Handles the /accuse command to log an accusation and notify the channel.
    """
    data = request.form

    # Extract data from the command payload
    accuser_id = data.get("user_id")
    accuser_name = data.get("user_name")
    input_text = data.get("text").strip()  # Slack sends the text following the command
    channel_id = data.get("channel_id")

    # Debugging: Log the raw input text
    print(f"Received input text: {input_text}")

    # Check if input is empty
    if not input_text:
        return jsonify({
            "response_type": "ephemeral",
            "text": "Please specify a user to accuse. Example: `/accuse username`"
        })

    # Try resolving as user ID directly (e.g., U12345678)
    if input_text.startswith("U") and len(input_text) > 5:
        accused_id = input_text
    else:
        # Otherwise, resolve input as a username
        accused_name = input_text.lstrip("@").strip()

        # Fetch users in the channel to resolve the username to user ID
        users = get_channel_users(channel_id)
        accused_user = next((user for user in users if user["name"] == accused_name), None)

        if not accused_user:
            return jsonify({
                "response_type": "ephemeral",
                "text": f"Could not find a user named {accused_name} in the channel."
            })

        accused_id = accused_user["id"]

    # Fetch accused user's details from Slack API
    user_info = requests.get(
        "https://slack.com/api/users.info",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        params={"user": accused_id}
    ).json()

    if not user_info.get("ok"):
        return jsonify({
            "response_type": "ephemeral",
            "text": f"Could not resolve user with ID {accused_id}."
        })

    accused_name = user_info["user"]["name"]

    # Log the accusation and get the accusation ID
    accusation_id = log_accusation(accuser_id, accuser_name, accused_id, accused_name, channel_id)

    # Notify the channel with the accusation and ID
    message = f"@{accused_name} has been accused of taking the last cup! (Accusation ID: {accusation_id})"
    send_message(channel_id, message)

    # Respond to the accuser with a private acknowledgment
    return jsonify({
        "response_type": "ephemeral",
        "text": f"Your accusation has been sent to the channel. Accusation ID: {accusation_id}"
    })


@routes.route('/leaderboard', methods=['POST'])
def leaderboard():
    def handler(_, __, leaderboard_type):
        valid_options = ["accused_leaderboard", "accuser_leaderboard", "brew_leaderboard"]
        if leaderboard_type not in valid_options:
            return {
                "text": "Invalid leaderboard type. Options are: accused_leaderboard, accuser_leaderboard, brew_leaderboard."}

        # Query leaderboard data
        leaderboard_data = get_leaderboard_data(leaderboard_type)

        # Debugging: Log leaderboard data
        print(f"Leaderboard Data: {leaderboard_data}")

        if not leaderboard_data:
            return {"text": f"No data available for {leaderboard_type}."}

        # Format leaderboard message
        leaderboard_message = f"📊 *{leaderboard_type.replace('_', ' ').title()} Top 3 Users:*\n"
        for rank, row in enumerate(leaderboard_data, start=1):
            leaderboard_message += f"{rank}. *{row['user_name']}* - {row['count']} points\n"

        # Notify the channel
        send_message(COFFEE_CHANNEL_ID, leaderboard_message)
        return {"text": "Leaderboard has been posted in the coffee channel."}

    return jsonify(handle_dm(request.form, handler))


@routes.route('/liar', methods=['POST'])
def liar():
    """
    Handles the /liar command to refute the most recent accusation made in the past 24 hours.
    """

    data = request.form

    # Extract data from the command payload
    channel_id = data.get("channel_id")

    # Calculate the 24-hour window
    time_limit = datetime.utcnow() - timedelta(hours=24)

    # Fetch the most recent accusation within the past 24 hours
    recent_accusation = supabase.table("accusations").select("*").filter(
        "timestamp", "gte", time_limit.isoformat()
    ).order("timestamp", desc=True).limit(1).execute()

    if not recent_accusation.data:
        return jsonify({
            "response_type": "ephemeral",
            "text": "No accusations found in the past 24 hours! Nothing to refute."
        })

    # Get the accusation details
    accusation = recent_accusation.data[0]
    accusation_id = accusation["id"]
    accused_name = accusation["accused_name"]

    # Log the refutation
    log_refutation(accusation_id, channel_id)

    # Notify the channel
    message = f"🔔 Accusation #{accusation_id} against @{accused_name} has been refuted! Let the debates begin!"
    send_message(channel_id, message)

    return jsonify({
        "response_type": "ephemeral",
        "text": f"Your refutation has been logged anonymously for accusation #{accusation_id} against @{accused_name}."
    })


@routes.route('/judge', methods=['POST'])
def judge():
    """
    Handles the /judge command to allow users to vote on an accusation.
    """
    data = request.form

    # Extract command data
    user_id = data.get("user_id")
    user_name = data.get("user_name")
    input_text = data.get("text").strip()

    # Parse the input
    try:
        accusation_id, vote = input_text.split()  # No need to cast to int
    except ValueError:
        return jsonify({
            "response_type": "ephemeral",
            "text": "Invalid format. Use `/judge accusation_id accept|reject`."
        })

    # Validate the vote
    if vote not in ["accept", "reject"]:
        return jsonify({
            "response_type": "ephemeral",
            "text": "Invalid vote. Use `accept` or `reject`."
        })

    # Log the vote
    supabase.table("votes").insert({
        "accusation_id": accusation_id,  # Keep as UUID (string)
        "voter_id": user_id,
        "voter_name": user_name,
        "vote": vote
    }).execute()

    return jsonify({
        "response_type": "ephemeral",
        "text": f"Your vote to {vote} accusation #{accusation_id} has been recorded."
    })


@routes.route('/call_vote', methods=['POST'])
def call_vote():
    """
    Tally votes for an accusation and announce the result.
    """
    data = request.form

    # Extract data from the command payload
    channel_id = data.get("channel_id")
    input_text = data.get("text").strip()

    # Parse the input
    accusation_id = input_text.strip()  # No need to cast to int

    # Fetch votes for the accusation
    votes = supabase.table("votes").select("*").filter(
        "accusation_id", "eq", accusation_id
    ).execute()

    if not votes.data:
        return jsonify({
            "response_type": "ephemeral",
            "text": f"No votes found for accusation #{accusation_id}."
        })

    # Tally votes
    accept_votes = sum(1 for vote in votes.data if vote["vote"] == "accept")
    reject_votes = sum(1 for vote in votes.data if vote["vote"] == "reject")

    # Determine result
    if accept_votes > reject_votes:
        result = f"✅ Accusation #{accusation_id} has been upheld with {accept_votes} accept votes and {reject_votes} reject votes!"
    elif reject_votes > accept_votes:
        result = f"❌ Accusation #{accusation_id} has been dismissed with {reject_votes} reject votes and {accept_votes} accept votes!"
    else:
        result = f"🤔 Accusation #{accusation_id} resulted in a tie with {accept_votes} accept votes and {reject_votes} reject votes."

    # Post result in the channel
    send_message(channel_id, result)

    return jsonify({
        "response_type": "ephemeral",
        "text": f"The votes for accusation #{accusation_id} have been tallied"
    })


