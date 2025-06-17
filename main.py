import os
import re
import json
import smtplib
import logging
import asyncio
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from telethon import TelegramClient
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
from dotenv import load_dotenv

# --- Configuration & Setup ---
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Telegram Configuration
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
CHANNELS_INPUT = os.getenv('TELEGRAM_CHANNELS', '').split(',')
CHANNELS = [c.strip() for c in CHANNELS_INPUT if c.strip()]
TARGET_CHAT_ID = int(os.getenv('TARGET_TELEGRAM_CHAT_ID', '0'))

# Email Configuration
MAIL_HOST = os.getenv('MAIL_HOST')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
MAIL_USER = os.getenv('MAIL_USER')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
MAIL_FROM_ADDRESS = os.getenv('MAIL_FROM_ADDRESS')
EMAIL_RECIPIENTS_FILE = 'emails.txt'
GUIDE_PDF_FILE = 'در صورت وقوع بحران یا جنگ.pdf'

# Bot & Storage Configuration
STORAGE_PATH = os.getenv('PERSISTENT_STORAGE_PATH', './data')
SESSION_FILE = os.path.join(STORAGE_PATH, 'bot.session')
STATE_FILE = os.path.join(STORAGE_PATH, 'last_message_ids.json')
RUN_INTERVAL = int(os.getenv('RUN_INTERVAL_SECONDS', 28800))

# Regular Expressions for Link Extraction
REGEX_PATTERNS = {
    "MTPROTO": r"https?://t\.me/proxy\?[^\s]+",
    "VLESS": r"vless://[^\s]+",
    "VMESS": r"vmess://[^\s]+",
    "SHADOWSOCKS": r"ss://[^\s]+"
}


def load_state():
    if not os.path.exists(STATE_FILE): return {}
    try:
        with open(STATE_FILE, 'r') as f: return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error loading state file: {e}"); return {}

def save_state(state):
    try:
        os.makedirs(STORAGE_PATH, exist_ok=True)
        with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=4)
    except IOError as e:
        logging.error(f"Error saving state file: {e}")

def get_email_recipients():
    if not os.path.exists(EMAIL_RECIPIENTS_FILE): return []
    try:
        with open(EMAIL_RECIPIENTS_FILE, 'r') as f:
            return [line.strip() for line in f if line.strip() and '@' in line]
    except IOError as e:
        logging.error(f"Could not read recipients file: {e}"); return []


def send_email(categorized_links, total_links_found):
    """Sends an email with an updated, more urgent message and attachments."""
    recipients = get_email_recipients()
    if not recipients:
        logging.warning("No email recipients found, skipping email."); return

    logging.info("Preparing to send email with attachments...")
    
    # --- NEW: Updated subject and email body for a more critical situation ---
    subject = "اطلاعات حیاتی برای شرایط اضطراری و لیست‌های اتصال"
    
    html_body = """
    <html><head><meta charset="UTF-8"></head>
    <body style='font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.7;'>
        <div style="direction: rtl; text-align: right; padding: 20px; border: 1px solid #eee; border-radius: 8px; background-color: #f9f9f9;">
            <div style="padding: 15px; border: 2px solid #d9534f; border-radius: 8px; background-color: #fdf7f7; margin-bottom: 20px;">
                <h2 style="color: #c9302c; margin-top: 0;">یک توصیه‌ی بسیار مهم</h2>
                <p>دوستان، بر اساس شنیده‌ها که امیدواریم هرگز درست نباشه، ظاهراً تصمیماتی برای قطع کامل اینترنت خارجی گرفته شده. لطفاً این موضوع رو جدی بگیرید.</p>
                <p><strong>از الان به فکر دانلود ابزارهای ارتباطی P2P (نقطه به نقطه) و ذخیره‌سازی آموزش‌های زمان جنگ و اورژانسی باشید.</strong></p>
                <p>فایل راهنمای پیوست شده می‌تونه کمک‌کننده باشه. لطفاً اون رو دانلود و ذخیره کنید و برای دیگران هم بفرستید.</p>
            </div>
            
            <p>در این شرایط، تنها کاری که از دست ما برمیاد اینه که هوای همدیگه رو داشته باشیم و به هم برای حفظ آرامش و دسترسی به اطلاعات کمک کنیم. این ایمیل هم در همین راستا ارسال می‌شه.</p>
            <p>امیدوارم در امنیت و سلامت باشید. ❤️</p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="font-size: 0.9em; color: #777;">لیست‌های پروکسی به صورت فایل‌های متنی (.txt) و راهنمای شرایط اضطراری به صورت PDF پیوست شده‌اند.</p>
        </div>
    </body></html>
    """
    
    attachments = []
    today_str = datetime.now().strftime('%Y-%m-%d')
    for protocol, links in categorized_links.items():
        if not links: continue
        file_content = "\n".join(links)
        attachment = MIMEApplication(file_content.encode('utf-8'), _subtype='txt')
        filename = f"{protocol.upper()}_Proxies_{today_str}.txt"
        attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        attachments.append(attachment)

    pdf_attachment = None
    if os.path.exists(GUIDE_PDF_FILE):
        try:
            with open(GUIDE_PDF_FILE, 'rb') as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename="راهنمای_شرایط_اضطراری.pdf")
        except Exception as e:
            logging.error(f"Could not read or attach PDF file: {e}")
    else:
        logging.warning(f"Guide PDF file not found at '{GUIDE_PDF_FILE}'. Skipping attachment.")

    max_retries = 300
    sent_to = set()

    for attempt in range(max_retries):
        remaining_recipients = [r for r in recipients if r not in sent_to]
        if not remaining_recipients:
            logging.info("All emails sent successfully.")
            return

        try:
            with smtplib.SMTP(MAIL_HOST, MAIL_PORT, timeout=90) as server:
                server.starttls()
                server.login(MAIL_USER, MAIL_PASSWORD)
                
                for recipient in remaining_recipients:
                    msg = MIMEMultipart()
                    msg['From'] = MAIL_FROM_ADDRESS
                    msg['To'] = recipient
                    msg['Subject'] = subject
                    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
                    
                    for att in attachments:
                        msg.attach(att)
                    if pdf_attachment:
                        msg.attach(pdf_attachment)
                    
                    server.send_message(msg)
                    logging.info(f"Email successfully sent to {recipient}")
                    sent_to.add(recipient)
            
            logging.info("All emails sent successfully.")
            return

        except Exception as e:
            logging.error(f"Email send attempt {attempt + 1}/{max_retries} failed. Reason: {e}")
            if attempt < max_retries - 1:
                logging.info("Waiting for 30 seconds before retrying remaining emails...")
                time.sleep(30)
            else:
                logging.critical("All email send attempts have failed.")


