# Dockerized Telegram Proxy Scraper and Notifier Bot

This project provides a Python-based bot that monitors public Telegram channels, scrapes proxy links (MTProto, VLESS, VMess, Shadowsocks), and sends them to recipients via both email (with attachments) and a designated Telegram group.

The application is fully containerized with Docker and designed for stateless deployment on platforms like RunonFlux.

## Features

- **Telegram Client API**: Uses `Telethon` to read all messages from public channels.
- **Robust Link Extraction**: Finds multiple proxy types in plain text and hidden hyperlinks.
- **Dual Notification Channels**:
    - **Email**: Sends an email with a Persian introduction and categorized links attached as `.txt` files.
    - **Telegram Group**: Sends formatted, chunked messages with categorized links to a specific group or channel.
- **Dynamic Configuration**: All settings are managed via environment variables.
- **Persistent State**: Remembers the last processed message per channel to prevent duplicates.

## Setup

### Getting Telegram API Credentials
1.  Log in to your Telegram account at [my.telegram.org](https://my.telegram.org).
2.  Go to "API development tools" and create a new application to get your `api_id` and `api_hash`.

### How to Find a `TARGET_TELEGRAM_CHAT_ID`
1. Add a bot like `@userinfobot` to your target group.
2. Type `/start` in the group.
3. The bot will reply with the group's ID (it will be a large negative number).
4. Remove the bot after you have the ID.

## Configuration

The application is configured via environment variables. Create a `.env` file from the example provided, and place your recipient email addresses in `emails.txt`.

## Running Locally with Docker

1.  **Build the Docker Image**:
    ```bash
    docker build -t telegram-proxy-scraper .
    ```

2.  **Run the Docker Container**:
    ```bash
    docker run -d \
      --name proxy-scraper-bot \
      -v "$(pwd)/data:/app/data" \
      --env-file .env \
      telegram-proxy-scraper
    ```
    - The `-v "$(pwd)/data:/app/data"` command mounts a local directory for persistent storage of your session file and message state.

3.  **Check Logs**:
    ```bash
    docker logs -f proxy-scraper-bot
    ```