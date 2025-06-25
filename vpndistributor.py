import asyncio
import os
import pandas as pd
import logging
import time
import socks
from telethon import TelegramClient
from telethon.tl.types import InputPeerUser
# Import the specific error for handling flood waits
from telethon.errors.rpcerrorlist import PeerFloodError, UserIsBlockedError, FloodWaitError

# --- 1. CONFIGURATION (تنظیمات) ---
# Your personal account credentials
API_ID = 2
API_HASH ='' 

# The ID of the group to get members from
TARGET_GROUP_ID = -1002730500541

# Proxy settings (since you are in Iran)
PROXY_DETAILS = {
    'proxy_type': socks.SOCKS5,
    'addr': '127.0.0.1',
    'port': 1080, # Make sure this is your SOCKS port
}

# File paths
EXCEL_FILE_PATH = 'sshs.xlsx'
SENT_USERS_FILE = 'sent_users.txt'

# SSH Config constants
SSH_PORT = 38742
UDG_PORT = 37300

# Delay between sending messages to different users to avoid spam flags
DELAY_BETWEEN_USERS = 120  # 20 seconds is a safe delay

# --- 2. LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- 3. HELPER FUNCTIONS ---
def load_sent_users():
    """Loads a set of user IDs that have already received credentials."""
    if not os.path.exists(SENT_USERS_FILE):
        return set()
    with open(SENT_USERS_FILE, 'r') as f:
        return {int(line.strip()) for line in f if line.strip()}

def add_sent_user(user_id):
    """Appends a new user ID to the sent users file."""
    with open(SENT_USERS_FILE, 'a') as f:
        f.write(f"{user_id}\n")


