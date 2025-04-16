from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, ContextTypes, CallbackQueryHandler
from motor.motor_asyncio import AsyncIOMotorClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from urllib.parse import quote_plus
from datetime import datetime, timedelta
from html import escape
from pymongo import MongoClient
from telegram.constants import ParseMode
import requests
import logging
import httpx
import html
import base64
import hmac
import hashlib
import time
import aiohttp
import asyncio
import json
import uuid
import pytz
import os
import re


load_dotenv('bot.env') # This loads environment variables from the .env file

# MongoDB configuration
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
encoded_username = quote_plus(str(username))
encoded_password = quote_plus(str(password))

MONGO_URI = f"mongodb+srv://{encoded_username}:{encoded_password}@cluster0.d1k0aur.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = AsyncIOMotorClient(MONGO_URI)
db = client['smilebot']
users_collection = db['user'] # user data
order_collection = db['order'] # order data for mlbb

SMILE_ONE_BASE_URL_BR: Final = "https://www.smile.one/br"
SMILE_ONE_BASE_URL_PH: Final = "https://www.smile.one/ph"
SMILE_ONE_BASE_URL_R: Final = "https://www.smile.one/ph"
TOKEN = os.getenv('BOTKEY')
UID = os.getenv('UID')
EMAIL = os.getenv('EMAIL')
KEY = os.getenv('KEY')
DEFAULT_PRODUCT_ID: Final = "213"
admins = [5671920054,1836389511,7135882496 ]

# Debug print to check if environment variables are loading correctly
print(f"DB_USERNAME: {username}")
print(f"DB_PASSWORD: {password}")
print(f"UID: {UID}")
print(f"EMAIL: {EMAIL}")
print(f"KEY: {KEY}")

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
        