def extract_links(message):
    extracted_links = set()
    text = message.text or ""
    for pattern in REGEX_PATTERNS.values():
        extracted_links.update(re.findall(pattern, text, re.IGNORECASE))
    if message.entities:
        for entity in message.entities:
            if isinstance(entity, (MessageEntityTextUrl, MessageEntityUrl)):
                url = entity.url if isinstance(entity, MessageEntityTextUrl) else text[entity.offset:entity.offset+entity.length]
                for pattern in REGEX_PATTERNS.values():
                    if re.match(pattern, url, re.IGNORECASE):
                        extracted_links.add(url); break
    return list(extracted_links)

async def send_results_to_telegram_group(client, categorized_links, total_links_found):
    if not TARGET_CHAT_ID:
        logging.info("TARGET_TELEGRAM_CHAT_ID not set, skipping sending to group.")
        return

    logging.info(f"Sending results to Telegram group ID: {TARGET_CHAT_ID}")
    try:
        summary_message = f"✅ **گزارش جدید پروکسی** | **{total_links_found}** لینک جدید"
        await client.send_message(TARGET_CHAT_ID, summary_message, parse_mode='md')
        await asyncio.sleep(1)

        MAX_MESSAGE_LENGTH = 4000
        for protocol, links in categorized_links.items():
            if not links: continue
            chunks, current_chunk, link_counter = [], "", 1
            for link in links:
                link_line = f"[proxy{link_counter}]({link})  " if protocol == "MTPROTO" else f"`{link}`\n"
                if protocol == "MTPROTO": link_counter += 1
                if len(current_chunk) + len(link_line) > MAX_MESSAGE_LENGTH:
                    chunks.append(current_chunk); current_chunk = ""
                current_chunk += link_line
            if current_chunk: chunks.append(current_chunk)

            for i, chunk_content in enumerate(chunks, 1):
                part_header = f"**{protocol.upper()} ({len(links)}) - Part {i}/{len(chunks)}**\n\n"
                await client.send_message(TARGET_CHAT_ID, part_header + chunk_content, parse_mode='md', link_preview=False)
                await asyncio.sleep(1)
        logging.info("Successfully sent all link batches to the Telegram group.")
    except Exception as e:
        logging.error(f"Could not send messages to Telegram group. Reason: {e}")


async def main_task():
    """The main coroutine that connects, scrapes, and notifies."""
    if not all([API_ID, API_HASH, CHANNELS, MAIL_HOST, MAIL_USER, MAIL_PASSWORD, MAIL_FROM_ADDRESS]):
        logging.critical("One or more critical environment variables are missing. Exiting.")
        return

    try:
        os.makedirs(STORAGE_PATH, exist_ok=True)
    except OSError as e:
        logging.critical(f"Could not create storage directory at {STORAGE_PATH}. Error: {e}"); return

    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

    try:
        await client.start()
        logging.info("Telegram client started successfully.")
    except Exception as e:
        logging.critical(f"Failed to start Telegram client: {e}"); return

    while True:
        logging.info("Starting new scrape cycle...")
        state = load_state() 
        all_new_links = {protocol: set() for protocol in REGEX_PATTERNS}
        
        time_offset_hours = RUN_INTERVAL / 3600
        offset_date = datetime.utcnow() - timedelta(hours=time_offset_hours)
        logging.info(f"Fetching all messages from the last {int(time_offset_hours)} hours.")
        
        for channel_name in CHANNELS:
            try:
                channel_entity = await client.get_entity(channel_name)
                channel_id_str = str(channel_entity.id)
                
                async for message in client.iter_messages(channel_entity, offset_date=offset_date, reverse=True):
                    links = extract_links(message)
                    if links:
                        for link in links:
                            for protocol, pattern in REGEX_PATTERNS.items():
                                if re.match(pattern, link, re.IGNORECASE):
                                    all_new_links[protocol].add(link); break
                    state[channel_id_str] = max(state.get(channel_id_str, 0), message.id)
            except Exception as e:
                logging.error(f"Error processing channel {channel_name}: {e}")

        total_new_links = sum(len(links) for links in all_new_links.values())
        if total_new_links > 0:
            logging.info(f"Found a total of {total_new_links} new unique links.")
            categorized_links = {protocol: sorted(list(links)) for protocol, links in all_new_links.items()}
            
            send_email(categorized_links, total_new_links)
            await send_results_to_telegram_group(client, categorized_links, total_new_links)
        else:
            logging.info("No new links found in this cycle.")

        save_state(state)
        logging.info(f"Scrape cycle finished. Waiting for {int(RUN_INTERVAL / 3600)} hours...")
        await asyncio.sleep(RUN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main_task())
