# Dockerized Telegram Proxy Scraper and Email Notifier Bot

This project provides a Python-based bot that monitors public Telegram channels, scrapes proxy links (MTProto, VLESS, VMess), and sends them to a list of recipients via email. The application is fully containerized with Docker and designed for stateless deployment on platforms like RunonFlux.

## Features

- **Telegram Client API**: Uses `Telethon` to read messages from public channels like a real user.
- **Dynamic Configuration**: All settings are managed via environment variables.
- **Persistent State**: Remembers the last processed message to avoid duplicates on restart.
- **Robust Link Extraction**: Uses regex to find MTProto, VLESS, and VMess links in both plain text and hyperlinks.
- **Email Notifications**: Sends neatly formatted HTML emails with categorized links.
- **Dockerized**: Easy to build, run, and deploy.
- **Stateless Design**: Optimized for cloud platforms like RunonFlux, relying on mounted volumes for state.

## 1. Setup

### Getting Telegram API Credentials

The bot requires `api_id` and `api_hash` from a Telegram user account.

1.  Log in to your Telegram account at [my.telegram.org](https://my.telegram.org).
2.  Go to the "API development tools" section.
3.  Fill out the form to create a new application (you can use any name, e.g., "Proxy Scraper").
4.  You will receive your `api_id` and `api_hash`. **Keep these secure.**

### Configuration

The application is configured entirely through environment variables.

1.  **Create a `.env` file**: Copy the `.env.example` file to a new file named `.env`.

    ```bash
    cp .env.example .env
    ```

2.  **Edit `.env`**: Fill in the values for your Telegram API credentials, the target channels, and your SMTP server details.

    ```ini
    # .env
    API_ID=1234567
    API_HASH=your_api_hash
    TELEGRAM_CHANNELS=@channel1,[https://t.me/channel2](https://t.me/channel2)
    PERSISTENT_STORAGE_PATH=./data
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USERNAME=your_email@gmail.com
    SMTP_PASSWORD=your_google_app_password # IMPORTANT: Use an App Password if using Gmail with 2FA
    RUN_INTERVAL_SECONDS=3600
    ```

3.  **Edit `emails.txt`**: Add the recipient email addresses, one per line.

## 2. Running Locally with Docker

These steps assume you have Docker installed and running.

1.  **Build the Docker Image**:
    Open a terminal in the project's root directory and run:

    ```bash
    docker build -t telegram-proxy-scraper .
    ```

2.  **Run the Docker Container**:
    This command runs the container in detached mode (`-d`), mounts a local `./data` directory for persistent storage (`-v`), and passes the environment variables from your `.env` file.

    ```bash
    docker run -d \
      --name proxy-scraper-bot \
      -v "$(pwd)/data:/app/data" \
      --env-file .env \
      telegram-proxy-scraper
    ```

    - `--name proxy-scraper-bot`: Assigns a convenient name to the container.
    - `-v "$(pwd)/data:/app/data"`: Mounts the local `data` directory into the container's `/app/data` directory. This is where the `bot.session` and `last_message_ids.json` files will be stored, ensuring they persist across container restarts.

3.  **Check Logs**:
    To see the bot's output and monitor its activity:

    ```bash
    docker logs -f proxy-scraper-bot
    ```

4.  **Stop the Container**:

    ```bash
    docker stop proxy-scraper-bot
    ```

## 3. Deployment Notes (RunonFlux)

This application is designed to be compatible with platforms like RunonFlux.

-   **Configuration**: When deploying, you will need to input all the environment variables (from your `.env` file) into the Flux platform's configuration interface for your application. **Do not** commit your `.env` file with secrets to a public repository.
-   **Persistent Storage**: Flux provides a mechanism for persistent storage. You must configure a persistent volume and mount it to the path specified by the `PERSISTENT_STORAGE_PATH` environment variable (which defaults to `/app/data` inside the container). This is critical for the bot to remember its state.
-   **Statelessness**: The container itself is stateless. All state (Telegram session and message IDs) is written to the mounted volume, allowing the container to be stopped, restarted, or migrated without losing its place.