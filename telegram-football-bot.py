import logging
import random
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, PollAnswerHandler, MessageHandler, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dictionary to store manual participants for each chat
manual_participants = {}

# Dictionary to store latest poll data for each chat
latest_polls = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    keyboard = [
        [InlineKeyboardButton("Add players", callback_data="cmd_add"),
         InlineKeyboardButton("Randomize teams", callback_data="cmd_randomize_manual")],
        [InlineKeyboardButton("Create poll", callback_data="cmd_create_poll"),
         InlineKeyboardButton("Randomize from poll", callback_data="cmd_randomize")],
        [InlineKeyboardButton("Clear data", callback_data="cmd_clear")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Welcome to the Football Team Randomizer Bot!\n\n"
        "You can use buttons or commands:\n"
        "/add name1 name2 name3... - Add players manually, separating names with spaces\n"
        "/randomize_manual - Randomize teams from manually added players\n"
        "/create_poll - Create a poll that will be tracked by the bot\n"
        "/randomize - Randomize teams from people who voted YES in the poll\n"
        "/use_poll - Use as a reply to a poll to select it for randomization\n"
        "/add_voters name1 name2... - Add participants to the selected poll\n"
        "/clear - Clear player and poll data\n\n"
        "The bot can randomize teams in two ways:\n"
        "1. From a poll (/create_poll or /use_poll, then /randomize)\n"
        "2. From a manually entered player list (/add, then /randomize_manual)",
        reply_markup=reply_markup
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add players to the list from space-separated names."""
    chat_id = update.effective_chat.id

    if chat_id not in manual_participants:
        manual_participants[chat_id] = []

    # Get text after command
    message_text = update.message.text
    command_parts = message_text.split(' ', 1)

    if len(command_parts) < 2:
        await update.message.reply_text("Enter player names after the command, separating them with spaces.\nFor example: /add Adam Peter Mark")
        return

    # Extract names from input text
    names_text = command_parts[1]
    names = [name.strip() for name in names_text.split() if name.strip()]

    if not names:
        await update.message.reply_text("No names found. Enter player names after the command, separating them with spaces.")
        return

    # Clear previous list
    manual_participants[chat_id] = []

    # Add names to the list
    for name in names:
        manual_participants[chat_id].append({
            'id': len(manual_participants[chat_id]),  # Using index as id for manual entries
            'name': name
        })

    player_list = "\n".join([f"{i+1}. {player['name']}" for i, player in enumerate(manual_participants[chat_id])])
    await update.message.reply_text(f"Added {len(names)} players to the list:\n{player_list}\n\nUse /randomize_manual to divide them into teams.")

async def randomize_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Randomize manual players into two teams."""
    chat_id = update.effective_chat.id

    if chat_id not in manual_participants or not manual_participants[chat_id]:
        await update.message.reply_text("The player list is empty! Add players using the /add command.")
        return

    # Make a copy of the player list and shuffle it
    players = manual_participants[chat_id].copy()
    random.shuffle(players)

    # Split into two teams
    half = len(players) // 2
    team1 = players[:half]
    team2 = players[half:]

    # Generate team lists with full names
    team1_list = "\n".join([f"{i+1}. {player['name']}" for i, player in enumerate(team1)])
    team2_list = "\n".join([f"{i+1}. {player['name']}" for i, player in enumerate(team2)])

    message = f"🏆 Teams have been randomized from manually added list 🏆\n\n"
    message += f"⚽️ Team 1 ({len(team1)}):\n{team1_list}\n\n"
    message += f"⚽️ Team 2 ({len(team2)}):\n{team2_list}"

    # Create randomize again button
    keyboard = [[InlineKeyboardButton("Randomize again", callback_data="manual_randomize_again")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(message, reply_markup=reply_markup)

async def create_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a poll that the bot can track properly."""
    chat_id = update.effective_chat.id

    message = await context.bot.send_poll(
        chat_id=chat_id,
        question="Are you playing on Thursday?",
        options=["Yes", "No"],
        is_anonymous=False
    )

    poll_id = message.poll.id
    latest_polls[chat_id] = {
        'poll_id': poll_id,
        'options': message.poll.options,
        'voters': []
    }

    await update.message.reply_text(
        "Poll has been created! The bot will automatically track YES responses."
    )

async def use_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Use a specific poll for team creation."""
    if not update.message.reply_to_message:
        await update.message.reply_text("This command must be used as a reply to a poll.")
        return

    replied_message = update.message.reply_to_message

    if not replied_message.poll:
        await update.message.reply_text("This is not a poll. Reply to a message with a poll.")
        return

    chat_id = update.effective_chat.id
    poll_id = replied_message.poll.id

    logger.info(f"Registered poll with ID {poll_id} in chat {chat_id}")

    # Ask for people who voted YES
    keyboard = [[InlineKeyboardButton("Add participants manually", callback_data="add_poll_participants")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Initialize a new poll entry
    latest_polls[chat_id] = {
        'poll_id': poll_id,
        'options': replied_message.poll.options,
        'voters': []
    }

    # Notify the user
    await update.message.reply_text(
        "Poll has been registered!\n\n"
        "NOTE: The bot cannot see previous votes. To add people who have already voted YES, "
        "press the button below and enter their names manually, or wait for new votes.",
        reply_markup=reply_markup
    )

async def add_voters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add voters manually to the last registered poll."""
    chat_id = update.effective_chat.id

    if chat_id not in latest_polls or latest_polls[chat_id].get('poll_id') is None:
        await update.message.reply_text("First select a poll using /use_poll as a reply to a poll.")
        return

    # Get text after command
    message_text = update.message.text
    command_parts = message_text.split(' ', 1)

    if len(command_parts) < 2:
        await update.message.reply_text("Enter the names of people who voted YES, separated by spaces.")
        return

    # Extract names
    names_text = command_parts[1]
    names = [name.strip() for name in names_text.split() if name.strip()]

    if not names:
        await update.message.reply_text("No names found.")
        return

    # Add people to the voter list
    for i, name in enumerate(names):
        # Check if this might be a full name
        name_parts = name.split(' ', 1)
        full_name = name  # Default to using the full provided text

        latest_polls[chat_id]['voters'].append({
            'id': f"manual_{i}_{random.randint(1000, 9999)}",  # Use a unique ID for manually added players
            'name': full_name,
            'option_ids': [0]  # Assume they voted for the first option (YES)
        })

    voters_count = len(latest_polls[chat_id]['voters'])
    await update.message.reply_text(
        f"Added {len(names)} players to the poll.\n"
        f"There are now a total of {voters_count} people voting YES in the poll.\n"
        f"Use /randomize to randomize teams."
    )

async def process_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process and store information about polls in the chat."""
    if update.poll:
        return  # We only care about new polls, not updates

    if update.message and update.message.poll:
        chat_id = update.effective_chat.id
        poll_id = update.message.poll.id

        logger.info(f"New poll with ID {poll_id} in chat {chat_id}")

        # Initialize a new poll entry
        latest_polls[chat_id] = {
            'poll_id': poll_id,
            'options': update.message.poll.options,
            'voters': []
        }

        # Suggest using /use_poll
        keyboard = [[InlineKeyboardButton("Use this poll", callback_data="use_this_poll")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "New poll detected! To use it for team randomization, reply to it with the /use_poll command",
            reply_markup=reply_markup
        )

async def process_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process poll answers to collect voters."""
    poll_id = update.poll_answer.poll_id
    user = update.effective_user
    option_ids = update.poll_answer.option_ids  # List of selected options

    # Full name of the user
    full_name = user.first_name
    if user.last_name:
        full_name += f" {user.last_name}"

    logger.info(f"Received response to poll {poll_id} from user {full_name}, options: {option_ids}")

    # Find the chat with this poll
    found = False
    for chat_id, poll_data in latest_polls.items():
        if poll_data.get('poll_id') == poll_id:
            found = True
            # Remove the user from the voter list if they were already there
            latest_polls[chat_id]['voters'] = [
                voter for voter in poll_data['voters']
                if voter['id'] != user.id
            ]

            # Add the user only if they selected the first option (YES - index 0)
            if 0 in option_ids:
                latest_polls[chat_id]['voters'].append({
                    'id': user.id,
                    'name': full_name,
                    'option_ids': option_ids
                })
                logger.info(f"User {full_name} voted YES in poll {poll_id}, now we have {len(latest_polls[chat_id]['voters'])} voters.")
            break

    if not found:
        logger.warning(f"Could not find poll with ID {poll_id} in registered polls.")

async def randomize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Randomize players into two teams."""
    chat_id = update.effective_chat.id

    # Check if there is a latest poll for this chat
    if chat_id in latest_polls and latest_polls[chat_id]['voters']:
        # Use poll data - only people who voted YES
        poll_voters = latest_polls[chat_id]['voters']

        logger.info(f"Randomizing {len(poll_voters)} voters from poll in chat {chat_id}")

        # Make a copy of the poll voters and shuffle it
        players = poll_voters.copy()
        random.shuffle(players)

        # Split into two teams
        half = len(players) // 2
        team1 = players[:half]
        team2 = players[half:]

        # Generate team lists with full names
        team1_list = "\n".join([f"{i+1}. {player['name']}" for i, player in enumerate(team1)])
        team2_list = "\n".join([f"{i+1}. {player['name']}" for i, player in enumerate(team2)])

        message = f"🏆 Teams have been randomized from people who voted YES 🏆\n\n"
        message += f"⚽️ Team 1 ({len(team1)}):\n{team1_list}\n\n"
        message += f"⚽️ Team 2 ({len(team2)}):\n{team2_list}"

        # Create randomize again button
        keyboard = [[InlineKeyboardButton("Randomize again", callback_data="randomize_again")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(message, reply_markup=reply_markup)
    else:
        # No active poll, ask the user to send a poll
        if chat_id in latest_polls and latest_polls[chat_id].get('poll_id'):
            await update.message.reply_text(
                "There are no votes in the poll yet.\n"
                "You can add participants manually using the /add_voters command name1 name2 ..."
            )
        else:
            await update.message.reply_text(
                "No active poll found.\n"
                "Reply to any previous poll with the /use_poll command to use it for team randomization."
            )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id

    if query.data == "randomize_again":
        # Check if we have poll data
        if chat_id in latest_polls and latest_polls[chat_id]['voters']:
            # Use poll data - only people who voted YES
            poll_voters = latest_polls[chat_id]['voters']

            # Make a copy of the poll voters and shuffle it
            players = poll_voters.copy()
            random.shuffle(players)

            # Split into two teams
            half = len(players) // 2
            team1 = players[:half]
            team2 = players[half:]

            # Generate team lists with full names
            team1_list = "\n".join([f"{i+1}. {player['name']}" for i, player in enumerate(team1)])
            team2_list = "\n".join([f"{i+1}. {player['name']}" for i, player in enumerate(team2)])

            message = f"🏆 Teams have been randomized from people who voted YES 🏆\n\n"
            message += f"⚽️ Team 1 ({len(team1)}):\n{team1_list}\n\n"
            message += f"⚽️ Team 2 ({len(team2)}):\n{team2_list}"

            # Create randomize again button
            keyboard = [[InlineKeyboardButton("Randomize again", callback_data="randomize_again")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await query.edit_message_text("No poll with votes found. Reply to any previous poll with the /use_poll command to use it for team randomization.")

    elif query.data == "manual_randomize_again":
        if chat_id in manual_participants and manual_participants[chat_id]:
            # Make a copy of the player list and shuffle it
            players = manual_participants[chat_id].copy()
            random.shuffle(players)

            # Split into two teams
            half = len(players) // 2
            team1 = players[:half]
            team2 = players[half:]

            # Generate team lists with full names
            team1_list = "\n".join([f"{i+1}. {player['name']}" for i, player in enumerate(team1)])
            team2_list = "\n".join([f"{i+1}. {player['name']}" for i, player in enumerate(team2)])

            message = f"🏆 Teams have been randomized from manually added list 🏆\n\n"
            message += f"⚽️ Team 1 ({len(team1)}):\n{team1_list}\n\n"
            message += f"⚽️ Team 2 ({len(team2)}):\n{team2_list}"

            # Create randomize again button
            keyboard = [[InlineKeyboardButton("Randomize again", callback_data="manual_randomize_again")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await query.edit_message_text("The player list is empty! Add players using the /add command.")

    # Handle menu command buttons
    elif query.data == "cmd_add":
        await query.edit_message_text("Enter the /add command along with a list of players separated by spaces.\nFor example: /add Adam Peter Mark")

    elif query.data == "cmd_randomize_manual":
        # Create a new message instead of editing the old one
        await context.bot.send_message(
            chat_id=chat_id,
            text="Randomizing teams from manually entered list..."
        )
        await randomize_manual(update, context)

    elif query.data == "cmd_randomize":
        # Create a new message instead of editing the old one
        await context.bot.send_message(
            chat_id=chat_id,
            text="Randomizing teams from people who voted YES in the poll..."
        )
        await randomize(update, context)

    elif query.data == "cmd_clear":
        # Create a new message instead of editing the old one
        await context.bot.send_message(
            chat_id=chat_id,
            text="Clearing data..."
        )
        await clear(update, context)

    elif query.data == "cmd_create_poll":
        # Create a new message instead of editing the old one
        await context.bot.send_message(
            chat_id=chat_id,
            text="Creating a new poll..."
        )
        await create_poll(update, context)

    elif query.data == "add_poll_participants":
        await query.edit_message_text(
            "Enter the names of people who voted YES in the poll using the /add_voters command.\n"
            "For example: /add_voters Adam Mark Peter"
        )

    elif query.data == "use_this_poll":
        # Redirect to "replying" to this poll with /use_poll
        await query.edit_message_text(
            "To use this poll, reply to it directly using the /use_poll command"
        )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear both poll data and manual player list."""
    chat_id = update.effective_chat.id

    both_empty = True

    if chat_id in latest_polls:
        latest_polls[chat_id] = {'poll_id': None, 'voters': []}
        both_empty = False

    if chat_id in manual_participants and manual_participants[chat_id]:
        manual_participants[chat_id] = []
        both_empty = False

    if both_empty:
        await update.message.reply_text("No data to clear!")
    else:
        await update.message.reply_text("All data has been cleared!")

def main() -> None:
    """Start the bot."""
    # Replace with your bot token received from @BotFather
    token = "YOUR_BOT_TOKEN_HERE"

    # Create the Application
    application = ApplicationBuilder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("randomize_manual", randomize_manual))
    application.add_handler(CommandHandler("randomize", randomize))
    application.add_handler(CommandHandler("use_poll", use_poll))
    application.add_handler(CommandHandler("add_voters", add_voters))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("create_poll", create_poll))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Add poll handlers
    application.add_handler(MessageHandler(filters.POLL, process_poll))
    application.add_handler(PollAnswerHandler(process_poll_answer))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()