# --- 4. CORE DISTRIBUTION LOGIC ---
async def main():
    """Main script to connect, get members, and distribute credentials."""
    
    client = TelegramClient(
        'distributor_session', 
        API_ID, 
        API_HASH, 
        proxy=PROXY_DETAILS
    )
    
    print("Connecting to Telegram with your account...")
    await client.start()
    print("Connection successful.")

    try:
        df = pd.read_excel(EXCEL_FILE_PATH)
        df.columns = df.columns.str.strip()
        logger.info(f"Successfully loaded {EXCEL_FILE_PATH}.")
        
        required_columns = {'USER Names', 'password', 'hostname', 'taken'}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            logger.critical(f"CRITICAL ERROR: Excel file is missing columns: {missing}")
            return
            
    except FileNotFoundError:
        logger.critical(f"CRITICAL ERROR: The file '{EXCEL_FILE_PATH}' was not found.")
        return

    sent_users = load_sent_users()
    logger.info(f"Loaded {len(sent_users)} users who have already received credentials.")

    print(f"Fetching members from group ID {TARGET_GROUP_ID}...")
    try:
        all_participants = await client.get_participants(TARGET_GROUP_ID)
    except Exception as e:
        logger.critical(f"Could not fetch group members. Error: {e}")
        return
    
    print(f"Found {len(all_participants)} total members. Starting distribution...")

    for user in all_participants:
        if user.bot or user.id in sent_users:
            continue
            
        available_creds = df[df['taken'] == False]
        if available_creds.empty:
            logger.warning("No more available credentials left. Stopping.")
            break
            
        row = available_creds.iloc[0]
        row_index = row.name
        
        username = row['USER Names']
        password = row['password']
        hostname = row['hostname']
        
        # --- Format the messages (RESTORED TO FULL DETAIL) ---
        intro_message = """
سلام نازنین،

پیام های زیر حاوی یک اتصال اختصاصی دو کاربر برای دور زدن محدودیت های اینترنتی هست که به صورت اختصاصی برای اعضای خانواده فیزیک دانشگاه شریف فراهم شده. اون ها رو بخون و استفاده کن.

تمام راهنمایی های لازمه داده شده ولی اگر باز هم جایی سوال بود حتما بپرس.

آها یه چیزی!
از هم دیگه دست بگیریم و به هم کمک کنیم.
"""

        credential_message = f"""
🎉 **کانفیگ اختصاصی شما آماده شد!**

*📱 NapsternetV (iOS & Android)*
`ssh://{username}:{password}@{hostname}:{SSH_PORT}#{username}`

---
*💻 NetMod (Windows)*
`ssh://{username}:{password}@{hostname}:{SSH_PORT}/#{username}`

---
*📋 مشخصات برای تنظیم دستی:*
**Remark**: `{username}`
**SSH Host**: `{hostname}`
**Username**: `{username}`
**Password**: `{password}`
**Port**: `{SSH_PORT}`
**udgpw port**: `{UDG_PORT}`

_روی کانفیگ‌های بالا کلیک کنید تا به صورت خودکار کپی شوند._
"""

        ios_caption = """
*راهنمای اتصال در آیفون (iOS) با NapsternetV*

۱. برنامه را از اپ استور نصب کنید.
۲. کانفیگ کپی شده را در برنامه وارد کنید (معمولاً با زدن دکمه + و انتخاب Import from clipboard).
۳. به کانفیگ اضافه شده متصل شوید.

[لینک دانلود از اپ استور](https://apps.apple.com/us/app/napsternetv/id1629465476)
"""
        ios_images = ["ios/napster.jpg"]

        android_caption = """
*راهنمای اتصال در اندروید با NapsternetV*

۱. برنامه را از گوگل پلی یا لینک مستقیم نصب کنید.
۲. کانفیگ کپی شده را در برنامه وارد کنید.
۳. به کانفیگ اضافه شده متصل شوید.

[دانلود از گوگل پلی](https://play.google.com/store/apps/details?id=com.napsternetlabs.napsternetv)
"""
        android_images = ["android/a1.jpg", "android/a2.jpg", "android/a3.jpg", "android/a4.jpg", "android/a5.jpg", "android/a6.jpg", "android/a7.jpg"]
        
        # --- Retry loop for sending messages ---
        while True: # Loop to retry sending to the same user if a flood wait occurs
            try:
                print(f"\nAttempting to send credentials to user: {user.first_name} (ID: {user.id})")
                
                await client.send_message(user.id, intro_message)
                await asyncio.sleep(2)
                
                await client.send_message(user.id, credential_message, parse_mode='md')
                await asyncio.sleep(2)
                
                await client.send_file(user.id, ios_images, caption=ios_caption, parse_mode='md')
                await asyncio.sleep(2)

                await client.send_file(user.id, android_images, caption=android_caption, parse_mode='md')
                
                # If all sends are successful, update state and break the retry loop
                df.at[row_index, 'taken'] = True
                df.to_excel(EXCEL_FILE_PATH, index=False)
                add_sent_user(user.id)
                sent_users.add(user.id)
                
                logger.info(f"SUCCESS: Credentials sent to {user.first_name} (ID: {user.id})")
                break # Exit the retry loop and move to the next user

            except FloodWaitError as e:
                # This is the specific error for "A wait of X seconds is required"
                wait_time = e.seconds + 5 # Add a 5-second buffer to be safe
                logger.warning(f"Flood wait triggered. Pausing for {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                # After sleeping, the while loop will automatically retry for the same user
            
            except (UserIsBlockedError, PeerFloodError) as e:
                logger.error(f"FAILED to send to {user.first_name}: {e}. Skipping user.")
                break # Exit the retry loop and move to the next user (skip this one)

            except Exception as e:
                logger.error(f"An unexpected error occurred for {user.first_name}: {e}. Skipping user.")
                break # Exit the retry loop and move on

        # Wait before processing the next user to avoid spam flags
        print(f"Waiting for {DELAY_BETWEEN_USERS} seconds before next user...")
        await asyncio.sleep(DELAY_BETWEEN_USERS)

    print("\nDistribution script finished.")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
