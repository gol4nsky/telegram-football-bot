# Telegram Football Team Randomizer Bot

A Telegram bot that helps organize football games by creating random teams from a list of players or poll responses.

## Features

- **Two Ways to Create Teams**:
  - From a manual list of players
  - From poll responses (who's playing?)
  
- **Smart Team Balancing**:
  - Automatically splits players into balanced teams
  - One-click re-randomization
  
- **User-Friendly Interface**:
  - Button-based menu for easy navigation
  - Simple commands for quick operation
  
- **Poll Management**:
  - Create polls directly from the bot
  - Use existing polls in chat
  - Track poll responses in real-time

## Commands

- `/start` - Display welcome message and available commands
- `/add name1 name2 name3...` - Add players manually, separating names with spaces
- `/randomize_manual` - Randomize teams from manually added players
- `/create_poll` - Create a poll that will be tracked by the bot
- `/randomize` - Randomize teams from people who voted YES in the poll
- `/use_poll` - Use as a reply to a poll to select it for randomization
- `/add_voters name1 name2...` - Add participants to the selected poll
- `/clear` - Clear player and poll data

## Setup and Installation

### Prerequisites

- Python 3.7 or higher
- python-telegram-bot library (version 20.0 or higher)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/gol4nsky/telegram-football-bot.git
   cd telegram-football-bot
   ```

2. Install required packages:
   ```bash
   pip install python-telegram-bot
   ```

3. Create a bot on Telegram:
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Use the `/newbot` command and follow the steps
   - Copy your bot token

4. Update the token in the code:
   ```python
   # Replace with your bot token received from @BotFather
   token = "YOUR_BOT_TOKEN_HERE"
   ```

5. Run the bot:
   ```bash
   python telegram-football-bot.py
   ```

## Usage Examples

### Creating Teams Manually

1. Add players:
   ```
   /add John Mike Sarah Alex Emma Chris
   ```

2. Generate random teams:
   ```
   /randomize_manual
   ```

3. Regenerate teams if needed by clicking the "Randomize again" button.

### Creating Teams from a Poll

1. Create a poll:
   ```
   /create_poll
   ```

2. Wait for people to vote or add voters manually:
   ```
   /add_voters John Mike Sarah
   ```

3. Generate random teams:
   ```
   /randomize
   ```

## Deployment

For 24/7 availability, you can deploy the bot to:

- **Heroku**: Use the provided Procfile
- **VPS/Cloud Server**: Run with systemd or screen
- **PythonAnywhere**: Follow their Telegram bot hosting guide

## Customization

You can easily customize the bot:
- Edit poll questions
- Change team emojis and formatting
- Add additional randomization logic

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
