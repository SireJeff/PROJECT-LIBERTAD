import os
import re
import json
import smtplib
import logging
import asyncio
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
from dotenv import load_dotenv

# --- Configuration & Setup ---
load_dotenv()

# Set up structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Telegram Client Configuration
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
CHANNELS_INPUT = os.getenv('TELEGRAM_CHANNELS', '').split(',')
CHANNELS = [c.strip() for c in CHANNELS_INPUT if c.strip()]

# Persistent Storage Configuration
STORAGE_PATH = os.getenv('PERSISTENT_STORAGE_PATH', './data')
SESSION_FILE = os.path.join(STORAGE_PATH, 'bot.session')
STATE_FILE = os.path.join(STORAGE_PATH, 'last_message_ids.json')

# Email Configuration
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USERNAME')
SMTP_PASS = os.getenv('SMTP_PASSWORD')
EMAIL_RECIPIENTS_FILE = 'emails.txt'

# Bot Settings
RUN_INTERVAL = int(os.getenv('RUN_INTERVAL_SECONDS', 3600))

# Regular Expressions for Proxy Links
REGEX_PATTERNS = {
    "MTPROTO": r"https?://t\.me/proxy\?[^\s]+",
    "VLESS": r"vless://[^\s]+",
    "VMESS": r"vmess://[^\s]+"
}

# --- State Management ---

def load_state():
    """Loads the last processed message IDs from the state file."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error loading state file: {e}")
        return {}

def save_state(state):
    """Saves the current state to the state file."""
    try:
        os.makedirs(STORAGE_PATH, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except IOError as e:
        logging.error(f"Error saving state file: {e}")

# --- Link Extraction and Parsing ---

def extract_links(message):
    """Extracts proxy links from a message's text and entities."""
    extracted_links = set()
    text = message.text or ""

    # 1. Extract from plain text
    for protocol, pattern in REGEX_PATTERNS.items():
        found = re.findall(pattern, text, re.IGNORECASE)
        extracted_links.update(found)

    # 2. Extract from message entities (hyperlinks)
    if message.entities:
        for entity in message.entities:
            if isinstance(entity, (MessageEntityTextUrl, MessageEntityUrl)):
                url = entity.url if isinstance(entity, MessageEntityTextUrl) else text[entity.offset:entity.offset+entity.length]
                for protocol, pattern in REGEX_PATTERNS.items():
                    if re.match(pattern, url, re.IGNORECASE):
                        extracted_links.add(url)
                        break
    return list(extracted_links)

# --- Email Distribution ---

def get_email_recipients():
    """Reads recipient email addresses from the specified file."""
    if not os.path.exists(EMAIL_RECIPIENTS_FILE):
        logging.warning(f"Recipients file not found: {EMAIL_RECIPIENTS_FILE}")
        return []
    try:
        with open(EMAIL_RECIPIENTS_FILE, 'r') as f:
            return [line.strip() for line in f if line.strip() and '@' in line]
    except IOError as e:
        logging.error(f"Could not read recipients file: {e}")
        return []

def send_email(categorized_links):
    """Sends an email with the categorized proxy links."""
    recipients = get_email_recipients()
    if not recipients:
        logging.warning("No recipients found, skipping email.")
        return

    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS]):
        logging.error("SMTP environment variables are not fully configured. Cannot send email.")
        return

    # Format email content
    subject = f"New Proxy Links Found - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    html_body = "<html><body>"
    html_body += "<h2>New Proxy Links Found</h2>"
    html_body += "<p>The following new proxy links have been collected:</p>"

    for category, links in categorized_links.items():
        if links:
            html_body += f"<h3>{category.upper()} Proxies ({len(links)})</h3>"
            html_body += "<ul>"
            for link in links:
                html_body += f'<li><a href="{link}">{link}</a></li>'
            html_body += "</ul>"
    html_body += "</body></html>"

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, recipients, msg.as_string())
            logging.info(f"Email successfully sent to {len(recipients)} recipients.")
    except smtplib.SMTPException as e:
        logging.error(f"Failed to send email: {e}")

# --- Main Bot Logic ---

async def main_task():
    """The main coroutine that connects, scrapes, and notifies."""
    if not all([API_ID, API_HASH]):
        logging.critical("API_ID and API_HASH must be set in environment variables.")
        return
        
    if not CHANNELS:
        logging.critical("TELEGRAM_CHANNELS environment variable is empty or not set.")
        return

    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

    try:
        await client.start()
        logging.info("Telegram client started successfully.")
    except Exception as e:
        logging.critical(f"Failed to start Telegram client: {e}")
        return

    while True:
        logging.info("Starting new scrape cycle...")
        state = load_state()
        all_new_links = {protocol: set() for protocol in REGEX_PATTERNS}
        
        for channel_name in CHANNELS:
            try:
                channel_entity = await client.get_entity(channel_name)
                channel_id = str(channel_entity.id)
                last_message_id = state.get(channel_id, 0)
                
                logging.info(f"Checking channel '{channel_name}' for messages since ID {last_message_id}...")
                
                new_messages_found = False
                async for message in client.iter_messages(channel_entity, min_id=last_message_id, reverse=True):
                    links = extract_links(message)
                    if links:
                        new_messages_found = True
                        for link in links:
                            for protocol, pattern in REGEX_PATTERNS.items():
                                if re.match(pattern, link, re.IGNORECASE):
                                    all_new_links[protocol].add(link)
                                    break
                    
                    # Update state with the newest message ID from this channel
                    if message.id > last_message_id:
                        state[channel_id] = message.id
                
                if not new_messages_found:
                    logging.info(f"No new messages with links found in '{channel_name}'.")

            except Exception as e:
                logging.error(f"Error processing channel {channel_name}: {e}")

        # Finalize and send email if new links were found
        categorized_links = {protocol: sorted(list(links)) for protocol, links in all_new_links.items()}
        total_new_links = sum(len(links) for links in categorized_links.values())

        if total_new_links > 0:
            logging.info(f"Found a total of {total_new_links} new unique links.")
            send_email(categorized_links)
        else:
            logging.info("No new links found in this cycle. No email will be sent.")

        # Persist the latest state
        save_state(state)
        logging.info(f"Scrape cycle finished. Waiting for {RUN_INTERVAL} seconds...")
        await asyncio.sleep(RUN_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(main_task())
    except KeyboardInterrupt:
        logging.info("Bot stopped manually.")