############ message part ###############
# Fetch and display user ID
async def getid_command(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    await update.message.reply_text(f"Your Telegram user 🆔 is: {user_id}")

async def start_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Telegram user ID
    username = update.message.from_user.username

    # Check if the user exists in the database
    user = await users_collection.find_one({"user_id": user_id})

    if not user:
        # Show the introduction message with a Register button
        not_registered_message = (
            "<b>WELCOME TO Minhtet Bot</b>\n"
            "<b>WE PROVIDE MLBB  INSTANT DIAMOND RECHARGE</b>\n"
            "<b>why choose MinHtet Bot? 🤔</b>\n\n"
            "<b>👉24x7 Instant delivery 🚚 ✅</b>\n"
            "<b>👉Buy Using UPI💯</b>\n"
            "<b>👉Easy To Use✅</b>\n"
            "<b>👉No Need To Wait For Admin Reply(You Can Buy Yourself Whenever You Want)✅</b>\n"
             "<b>Register Now 👇</b>\n"          
        )

        # Add a Register button
        keyboard = [
            [InlineKeyboardButton("✅ Register", callback_data="register_user")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            not_registered_message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        balance = user.get('balance_br', 0)
        existing_user_message = (
            "<b>HI! DEAR,</b>\n"
            "Your current balances:\n"
            f"1️⃣ Balance : ${balance}\n\n"

            "<b>PLEASE PRESS /help FOR HOW TO USED</b>\n"
        )
        await update.message.reply_text(existing_user_message, parse_mode="HTML")


async def handle_register_user(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query
    user_id = str(query.from_user.id)

    # Check if the user is already registered
    user = await users_collection.find_one({"user_id": user_id})
    if user:
        # User is already registered
        balance = user.get('balance_br', 0)
        existing_user_message = (
            "Hi Dear, You are already registered!\n"
            "Your Current Balance:\n"
            f"1️⃣ Balance : ${balance}\n\n"
            "<b>PLEASE PRESS /help FOR HOW TO USED</b>\n"
        )
        await query.edit_message_text(existing_user_message, parse_mode="HTML")
    else:
        # Register the user
        new_user = {
            "user_id": user_id,
            "balance_br": 0,  # Initialize inr balance
            "date_joined": int(time.time())
        }
        await users_collection.insert_one(new_user)

        # Send a successful registration message
        success_message = (
            "🎉 <b>Registration Successful!</b>\n"
            "You are now registered in our system. Welcome to our services!\n"
            "Your current balances:\n"
            "1️⃣ Balance : $0\n\n"

            "<b>PLEASE PRESS /help FOR HOW TO USED</b>\n"
        )
        await query.edit_message_text(success_message, parse_mode="HTML")        
#########  commands ##########

async def help_command(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    user_id = str(update.message.from_user.id)  # Get the user ID as a string
    
    # Check if the user is registered in the database
    user = await users_collection.find_one({"user_id": user_id})
    
    if not user:
        # If the user is not found in the database
        await update.message.reply_text("You need to register first. Please use /start to register.")
        return
    
    help_message = f"""
<b>HELLO</b> {username} 🤖  

Please Contact admin ☺️
@minhtet4604

<b>COMMAND LIST</b>

/bal - <b>Bot Balance</b>

/his - <b>Orders History</b>

/role - <b>Check Username MLBB</b>

/getid - <b>Account ID</b>

/price - <b>Price List</b>

    """
    try:
        # Log the message for debugging
        logger.info("Sending help message: %s", help_message)
        await update.message.reply_text(help_message, parse_mode='HTML')  # Use HTML parsing
    except Exception as e:
        logger.error("Failed to send help message: %s", e)
        await update.message.reply_text("An error occurred while sending the help message.")


async def price_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    # Check if the user is registered in the database
    user = await users_collection.find_one({"user_id": user_id})

    if not user:
        await update.message.reply_text("You need to register first. Please use /start to register.")
        return

    # Now define the price list after registration check
    price_list = """
<b>🇧🇷 Pack List Brazil:</b>

       BONUS PACK 
    - svp: $39.00
    - 55: $39.00
    - 165: $116.90
    - 275: $187.50
    - 565: $385.00
    
      NORMAL PACK
    
    - wp: $76.00
    - wp2: $152.00
    - wp3: $228.00
    - wp4: $304.00
    - wp5: $380.00
    - wp10: $760.00
    - twilight: $402.50
    - 86: $61.50
    - 172: $122.00
    - 257: $177.50
    - 343: $239.00
    - 344: $244.00
    - 429: $299.50
    - 514: $355.00
    - 600: $416.50
    - 706: $480.00
    - 792: $541.50
    - 878: $602.00
    - 963: $657.50
    - 1049: $719.00
    - 1135: $779.50
    - 1220: $835.00
    - 1412: $960.00
    - 1584: $1082.00
    - 1755: $1199.00
    - 2195: $1453.00
    - 2901: $1940.00
    - 3688: $2424.00
    - 4390: $2906.00
    - 5532: $3660.00
    - 9288: $6079.00
    - 11483: $7532.00
    
HOW TO MAKE ORDERS 

/br game_id zone_id pack
e.g. /br 74378349 8357 86

FOR BULK ORDERS
/br game_id zone_id pack game_id zone_id pack..... upto 10      
"""
    await update.message.reply_text(price_list, parse_mode='HTML')
    

async def admin_command(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    
    user_id = update.message.from_user.id
    # Check if the user is an admin
    if user_id not in admins:  # Assuming `admins` is a list of admin user IDs
        await update.message.reply_text("❌Unauthorized Alert🚨")
        return
  
    help_message = f"""
<b>Hello Admin</b> {username} 
<b>You can use below commands :</B>   
    
1️⃣<b>Admin Mode</b>:
 /bal_admin - <b>Check balance</b>
 /user - <b>User List</b>
 /all_his - <b>All Order History</b>
 
2️⃣ <b>Wallet Topup:</b>

Ask to user for telegram_id Press 
/getid

<b>Added</b>
/add_bal 784546863 500
/add_bal telegram_id amount

<b>Deducted</b>
/ded_bal 784546863 500
/ded_bal telegram_id amount
    """ 
    try:
        # Log the message for debugging
        logger.info("Sending help message: %s", help_message)
        await update.message.reply_text(help_message, parse_mode='HTML')  # Use HTML parsing
    except Exception as e:
        logger.error("Failed to send help message: %s", e)
        await update.message.reply_text("An error occurred while sending the help message.")


async def get_balance(user_id: str):
    user = await users_collection.find_one({"user_id": user_id})  # Await the database query
    print(f"Fetching balance for user_id: {user_id}")  # Debugging statement
    if user:
        return {
            'balance_br': user.get('balance_br', 0),  # Return balance_br or 0 if not found
       }
    return None

# Check balance command
async def balance_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Convert user_id to string  

    user = await users_collection.find_one({"user_id": user_id})
    
    if not user:
        # If the user is not found in the database
        await update.message.reply_text("You need to register first. Please use /start to register.")
        return
    
    balances = await get_balance(user_id)  # Await the async get_balance function

    if balances:
        balance = balances.get('balance_br', 0)  # Fetch balance for Brazil

        # Format the response with emojis and Markdown styling
        response_message = (
            f"*MinHtet Bot BALANCE 💰:*\n\n"
            f"🇮🇳 *BALANCE *: `{balance:.2f}` 🪙\n"
        )

        await update.message.reply_text(response_message, parse_mode='Markdown')
    else:
        await update.message.reply_text("User not found. Please register using /start.")

async def update_balance(user_id: str, amount: int):  
    """
    Updates the balance of the specified user.
    """
    user = await users_collection.find_one({"user_id": user_id})
    if user:
        # Ensure the "balance" field exists and defaults to 0 if missing
        current_balance = user.get("balance_br", 0)
        new_balance = current_balance + amount
        
        # Update the balance
        await users_collection.update_one({"user_id": user_id}, {"$set": {"balance_br": new_balance}})
        return new_balance
    return None


async def add_balance_command(update: Update, context: CallbackContext):
    """
    Command to add balance to a user's account and log the transaction.
    """
    admin_user_id = update.message.from_user.id  # Get the user ID of the admin issuing the command

    # Check if the user is an admin
    if admin_user_id not in admins:
        await update.message.reply_text("🚫 *Unauthorized*: You are not allowed to use this command.", parse_mode='Markdown')
        return

    # Expecting two arguments: target_user_id and amount
    if len(context.args) != 2 or not context.args[1].isdigit():
        await update.message.reply_text(
            "*Please do like this*: `/add_bal <user_id> <amount>`",
            parse_mode='Markdown'
        )
        return

    target_user_id = context.args[0]  # The user ID to add balance to
    amount = int(context.args[1])  # The amount to add

    # Check if the target user exists in the database
    target_user = await users_collection.find_one({"user_id": target_user_id})
    if not target_user:
        await update.message.reply_text(f"❌ *User Not Found*: No user with ID `{target_user_id}` found.", parse_mode='Markdown')
        return

    # Add the balance to the target user
    new_balance = await update_balance(target_user_id, amount)
    
    if new_balance is not None:
        # Log the balance addition in the balance history collection
        log_entry = {
            "target_user_id": target_user_id,
            "amount": amount,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")  # Use UTC time
        }
        
        # Success message with formatting
        await update.message.reply_text(
            f"✅ *Success!* Added `{amount}` to *User ID* `{target_user_id}`'s balance.\n\n"
            f"💵 New Balance: `{new_balance}` 🪙",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"❌ *Failed*: Unable to update balance for *User ID* `{target_user_id}`.", parse_mode='Markdown')


async def deduct_balance(user_id: str, amount: int):  
    """
    Deduct balance from a specified user.
    """
    user = await users_collection.find_one({"user_id": user_id})
    if user and user["balance_br"] >= amount:  # Ensure sufficient balance exists
        new_balance = user["balance_br"] - amount
        await users_collection.update_one({"user_id": user_id}, {"$set": {"balance_br": new_balance}})
        return new_balance
    return None  # Return None if insufficient balance or user does not exist

async def deduct_balance_command(update: Update, context: CallbackContext):
    """
    Command to deduct balance from a user's account.
    """
    user_id = str(update.message.from_user.id)  # Get the user ID of the person issuing the command

    # Check if the user is an admin
    if int(user_id) not in admins:
        await update.message.reply_text(
            "🚫 *Unauthorized*: You are not allowed to use this command.",
            parse_mode='Markdown'
        )
        return

    # Expecting two arguments: target_user_id and amount
    if len(context.args) != 2 or not context.args[1].isdigit():
        await update.message.reply_text(
            "*Please do like this*: Example: `/ded_balance <user_id> <amount>`",
            parse_mode='Markdown'
        )
        return

    target_user_id = context.args[0]  # The user ID to deduct balance from
    amount = int(context.args[1])  # The amount to deduct

    # Check if the target user exists in the database
    target_user = await users_collection.find_one({"user_id": target_user_id})
    if not target_user:
        await update.message.reply_text(
            f"❌ *User Not Found*: No user with ID `{target_user_id}` found.",
            parse_mode='Markdown'
        )
        return

    # Deduct the balance from the target user
    new_balance = await deduct_balance(target_user_id, amount)
    
    if new_balance is not None:
        # Success message with formatting
        await update.message.reply_text(
            f"✅ *Success!* Deducted `{amount}` from *User ID* `{target_user_id}`'s balance.\n\n"
            f"💵 New Balance: `{new_balance}` 🪙",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ *Failed*: Insufficient balance or unable to deduct for *User ID* `{target_user_id}`.",
            parse_mode='Markdown'
        )

def split_message(text, max_length=4096):
    """Splits the message into chunks that fit within the Telegram message limit."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

async def get_users_command(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id  # Get the user ID of the person issuing the command

    # Check if the user is an admin
    if user_id not in admins:
        await update.message.reply_text("Unauthorized: You are not allowed to use this command.")
        return

    # Fetch all users from the database
    users_cursor = users_collection.find()  # Fetch all users
    users_list = await users_cursor.to_list(length=None)  # Convert cursor to list

    if not users_list:  # Check if there are no users
        await update.message.reply_text("No users found in the database.")
        return

    # Prepare the response message
    response_summary = "User Details: 📋\n\n"
    for user in users_list:
        user_id = user.get('user_id', 'N/A')
        balance = user.get('balance_br', 0)
        date_joined = datetime.fromtimestamp(user.get('date_joined', 0)).strftime('%Y-%m-%d %H:%M:%S')
        
        """
        # Count total orders created by this user from both collections
        total_orders_collection1 = await orders_collection.count_documents({"sender_user_id": user_id})
        total_orders_collection2 = await order_collection.count_documents({"sender_user_id": user_id})
        total_orders = total_orders_collection1 + total_orders_collection2
        """
        # Enhance the output with clear formatting
        response_summary += (
            f"🆔 USER ID: {user_id}\n"
            f" BALANCE : ${balance:.2f}\n"
            f"📅 DATE JOINED: {date_joined}\n"
            "---------------------------------\n"  # Separator for better readability
        )

    # Split message if it's too long
    messages = split_message(response_summary)

    # Send each chunk of the message
    for msg in messages:
        try:
            await update.message.reply_text(msg)  # Send the message without Markdown
        except Exception as e:
            print(f"Error sending message: {e}")
            await update.message.reply_text("An error occurred while sending the message. Please try again later.")
 
 
def split_message(text, max_length=4096):
    """Splits the message into chunks that fit within the Telegram message limit."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

async def get_user_orders(update: Update, context: CallbackContext):
    sender_user_id = str(update.message.from_user.id)  # Get the Telegram user's ID

    # Query both collections for orders made by this sender
    transactions_cursor = order_collection.find({"sender_user_id": sender_user_id})

    # Convert the cursors to lists asynchronously
    transactions_list = await transactions_cursor.to_list(length=None)

    response_summary = "==== Order History ====\n\n"

    # Process orders from transactions_collection
    for order in transactions_list:
        sender_user_id = order.get('sender_user_id', 'N/A')
        user_id = order.get('player_id', 'N/A')
        zone_id = order.get('zone_id', 'N/A')
        pack = order.get('product_name', 'N/A')
        order_ids = order.get('order_ids', 'N/A')
        date = order.get('date', 'N/A')
        total_cost = order.get('total_cost', 0.0)
        status = order.get('status', 'N/A')

        if isinstance(order_ids, list):
            order_ids = ', '.join(order_ids)
        else:
            order_ids = str(order_ids)

        response_summary += (
            f"🆔 Telegram ID: {sender_user_id}\n"
            f"📍 Game ID: {user_id}\n"
            f"🌍 Zone ID: {zone_id}\n"
            f"💎 Pack: {pack}\n"
            f"🆔 Order ID: {order_ids}\n"
            f"📅 Date: {date}\n"
            f"💵 Rate: $ {float(total_cost):.2f}\n"
            f"🔄 Status: {status}\n\n"
        )

    # Split the message if it's too long for a single reply
    messages = split_message(response_summary)
    for msg in messages:
        await update.message.reply_text(msg, parse_mode='HTML')

async def get_all_orders(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Get the Telegram user's ID

    # Check if the user is an admin
    if int(user_id) not in admins:  # Convert to integer for proper comparison
        logging.info(f"Unauthorized access attempt by user ID: {user_id}")
        await update.message.reply_text("❌ Unauthorized: You are not allowed to use this command.")
        return

    # Fetch all orders from the collection
    try:
        orders_cursor = order_collection.find({})  # Fetch all orders
        orders_list = await orders_cursor.to_list(length=None)  # Convert to a list

        if not orders_list:
            await update.message.reply_text("No orders found in the database.")
            return

        response_summary = "==== All Order Histories ====\n\n"

        # Process each order
        for order in orders_list:
            sender_user_id = order.get('sender_user_id', 'N/A')
            player_id = order.get('player_id', 'N/A')
            zone_id = order.get('zone_id', 'N/A')
            product_name = order.get('product_name', 'N/A')
            order_ids = order.get('order_ids', 'N/A')
            date = order.get('date', 'N/A')
            total_cost = order.get('total_cost', 0.0)
            status = order.get('status', 'N/A')

            if isinstance(order_ids, list):
                order_ids = ', '.join(order_ids)
            else:
                order_ids = str(order_ids)

            response_summary += (
                f"🆔 Sender Telegram ID: {sender_user_id}\n"
                f"🎮 Player ID: {player_id}\n"
                f"🌍 Zone ID: {zone_id}\n"
                f"💎 Product: {product_name}\n"
                f"🆔 Order IDs: {order_ids}\n"
                f"📅 Date: {date}\n"
                f"💵 Total Cost: $ {float(total_cost):.2f}\n"
                f"🔄 Status: {status}\n\n"
            )

        # Split the message if it's too long for Telegram's limit
        messages = split_message(response_summary)
        for msg in messages:
            await update.message.reply_text(msg, parse_mode='HTML')

    except Exception as e:
        logging.error(f"Error retrieving orders: {e}")
        await update.message.reply_text("❌ Failed to retrieve order history. Please try again.")
       

############# smile part ###############

# Function to calculate sign
def calculate_sign(params):
    sorted_params = sorted(params.items())
    query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
    query_string += f"&{KEY}"
    hashed_string = hashlib.md5(hashlib.md5(query_string.encode()).hexdigest().encode()).hexdigest()
    return hashed_string

async def get_role_info(userid: str, zoneid: str, product_id: str = DEFAULT_PRODUCT_ID):
    endpoint = f"{SMILE_ONE_BASE_URL_R}/smilecoin/api/getrole"
    current_time = int(time.time())
    params = {
        'uid': UID,
        'email': EMAIL,
        'userid': userid,
        'zoneid': zoneid,
        'product': 'mobilelegends',
        'productid': product_id,
        'time': current_time
    }
    params['sign'] = calculate_sign(params)

    async with aiohttp.ClientSession() as session:  # Use an async session
        try:
            async with session.post(endpoint, data=params, headers={'Content-Type': 'application/x-www-form-urlencoded'}) as response:
                response.raise_for_status()  # Raise an error for bad responses
                data = await response.json()  # Await the JSON response
                print(data)
                return data if data.get('status') == 200 else None
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching role info: {e}")
            return None


async def role_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Get the user ID as a string
    
    # Check if the user is registered in the database
    user = await users_collection.find_one({"user_id": user_id})
    
    if not user:
        # If the user is not found in the database
        await update.message.reply_text("You need to register first. Please use /start to register.")
        return
    
    args = context.args
    if len(args) != 2:
        await update.message.reply_text('Please enter /role userid zoneid.')
        return
    userid, zoneid = args
    role_info = await get_role_info(userid, zoneid)  # Await this call
    if role_info:
        username = role_info.get('username', 'N/A')  # Check username for special characters
        reply_message = (
            f"<b>=== User Details ===</b>\n"
            f"<b>User name:</b> {username}\n"
            f"<b>ID:</b> {userid}\n"
            f"<b>Server:</b> {zoneid}"
        )
        await update.message.reply_text(reply_message, parse_mode='HTML')  # Use HTML for formatting
    else:
        await update.message.reply_text('Failed to fetch role info. Try again later.')

# Query points for BR region
def get_query_points_br():
    endpoint = f"{SMILE_ONE_BASE_URL_BR}/smilecoin/api/querypoints"
    current_time = int(time.time())
    params = {
        'uid': UID,
        'email': EMAIL,
        'product': 'mobilelegends',
        'time': current_time
    }
    params['sign'] = calculate_sign(params)
    try:
        response = requests.post(endpoint, data=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching points: {e}")
        return None

async def get_query_points_ph():
    endpoint = f"{SMILE_ONE_BASE_URL_PH}/smilecoin/api/querypoints"
    current_time = int(time.time())
    params = {
        'uid': UID,
        'email': EMAIL,
        'product': 'mobilelegends',
        'time': current_time
    }
    params['sign'] = calculate_sign(params)
    try:
        response = requests.post(endpoint, data=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching points: {e}")
        return None


# Command to query points in both BR and PH
async def query_point_command(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # Authorization check
    if user_id not in admins:
        await update.message.reply_text('Unauthorized access.')
        return

    try:
        # Fetch Smile Points and Yok Balance
        response_br = get_query_points_br()
        response_ph = await get_query_points_ph()

        # Extract points
        points_br = response_br.get('smile_points', 'Unavailable') if response_br else 'Unavailable'
        points_ph = response_ph.get('smile_points', 'Unavailable') if response_ph else 'Unavailable'

        # Format response
        response_message = (
            f"<b>ADMIN BALANCE</b>:\n\n"
            f"🪙 <b>1. Smile One BRL</b>: {points_br}\n\n"
        )

        # Send response
        await update.message.reply_text(response_message, parse_mode='HTML')

    except Exception as e:
        logging.error(f"Error in /query_point_command: {e}")
        await update.message.reply_text("An error occurred while fetching balances.")


# order br
product_info = {
    "svp": {"id": "22594", "rate": 39.00},
    "55": {"id": "22590", "rate": 39.00},
    "165": {"id": "22591", "rate": 116.90},
    "275": {"id": "22592", "rate": 187.50},
    "565": {"id": "22593", "rate": 385.00},
    
    "86": {"id": "13", "rate": 61.50},   
    "172": {"id": "23", "rate": 122.00},   
    "257": {"id": "25", "rate": 177.50},   
    "706": {"id": "26", "rate": 480.00},   
    "2195": {"id": "27", "rate": 1453.00},   
    "3688": {"id": "28", "rate": 2424.00},   
    "5532": {"id": "29", "rate": 3660.00},   
    "9288": {"id": "30", "rate": 6079.00},   
    "twilight": {"id": "33", "rate":402.50},   
    "wp": {"id": "16642", "rate": 76.00},    
    "343": {"id": ["13", "25"], "rate": 239.00},   
    "344": {"id": ["23", "23"], "rate": 244.00},    
    "429": {"id": ["23", "25"], "rate": 299.00},   
    "514": {"id": ["25", "25"], "rate": 355.00},   
    "600": {"id": ["25", "25", "13"], "rate": 416.00},    
    "792": {"id": ["26", "13"], "rate": 541.00},    
    "878": {"id": ["26", "23"], "rate": 602.00},   
    "963": {"id": ["26", "25"], "rate": 657.00},   
    "1049": {"id": ["26", "25", "13"], "rate": 719.00},   
    "1135": {"id": ["26", "25", "23"], "rate": 779.00},  
    "1220": {"id": ["26", "25", "25"], "rate": 835.00},   
    "1412": {"id": ["26", "26"], "rate": 960.00},   
    "1584": {"id": ["26", "26", "23"], "rate": 1082.00},   
    "1755": {"id": ["26", "26", "25", "13"], "rate": 1199.00},   
    "2901": {"id": ["27", "26"], "rate": 1940.00},   
    "4390": {"id": ["27", "27"], "rate": 2906.00},   
    "11483": {"id": ["30", "27"], "rate": 7532.00},  
    "wp2": {"id": ["16642", "16642"], "rate": 152.00},   
    "wp3": {"id": ["16642", "16642", "16642"], "rate": 228.00},   
    "wp4": {"id": ["16642", "16642", "16642", "16642"], "rate": 304.00},
    "wp5": {"id": ["16642", "16642","16642", "16642", "16642"], "rate": 380.00},    
    "wp10": {"id": ["16642", "16642","16642", "16642", "16642", "16642", "16642", "16642", "16642", "16642"], "rate": 760.00}, 
}

async def create_order_and_log_br(userid, zoneid, product_id):
    endpoint = f"{SMILE_ONE_BASE_URL_BR}/smilecoin/api/createorder"
    current_time = int(time.time())
    
    params = {
        'uid': UID,
        'email': EMAIL,
        'userid': userid,
        'zoneid': zoneid,
        'product': 'mobilelegends',
        'productid': product_id,
        'time': current_time
    }
    
    params['sign'] = calculate_sign(params)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(endpoint, data=params) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get('status') == 200:
                    return {"order_id": data.get('order_id')}  # Return only the order ID if successful
                else:
                    error_message = data.get('message', 'Unknown error')  # Capture the specific failure reason
                    logger.error(f"Failed to create order: {error_message}")
                    return {"order_id": None, "reason": error_message}  # Return None with reason
        except aiohttp.ClientError as e:
            logger.error(f"Error creating order: {e}")
            return {"order_id": None, "reason": str(e)}  # Capture client error as reason if needed


async def create_order_for_product(user_id, zone_id, pid):
    return await create_order_and_log_br(user_id, zone_id, pid)  # Make sure this is awaited

async def bulk_command_br(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Get the user ID as a string

    # Check if the user is registered in the database
    user = await users_collection.find_one({"user_id": user_id})
    if not user:
        await update.message.reply_text("You need to register first. Please use /start to register.")
        return

    args = context.args

    # Security: Check for multiple commands in one input
    if len(update.message.text.split('/br')) > 2:
        await update.message.reply_text("Multiple /br commands detected in one input. Process aborted for security reasons.")
        return    

    if len(args) < 3:  # Expecting at least one user ID, zone ID, and one product name
        await update.message.reply_text('Please enter /br user_id Zone_id pack. Bulk order /br user_id zone_id pack user_id zone_id pack........ up to 10 max.')
        return

    order_requests = []
    failed_orders = []
    sender_user_id = str(update.message.from_user.id)

    loading_message = await update.message.reply_text(
        "<b>ORDER PROCESSING</b> 🕐",
        parse_mode="HTML"
    )

    # Iterate through the args to extract user ID, zone ID, and product names
    for i in range(0, len(args), 3):
        if i + 2 >= len(args):
            await update.message.reply_text('Invalid input. Make sure to provide user ID, zone ID, and product name for each order.')
            return

        user_id = str(args[i])
        zone_id = str(args[i + 1])
        product_name = args[i + 2].lower()

        # Check if the product name is valid
        product = product_info.get(product_name)
        if not product:
            failed_orders.append(
                f"<b>Game ID</b>: {user_id}\n"
                f"<b>Game Server</b>: {zone_id}\n"
                f"<b>Items</b>: {product_name}\n"
                f"<b>Results</b>: Invalid Product\n\n"
            )
            continue

        # Determine the rate based on user type
        product_rate = product["rate"]
        if product_rate is None:
            failed_orders.append(
                f"<b>Game ID</b>: {user_id}\n"
                f"<b>Game Server</b>: {zone_id}\n"
                f"<b>Items</b>: {product_name}\n"
                f"<b>Results</b>: Product rate not available\n\n"
            )
            continue
        order_requests.append({
            "user_id": user_id,
            "zone_id": zone_id,
            "product_name": product_name,
            "product_rate": product_rate,
            "product_ids": product['id'] if isinstance(product['id'], list) else [product['id']]
        })

    if not order_requests:
        await loading_message.edit_text("No valid orders to process. Please Enter Valid Product Name")
        return    

        # Check if the user has sufficient balance
    current_balance = await get_balance(sender_user_id)
    if current_balance is None:
        print(f"[ERROR] Sender wallet balance not found for User ID: {sender_user_id}")
        await loading_message.edit_text("User wallet not found. Please register using /start.")
        return    
    # Calculate total cost of all valid orders
    total_cost = sum(order['product_rate'] for order in order_requests)        
            
    # Check if the user's balance is sufficient for the total cost
    if current_balance['balance_br'] < total_cost:
        print(f"[ERROR] Insufficient balance for User ID: {sender_user_id}. Required: {total_cost}, Available: {current_balance['balance_br']}")
        await loading_message.edit_text(
            f"Insufficient balance.\nAvailable Balance: {current_balance['balance_br']}\nTotal Cost: {total_cost}"
        )
        return    

    # Process orders
    order_summary = []
    transaction_documents = []
    balance_to_readd = 0  # Track balance to re-add for failed orders
    
    for order in order_requests:
        current_balance = await get_balance(sender_user_id)   
        if current_balance['balance_br'] < order['product_rate']:
            print(f"[ERROR] Insufficient balance during processing for User ID: {sender_user_id}.")
            failed_orders.append(
                f"<b>Game ID:</b> {order['user_id']}\n"
                f"<b>Game Server:</b> {order['zone_id']}\n"
                f"<b>Items:</b> {order['product_name']}\n"
                f"<b>Results:</b> Insufficient Balance\n\n"
            )
            continue
        
        # Deduct balance for the current order
        try:
            new_balance = await deduct_balance1(sender_user_id, order['product_rate'], 'balance_br')
            if new_balance is None:
                raise Exception("Balance deduction failed or insufficient balance.")
            print(f"[DEBUG] Deducted {order['product_rate']} for User ID: {sender_user_id}. New balance: {new_balance}.")
        except Exception as e:
            print(f"[ERROR] Failed to deduct balance: {e}")
            failed_orders.append(
                f"<b>Game ID:</b> {order['user_id']}\n"
                f"<b>Game Server:</b> {order['zone_id']}\n"
                f"<b>Items:</b> {order['product_name']}\n"
                f"<b>Results:</b> Balance Deduction Failed\n\n"
            )
            continue        
        
        # Process the order
        order_ids = []
        try:
            for pid in order['product_ids']:
                result = await create_order_and_log_br(order['user_id'], order['zone_id'], pid)
                order_id = result.get("order_id")
                if not order_id:
                    raise Exception(result.get("reason", "Unknown failure"))
                order_ids.append(order_id)
        except Exception as e:
            print(f"[ERROR] Order processing failed: {e}")
            balance_to_readd += order['product_rate']  # Add back the balance for failed orders
            failed_orders.append(
                f"<b>Game ID:</b> {order['user_id']}\n"
                f"<b>Game Server:</b> {order['zone_id']}\n"
                f"<b>Items:</b> {order['product_name']}\n"
                f"<b>Results:</b> {str(e)}\n\n"
            )
            continue        

        if order_ids:
            role_info = await get_role_info(order['user_id'], order['zone_id'])
            if role_info is None:
                balance_to_readd += order['product_rate']  # Add back the balance for failed user lookup
                failed_orders.append(
                    f"<b>Game ID:</b> {order['user_id']}\n"
                    f"<b>Game Server:</b> {order['zone_id']}\n"
                    f"<b>Items:</b> {order['product_name']}\n"
                    f"<b>Results:</b> User ID not exist\n\n"
                )
                continue

            username = role_info.get('username', 'N/A')
            order_summary.append({
                "order_ids": order_ids,
                "username": username,
                "user_id": order['user_id'],
                "zone_id": order['zone_id'],
                "product_name": order['product_name'],
                "total_cost": order['product_rate'],
            })

            transaction_documents.append({
                "sender_user_id": sender_user_id,
                "user_id": order['user_id'],
                "zone_id": order['zone_id'],
                "username": username,
                "product_name": order['product_name'],
                "order_ids": order_ids,
                "date": datetime.now().strftime('%Y-%m-%d'),
                "total_cost": order['product_rate'],
                "status": "success"
            })

    # Re-add balance for failed orders
    if balance_to_readd > 0:
        await readd_balance(sender_user_id, balance_to_readd, 'balance_br')
        print(f"[DEBUG] Re-added {balance_to_readd} to User ID: {sender_user_id} due to failed orders.")
 
    # Insert all successful transactions
    if transaction_documents:
        await order_collection.insert_many(transaction_documents)

    # Prepare response summary
    response_summary = "===Transaction Report===\n"
    for detail in order_summary:
        order_ids_str = ', '.join(detail["order_ids"])
        response_summary += (
            f"<b>Order Status:</b> SUCCESSFUL✅\n"
            f"<b>Order ID:</b> {order_ids_str}\n"
            f"<b>User Name:</b> {detail['username']}\n"
            f"<b>Game ID:</b> {detail['user_id']}\n"
            f"<b>Game Server:</b> {detail['zone_id']}\n"
            f"<b>Items:</b> {detail['product_name']}💎\n"
            f"<b>Total Amount:</b> ${detail['total_cost']:.2f} 🪙\n\n"
        )

    if failed_orders:
        response_summary += "\n<b>Order Status: FAILED ORDERS🚫</b>:\n"
        response_summary += "\n".join(failed_orders)

    await loading_message.edit_text(response_summary, parse_mode='HTML')
  
async def deduct_balance1(user_id: str, amount: int, balance_type: str):
    """
    Deducts the specified amount from the user's balance safely.

    Args:
        user_id (str): The user's ID.
        amount (int): The amount to deduct.
        balance_type (str): The type of balance to deduct from (e.g., 'balance_ph').

    Returns:
        int: The updated balance after deduction, or None if the operation failed.
    """
    try:
        # Use findOneAndUpdate for atomic operation
        result = await users_collection.find_one_and_update(
            {
                "user_id": user_id,  # Filter by user_id
                balance_type: {"$gte": amount}  # Ensure sufficient balance
            },
            {
                "$inc": {balance_type: -amount}  # Deduct the amount
            },
            return_document=True  # Return the updated document
        )

        if result:
            # Successfully deducted; return the new balance
            new_balance = result[balance_type] - amount
            print(f"[DEBUG] Deduction successful. User ID: {user_id}, New Balance: {new_balance}")
            return new_balance
        else:
            # User not found or insufficient balance
            print(f"[ERROR] Deduction failed. User ID: {user_id}, Balance Type: {balance_type}, Amount: {amount}")
            return None
    except Exception as e:
        # Handle unexpected errors
        print(f"[ERROR] Exception occurred during balance deduction: {e}")
        return None


async def readd_balance(user_id: str, amount: int, balance_type: str):
    """
    Re-adds the specified amount to the user's balance.

    Args:
        user_id (str): The user's ID.
        amount (int): The amount to re-add.
        balance_type (str): The type of balance to adjust (e.g., 'balance_ph').

    Returns:
        int: The updated balance after re-adding, or None if the operation failed.
    """
    try:
        # Use findOneAndUpdate for atomic operation
        result = await users_collection.find_one_and_update(
            {
                "user_id": user_id  # Filter by user_id
            },
            {
                "$inc": {balance_type: amount}  # Re-add the amount
            },
            return_document=True  # Return the updated document
        )

        if result:
            # Successfully re-added; return the new balance
            new_balance = result[balance_type] + amount
            print(f"[DEBUG] Re-added {amount} to User ID: {user_id}, New Balance: {new_balance}")
            return new_balance
        else:
            # User not found
            print(f"[ERROR] Re-addition failed. User ID: {user_id}, Amount: {amount}")
            return None
    except Exception as e:
        # Handle unexpected errors
        print(f"[ERROR] Exception occurred during balance re-addition: {e}")
        return None
  

# Main function to run the bot
if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('getid', getid_command))
    app.add_handler(CommandHandler('bal', balance_command)) # user balance
    app.add_handler(CommandHandler('bal_admin', query_point_command)) # admin balance both smile and mg
    app.add_handler(CommandHandler('admin', admin_command))
    app.add_handler(CommandHandler('price', price_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('role', role_command)) # user name check 
    app.add_handler(CommandHandler('br', bulk_command_br))
    app.add_handler(CommandHandler('add_bal', add_balance_command)) # add balance for user
    app.add_handler(CommandHandler('ded_bal', deduct_balance_command)) # remove balance from user
    app.add_handler(CommandHandler('user', get_users_command)) # admin command user list collect
    app.add_handler(CommandHandler('all_his', get_all_orders))
    app.add_handler(CommandHandler('his', get_user_orders)) # order history
    app.add_handler(CallbackQueryHandler(handle_register_user, pattern="register_user"))
    
    
    print("Bot is running...")
    app.run_polling(poll_interval=3)   