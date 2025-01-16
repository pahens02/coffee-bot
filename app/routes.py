from flask import Blueprint, request, jsonify
import requests
from app.utils import (
    send_message,
    delayed_message,
    log_brew,
    get_channel_users,
    pick_random_brewer,
    log_selected_brewer,
    log_last_cup,
    log_accusation,
    get_leaderboard_data
)
from app.config import SLACK_BOT_TOKEN, COFFEE_CHANNEL_ID

routes = Blueprint('routes', __name__)


def handle_dm(data, handler_function):
    """
    Handles commands sent via direct message (DM) and routes them to the appropriate handler function.
    Posts results to the coffee channel.
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

        # Schedule follow-up message
        delayed_message(COFFEE_CHANNEL_ID, "Coffee is ready!", 480)

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

    # Log the accusation with the accuser's name
    log_accusation(accuser_id, accuser_name, accused_id, accused_name, channel_id)

    # Notify the channel anonymously
    message = f"@{accused_name} has been accused of taking the last cup!"
    send_message(channel_id, message)

    # Respond to the accuser with a private acknowledgment
    return jsonify({
        "response_type": "ephemeral",
        "text": "Your accusation has been sent to the channel."
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

