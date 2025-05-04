# Copyright © 2025 Simone Montanari. All Rights Reserved.
# This file is part of HiKingsRome and may not be used or distributed without written permission.

#!/usr/bin/env python3
"""
HikyTheBot - Telegram bot for managing hiking activities
Version 2.0 - SQLite database version
"""

import os
import sys
import time
import atexit
import json
import logging
import sqlite3
import re
import threading
from datetime import datetime, date, timedelta
from datetime import time as datetime_time
from functools import wraps
import pytz
import requests
from dotenv import load_dotenv
from calendar import monthcalendar, month_name

# Telegram imports
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, LabeledPrice
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, Filters, PreCheckoutQueryHandler
)

# Local imports
from utils.db_utils import DBUtils
from utils.db_keyboards import KeyboardBuilder
from utils.rate_limiter import RateLimiter
from utils.weather_utils import WeatherUtils
from utils.db_query_utils import DBQueryUtils,TimeoutError
from utils.markdown_utils import escape_markdown, escape_markdown_v2, escape_preformatted

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.info(f"Using python-telegram-bot version: {telegram.__version__}")

# Define conversation states
(CHOOSING, NAME, EMAIL, PHONE, BIRTH_DATE, MEDICAL, HIKE_CHOICE, EQUIPMENT,
 CAR_SHARE, LOCATION_CHOICE, QUARTIERE_CHOICE, FINAL_LOCATION, CUSTOM_QUARTIERE,
 ELSEWHERE, NOTES, IMPORTANT_NOTES, REMINDER_CHOICE, PRIVACY_CONSENT, 
 ADMIN_MENU, ADMIN_CREATE_HIKE, ADMIN_HIKE_NAME, ADMIN_HIKE_DATE, 
 ADMIN_HIKE_MAX_PARTICIPANTS, ADMIN_HIKE_LOCATION, ADMIN_HIKE_DIFFICULTY,
 ADMIN_HIKE_DESCRIPTION, ADMIN_CONFIRM_HIKE, ADMIN_ADD_ADMIN, DONATION, ADMIN_HIKE_GUIDES,
 PROFILE_MENU, PROFILE_EDIT, PROFILE_NAME, PROFILE_SURNAME, PROFILE_EMAIL,  PROFILE_PHONE, PROFILE_BIRTH_DATE,
 ADMIN_MAINTENANCE, MAINTENANCE_DATE, MAINTENANCE_START_TIME, MAINTENANCE_END_TIME, MAINTENANCE_REASON,
 ADMIN_QUERY_DB, ADMIN_QUERY_EXECUTE, ADMIN_QUERY_SAVE, ADMIN_QUERY_DELETE, ADMIN_QUERY_NAME, 
 ADMIN_COSTS, COST_NAME, COST_AMOUNT, COST_FREQUENCY, COST_DESCRIPTION) = range(52)

# Define timezone for Rome (for consistent timestamps)
rome_tz = pytz.timezone('Europe/Rome')

# Maps municipio number to list of quartieri (neighborhoods)
municipi_data = {
    'I': ['Centro Storico', 'Trastevere', 'Testaccio', 'Esquilino', 'Prati'],
    'II': ['Parioli', 'Flaminio', 'Salario', 'Trieste'],
    'III': ['Monte Sacro', 'Val Melaina', 'Fidene', 'Bufalotta'],
    'IV': ['San Basilio', 'Tiburtino', 'Pietralata'],
    'V': ['Prenestino', 'Centocelle', 'Tor Pignattara'],
    'VI': ['Torre Angela', 'Tor Bella Monaca', 'Lunghezza'],
    'VII': ['Appio-Latino', 'Tuscolano', 'Cinecittà'],
    'VIII': ['Ostiense', 'Garbatella', 'San Paolo'],
    'IX': ['EUR', 'Torrino', 'Laurentino'],
    'X': ['Ostia', 'Acilia', 'Infernetto'],
    'XI': ['Portuense', 'Magliana', 'Trullo'],
    'XII': ['Monte Verde', 'Gianicolense', 'Pisana'],
    'XIII': ['Aurelio', 'Boccea', 'Casalotti'],
    'XIV': ['Monte Mario', 'Primavalle', 'Ottavia'],
    'XV': ['La Storta', 'Cesano', 'Prima Porta']
}

def check_user_membership(update, context):
    """Check if a user is a member of the private group"""
    PRIVATE_GROUP_ID = os.environ.get('TELEGRAM_GROUP_ID')
    if not PRIVATE_GROUP_ID:
        logger.error("No TELEGRAM_GROUP_ID provided in environment variables")
        return False

    user_id = update.effective_user.id
    try:
        # Check in local database first
        if DBUtils.check_in_group(user_id):
            return True
            
        # If not in database, check with Telegram API
        member = context.bot.get_chat_member(PRIVATE_GROUP_ID, user_id)
        is_member = member.status in ['member', 'administrator', 'creator']
        
        # Update database
        if is_member:
            DBUtils.add_group_member(user_id)
        else:
            DBUtils.remove_group_member(user_id)
            
        return is_member
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

def handle_non_member(update, context):
    """Handle users who are not members of the group"""
    GROUP_INVITE_LINK = "https://t.me/+dku6thBDTGM0MWZk"
    keyboard = [[InlineKeyboardButton("Join the Group", url=GROUP_INVITE_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = (
        "⚠️ You need to be a member of Hikings Rome group to use this bot.\n"
        "Use the button below to join the group and try again using /start."
    )
    
    if update.callback_query:
        update.callback_query.edit_message_text(text=message_text, reply_markup=reply_markup)
    else:
        update.message.reply_text(text=message_text, reply_markup=reply_markup)
        
    return ConversationHandler.END

def error_handler(update, context):
    """Handle errors globally with user-friendly messages"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        raise context.error
    except telegram.error.NetworkError:
        message = (
            "🤖 Oops! Looks like I had a brief power nap! 😴\n\n"
            "The server decided to take a coffee break while you were filling out the form. "
            "I know, bad timing! 🙈\n\n"
            "Could you use the button below to start again? I promise to stay awake this time! ⚡"
        )
    except telegram.error.Unauthorized:
        # User has blocked the bot
        return
    except telegram.error.TimedOut:
        message = (
            "⏰ Time out! Even robots need a breather sometimes!\n\n"
            "Let's start fresh - I'll be quicker this time! 🏃‍♂️"
        )
    except telegram.error.BadRequest as e:
        if "Message is not modified" in str(e):
            # Ignore these specific errors
            return
        message = (
            "🤖 *System reboot detected!*\n\n"
            "Sorry, looks like my circuits got a bit scrambled during a server update. "
            "These things happen when you're a bot living in the cloud! ☁️\n\n"
            "Could you help me out by starting over? "
            "I promise to keep all my circuits in order this time! 🔧✨"
        )
    except Exception:
        message = (
            "🤖 *Beep boop... something went wrong!*\n\n"
            "My processors got a bit tangled up there! 🎭\n"
            "Let's try again - second time's the charm! ✨\n\n"
            "_Note: If this keeps happening, you can always reach out to the hiking group for help!_"
        )

    # Send message to user if possible
    if update and update.effective_chat:
        try:
            keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as send_error:
            logger.error(f"Error sending error message: {send_error}")
            # Try one last send without markdown if first one fails
            try:
                keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message.replace('*', '').replace('_', ''),
                    reply_markup=reply_markup
                )
            except:
                pass

def menu(update, context):
    """Handle the /menu command - entry point for the conversation"""
    logger.info(f"Menu called by user {update.effective_user.id}")
    
    user_id = update.effective_user.id
    username = update.effective_user.username

    # Check group membership
    if not check_user_membership(update, context):
        return handle_non_member(update, context)
    
    # Add or update user in database
    DBUtils.add_or_update_user(user_id, username)
    
    # Check rate limiting
    if not context.bot_data.get('rate_limiter').is_allowed(user_id):
        if update.callback_query:
            update.callback_query.answer("Too many requests. Please wait a minute.")
            update.callback_query.edit_message_text(
                "⚠️ You're making too many requests. Please wait a minute and try again."
            )
        else:
            update.message.reply_text(
                "⚠️ You're making too many requests. Please wait a minute and try again."
            )
        return ConversationHandler.END
    
    # Check if user is an admin
    is_admin = DBUtils.check_is_admin(user_id)
    
    # Verify if user has given privacy consent
    privacy_settings = DBUtils.get_privacy_settings(user_id)
    if not privacy_settings or not privacy_settings.get('basic_consent'):
        # If no consent, show privacy policy first
        return cmd_privacy(update, context)
    
    # Clear user data for fresh start
    context.user_data.clear()
    context.chat_data.clear()
    
    # Store admin status in user_data
    context.user_data['is_admin'] = is_admin
    
    # Create and send appropriate keyboard
    username = update.effective_user.username or "there"
    welcome_message = (
        f"Hi {username} 👋 \n"
        f"I'm Hiky, your digital sherpa for @hikingsrome.\n"
        f"I can't climb mountains, but I sure can answer your messages. \n"
        f"So, how can I help you?"
    )
    
    # Get the base keyboard
    keyboard = KeyboardBuilder.create_menu_keyboard().inline_keyboard
    
    if is_admin:
        keyboard.append([InlineKeyboardButton("Admin Menu 🛠️", callback_data='admin_menu')])

    reply_markup = InlineKeyboardMarkup(keyboard)
        
    if update.callback_query:
        update.callback_query.edit_message_text(welcome_message, reply_markup=reply_markup)
    else:
        update.message.reply_text(welcome_message, reply_markup=reply_markup)
    
    return CHOOSING

def cmd_admin(update, context):
    """Handle /admin command - show admin menu"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if not DBUtils.check_is_admin(user_id):
        update.message.reply_text(
            "⚠️ You don't have admin privileges to use this command."
        )
        return ConversationHandler.END

    # Get cost summary for dashboard
    cost_summary = DBUtils.get_cost_summary()

    # Calculate yearly projection
    total_monthly = next((s['total_amount'] for s in cost_summary if s['frequency'] == 'monthly'), 0)
    total_quarterly = next((s['total_amount'] for s in cost_summary if s['frequency'] == 'quarterly'), 0)
    total_yearly = next((s['total_amount'] for s in cost_summary if s['frequency'] == 'yearly'), 0)
    
    yearly_projection = (total_monthly * 12) + (total_quarterly * 4) + total_yearly

    # Create admin message with cost dashboard
    admin_message = (
        "👑 *Admin Menu*\n\n"
        "What would you like to manage?\n\n"
        "💰 *Cost Summary*\n"
        f"Monthly: {total_monthly}€\n"
        f"Yearly projection: {yearly_projection}€\n"
    )
    
    reply_markup = KeyboardBuilder.create_admin_keyboard()
    
    update.message.reply_text(
        admin_message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_MENU

# Start def to manage cost menu
def show_cost_control_menu(update, context):
    """Show cost control management menu"""
    query = update.callback_query
    query.answer()

    logger.info(f"show_cost_control_menu called by user {query.from_user.id}")
    
    # Check if admin
    user_id = query.from_user.id
    if not DBUtils.check_is_admin(user_id):
        logger.warning(f"User {user_id} attempted to access the cost menu without admin privileges")
        query.edit_message_text("⚠️ You don't have admin privileges to use this menu.")
        return CHOOSING

    try:
        # Get existing costs
        logger.info("Recovering fixed costs from the database...")
        costs = DBUtils.get_fixed_costs()
        logger.info(f"Recovered {len(costs)} fixed costs")
        
        # Create and send keyboard
        reply_markup = KeyboardBuilder.create_cost_control_keyboard(costs)
    
        query.edit_message_text(
            "💰 *Cost Control Management*\n\n"
            "Here you can manage fixed costs for your operation.\n\n"
            "Select an existing cost to edit, or add a new one:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        logger.info("Cost management menu successfully displayed")
        return ADMIN_COSTS
        
    except Exception as e:
        logger.error(f"Error in show_cost_control_menu: {e}")
        query.edit_message_text(
            "⚠️ An error occurred while displaying the cost management menu."
        )
        return ADMIN_MENU

def start_cost_creation(update, context):
    """Start creating a new fixed cost"""
    query = update.callback_query
    query.answer()

    logger.info(f"start_cost_creation called by user {query.from_user.id}")

    try:
        # Clear any existing editing_cost_id to avoid confusion
        if 'editing_cost_id' in context.user_data:
            del context.user_data['editing_cost_id']
            
        query.edit_message_text(
            "📝 Please enter the name for this fixed cost:"
        )
        logger.info("Name entry request for new fixed cost")
        return COST_NAME
        
    except Exception as e:
        logger.error(f"Error in start_cost_creation: {e}")
        query.edit_message_text(
            "⚠️ An error occurred. Please try again later."
        )
        return ADMIN_COSTS

def save_cost_name(update, context):
    """Save cost name"""
    user_id = update.effective_user.id
    logger.info(f"save_cost_name called by user {user_id}")
    
    cost_name = update.message.text.strip()
    logger.info(f"Cost name entered: '{cost_name}'")
    
    if not cost_name:
        logger.warning("Cost name empty, request again")
        update.message.reply_text(
            "⚠️ Name cannot be empty. Please enter a valid name:"
        )
        return COST_NAME
    
    try:
        context.user_data['cost_name'] = cost_name
        logger.info(f"Cost name '{cost_name}' saved in user_data")
        
        # Ask for amount
        update.message.reply_text(
            "💰 Please enter the amount in euros (e.g., 15.50):"
        )
        logger.info("Request input amount")
        return COST_AMOUNT
        
    except Exception as e:
        logger.error(f"Error in save_cost_name: {e}")
        update.message.reply_text(
            "⚠️ An error occurred. Please try again later."
        )
        # Prova a recuperare tornando al menu costi
        reply_markup = KeyboardBuilder.create_cost_control_keyboard(DBUtils.get_fixed_costs())
        update.message.reply_text(
            "Returning to cost menu...",
            reply_markup=reply_markup
        )
        return ADMIN_COSTS

def save_cost_amount(update, context):
    """Save cost amount"""
    user_id = update.effective_user.id
    logger.info(f"save_cost_amount called by user {user_id}")
    
    amount_str = update.message.text.strip()
    logger.info(f"Amount entered: '{amount_str}'")
    
    try:
        # Try to parse as float and validate
        cleaned_amount = amount_str.replace(',', '.')
        # Check that there are no more points after replacement
        if cleaned_amount.count('.') > 1:
            logger.warning(f"Invalid number format (too many dots): {cleaned_amount}")
            raise ValueError("Invalid number format (too many decimal points)")
        
        # Try to parse as float and validate
        amount = float(cleaned_amount)
        logger.info(f"Amount converted to float: {amount}")
        
        if amount < 0:
            logger.warning(f"Negative amount: {amount}, request new entry")
            raise ValueError("Amount must be positive")
            
        context.user_data['cost_amount'] = amount
        logger.info(f"Amount {amount} saved in user_data")
        
        # Ask for frequency
        keyboard = [
            [InlineKeyboardButton("Monthly", callback_data='new_frequency_monthly')],
            [InlineKeyboardButton("Quarterly", callback_data='new_frequency_quarterly')],
            [InlineKeyboardButton("Yearly", callback_data='new_frequency_yearly')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "🔄 Please select the frequency of this cost:",
            reply_markup=reply_markup
        )
        logger.info("Frequency selection request")
        return COST_FREQUENCY
        
    except ValueError as e:
        logger.error(f"Error parsing amoun: {e}")
        update.message.reply_text(
            "⚠️ Please enter a valid positive number (e.g., 15.50):"
        )
        return COST_AMOUNT
    except Exception as e:
        logger.error(f"Generic error in save_cost_amount: {e}")
        update.message.reply_text(
            "⚠️ An unexpected error occurred. Please try again."
        )
        return COST_AMOUNT

def save_cost_frequency(update, context):
    """Save cost frequency"""
    query = update.callback_query
    user_id = query.from_user.id
    logger.info(f"save_cost_frequency called by user {user_id}")

    try:
        query.answer()
        
        frequency = query.data.replace('new_frequency_', '')
        logger.info(f"Frequency selected: {frequency}")
        
        context.user_data['cost_frequency'] = frequency
        logger.info(f"Frequency {frequency} saved in user_data")
        
        # Ask for description
        query.edit_message_text(
            "🗒 Please enter a description for this cost (optional, press /skip to leave blank):"
        )
        logger.info("Description input request")
        return COST_DESCRIPTION
        
    except Exception as e:
        logger.error(f"Error in save_cost_frequency: {e}")
        try:
            query.edit_message_text(
                "⚠️ An error occurred. Please try again later."
            )
        except:
            pass
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Returning to cost menu...",
            reply_markup=KeyboardBuilder.create_cost_control_keyboard(DBUtils.get_fixed_costs())
        )
        return ADMIN_COSTS

def skip_cost_description(update, context):
    """Skip providing a cost description"""
    context.user_data['cost_description'] = ""
    return save_cost_to_database(update, context)

def save_cost_description(update, context):
    """Save cost description and complete creation"""
    context.user_data['cost_description'] = update.message.text
    return save_cost_to_database(update, context)

def save_cost_to_database(update, context):
    """Save the complete cost to database"""
    user_id = update.effective_user.id
    logger.info(f"save_cost_to_database called by user {user_id}")
    
    # Collect data from context
    cost_data = {
        'name': context.user_data.get('cost_name'),
        'amount': context.user_data.get('cost_amount'),
        'frequency': context.user_data.get('cost_frequency'),
        'description': context.user_data.get('cost_description', '')
    }
    
    logger.info(f"Cost data to be saved: {cost_data}")

    # Check that all necessary data is present
    if not all(key in cost_data and cost_data[key] is not None for key in ['name', 'amount', 'frequency']):
        logger.error(f"Cost data not completed: {cost_data}")

        # Display which data are missing in the logs
        for key in ['name', 'amount', 'frequency']:
            if key not in cost_data or cost_data[key] is None:
                logger.error(f"Missing data: {key}")

        # Create an error message and return to the cost menu
        error_message = "⚠️ Incomplete cost data. Please try again."

        if isinstance(update, telegram.Update) and update.message:
            update.message.reply_text(error_message)
        else:
            context.bot.send_message(chat_id=user_id, text=error_message)

        # Back to cost menu
        context.bot.send_message(
            chat_id=user_id,
            text="Returning to cost menu...",
            reply_markup=KeyboardBuilder.create_cost_control_keyboard(DBUtils.get_fixed_costs())
        )
        return ADMIN_COSTS
    
    try:
        # Save to database
        logger.info("Attempt to save cost in database...")
        # Check if we're editing an existing cost or creating a new one
        if 'editing_cost_id' in context.user_data:
            # Update existing cost
            result = DBUtils.update_fixed_cost(context.user_data['editing_cost_id'], user_id, cost_data)
            # Clear the editing ID after the update
            del context.user_data['editing_cost_id']
        else:
            # Add new cost
            result = DBUtils.add_fixed_cost(user_id, cost_data)
            
        logger.info(f"Result saved: {result}")
    
        if result['success']:
            message = (
                f"✅ Fixed cost created successfully!\n\n"
                f"📝 Name: {cost_data['name']}\n"
                f"💰 Amount: {cost_data['amount']}€\n"
                f"🔄 Frequency: {cost_data['frequency']}\n"
            )
        
            if cost_data['description']:
                message += f"🗒 Description: {cost_data['description']}\n"

            logger.info("Cost saved successfully")
        
            # Create back button
            keyboard = [[InlineKeyboardButton("🔙 Back to cost menu", callback_data='admin_costs')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
            if isinstance(update, telegram.Update) and update.message:
                update.message.reply_text(message, reply_markup=reply_markup)
            else:
                context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=reply_markup
                )
        else:
            error_message = f"❌ Failed to create cost: {result.get('error', 'Unknown error')}"
            
            # Create back button
            keyboard = [[InlineKeyboardButton("🔙 Back to cost menu", callback_data='admin_costs')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if isinstance(update, telegram.Update) and update.message:
                update.message.reply_text(error_message, reply_markup=reply_markup)
            else:
                context.bot.send_message(
                    chat_id=user_id,
                    text=error_message,
                    reply_markup=reply_markup
                )

        # Clear the context data related to costs to prevent duplication
        for key in ['cost_name', 'cost_amount', 'cost_frequency', 'cost_description']:
            if key in context.user_data:
                del context.user_data[key]

    except Exception as e:
        logger.error(f"Unexpected error in save_cost_to_database: {e}")
        error_message = "⚠️ An unexpected error occurred. Please try again later."
        
        if isinstance(update, telegram.Update) and update.message:
            update.message.reply_text(error_message)
        else:
            context.bot.send_message(chat_id=user_id, text=error_message)
    
    return ADMIN_COSTS

def handle_cost_selection(update, context):
    """Handle selection of existing cost"""
    query = update.callback_query
    user_id = query.from_user.id
    logger.info(f"handle_cost_selection called by user {user_id}")

    try:
        query.answer()
    
        # Extract cost ID from callback
        cost_id = int(query.data.replace('edit_cost_', ''))
        logger.info(f"Cost ID selected: {cost_id}")
        
        context.user_data['editing_cost_id'] = cost_id
        logger.info(f"Cost ID {cost_id} saved in user_data")
    
        # Get cost details
        costs = DBUtils.get_fixed_costs()
        selected_cost = next((c for c in costs if c['id'] == cost_id), None)
    
        if not selected_cost:
            logger.warning(f"Cost ID {cost_id} not found in the database")
            query.edit_message_text(
                "⚠️ Cost not found. It may have been deleted."
            )
            return show_cost_control_menu(update, context)

        logger.info(f"Cost details found: {selected_cost}")
    
        # Create message
        message = (
            f"💰 *Fixed Cost Details*\n\n"
            f"📝 Name: {selected_cost['name']}\n"
            f"💰 Amount: {selected_cost['amount']}€\n"
            f"🔄 Frequency: {selected_cost['frequency']}\n"
        )
    
        if selected_cost.get('description'):
            message += f"🗒 Description: {selected_cost['description']}\n"
    
        # Create keyboard for actions
        reply_markup = KeyboardBuilder.create_cost_actions_keyboard(cost_id)
    
        query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        logger.info("Cost details successfully displayed")
        return ADMIN_COSTS
        
    except Exception as e:
        logger.error(f"Error in handle_cost_selection: {e}")
        try:
            query.edit_message_text(
                "⚠️ An error occurred while viewing cost details. Please try again."
            )
        except:
            pass
        
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Returning to cost menu...",
            reply_markup=KeyboardBuilder.create_cost_control_keyboard(DBUtils.get_fixed_costs())
        )
        return ADMIN_COSTS

def handle_cost_action(update, context):
    """Handle actions for a specific cost"""
    query = update.callback_query
    query.answer()
    
    action = query.data.split('_')
    cost_id = int(action[-1])
    action_type = '_'.join(action[1:-1])  # edit_name, edit_amount, edit_frequency, edit_description, delete
    
    context.user_data['editing_cost_id'] = cost_id
    
    if action_type == 'edit_name':
        query.edit_message_text(
            "📝 Please enter the new name for this cost:"
        )
        return COST_NAME
        
    elif action_type == 'edit_amount':
        query.edit_message_text(
            "💰 Please enter the new amount in euros (e.g., 15.50):"
        )
        return COST_AMOUNT
        
    elif action_type == 'edit_frequency':
        # Show frequency selection keyboard
        reply_markup = KeyboardBuilder.create_frequency_keyboard(cost_id)
        query.edit_message_text(
            "🔄 Please select the new frequency:",
            reply_markup=reply_markup
        )
        return COST_FREQUENCY
        
    elif action_type == 'edit_description':
        query.edit_message_text(
            "🗒 Please enter a new description for this cost (or send /skip to clear):"
        )
        return COST_DESCRIPTION
        
    elif action_type == 'delete':
        # Confirm deletion
        keyboard = [
            [
                InlineKeyboardButton("Yes, Delete ✅", callback_data=f'confirm_delete_cost_{cost_id}'),
                InlineKeyboardButton("No, Cancel ❌", callback_data=f'edit_cost_{cost_id}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "❓ Are you sure you want to delete this cost?\n\n"
            "This action cannot be undone.",
            reply_markup=reply_markup
        )
        return ADMIN_COSTS
    
    return ADMIN_COSTS

def delete_cost(update, context):
    """Delete a fixed cost"""
    query = update.callback_query
    query.answer()
    
    cost_id = int(query.data.replace('confirm_delete_cost_', ''))
    user_id = query.from_user.id
    
    # Delete from database
    result = DBUtils.delete_fixed_cost(cost_id, user_id)
    
    if result['success']:
        query.edit_message_text(
            "✅ Fixed cost has been deleted successfully."
        )
    else:
        query.edit_message_text(
            f"❌ Failed to delete cost: {result.get('error', 'Unknown error')}"
        )
    
    # Return to cost menu
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Returning to cost menu...",
        reply_markup=KeyboardBuilder.create_cost_control_keyboard(DBUtils.get_fixed_costs())
    )
    return ADMIN_COSTS

def update_cost_name(update, context):
    """Update name for existing cost"""
    cost_id = context.user_data.get('editing_cost_id')
    if not cost_id:
        update.message.reply_text("❌ Error: Cost ID not found. Please try again.")
        return show_cost_control_menu(update, context)
    
    new_name = update.message.text.strip()
    
    if not new_name:
        update.message.reply_text(
            "⚠️ Name cannot be empty. Please enter a valid name:"
        )
        return COST_NAME
    
    # Update in database
    result = DBUtils.update_fixed_cost(
        cost_id, 
        update.effective_user.id,
        {'name': new_name}
    )
    
    if result['success']:
        update.message.reply_text(f"✅ Cost name updated to '{new_name}'.")
    else:
        update.message.reply_text(f"❌ Failed to update: {result.get('error', 'Unknown error')}")
        
    # Show cost menu again
    reply_markup = KeyboardBuilder.create_cost_control_keyboard(DBUtils.get_fixed_costs())
    update.message.reply_text(
        "💰 *Cost Control Management*\n\n"
        "Select an existing cost to edit, or add a new one:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_COSTS

def update_cost_amount(update, context):
    """Update amount for existing cost"""
    cost_id = context.user_data.get('editing_cost_id')
    if not cost_id:
        update.message.reply_text("❌ Error: Cost ID not found. Please try again.")
        return show_cost_control_menu(update, context)
    
    amount_str = update.message.text.strip()
    logger.info(f"Amount entered: '{amount_str}'")
    
    try:
        # Try to parse as float and validate
        cleaned_amount = amount_str.replace(',', '.')

        if cleaned_amount.count('.') > 1:
            logger.warning(f"Invalid number format (too many decimal points): {cleaned_amount}")
            raise ValueError("Invalid number format (too many decimal points)")
            
        amount = float(cleaned_amount)
        logger.info(f"Float amount converted: {amount}")
        
        if amount < 0:
            raise ValueError("Amount must be positive")
            
        # Update in database
        result = DBUtils.update_fixed_cost(
            cost_id, 
            update.effective_user.id,
            {'amount': amount}
        )

        logger.info(f"Update result: {result}")
        
        if result['success']:
            update.message.reply_text(f"✅ Cost amount updated to {amount}€.")
        else:
            update.message.reply_text(f"❌ Failed to update: {result.get('error', 'Unknown error')}")
            
    except ValueError as e:
        logger.error(f"Error parsing amount: {e}")
        update.message.reply_text(
            "⚠️ Please enter a valid positive number. You can use either a dot or a comma as decimal separator (e.g., 15.50 or 15,50)):"
        )
        return COST_AMOUNT
    except Exception as e:
        logger.error(f"General error in update_cost_amount: {e}")
        update.message.reply_text(
            "⚠️ An unexpected error occurred. Please try again."
        )
        return COST_AMOUNT
    
    # Show cost menu again
    reply_markup = KeyboardBuilder.create_cost_control_keyboard(DBUtils.get_fixed_costs())
    update.message.reply_text(
        "💰 *Cost Control Management*\n\n"
        "Select an existing cost to edit, or add a new one:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_COSTS

def update_cost_frequency(update, context):
    """Update frequency for existing cost"""
    query = update.callback_query
    query.answer()
    
    cost_id = context.user_data.get('editing_cost_id')
    if not cost_id:
        query.edit_message_text("❌ Error: Cost ID not found. Please try again.")
        return show_cost_control_menu(update, context)
    
    # Get the frequency from callback data
    data_parts = query.data.split('_')
    frequency = data_parts[1]
    
    # Update in database
    result = DBUtils.update_fixed_cost(
        cost_id, 
        query.from_user.id,
        {'frequency': frequency}
    )
    
    if result['success']:
        query.edit_message_text(f"✅ Cost frequency updated to '{frequency}'.")
    else:
        query.edit_message_text(f"❌ Failed to update: {result.get('error', 'Unknown error')}")
    
    # Show cost menu again
    reply_markup = KeyboardBuilder.create_cost_control_keyboard(DBUtils.get_fixed_costs())
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="💰 *Cost Control Management*\n\n"
            "Select an existing cost to edit, or add a new one:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_COSTS

def update_cost_description(update, context):
    """Update description for existing cost"""
    cost_id = context.user_data.get('editing_cost_id')
    if not cost_id:
        update.message.reply_text("❌ Error: Cost ID not found. Please try again.")
        return show_cost_control_menu(update, context)
    
    description = update.message.text
    
    # Update in database
    result = DBUtils.update_fixed_cost(
        cost_id, 
        update.effective_user.id,
        {'description': description}
    )
    
    if result['success']:
        update.message.reply_text("✅ Cost description updated successfully.")
    else:
        update.message.reply_text(f"❌ Failed to update: {result.get('error', 'Unknown error')}")
    
    # Show cost menu again
    reply_markup = KeyboardBuilder.create_cost_control_keyboard(DBUtils.get_fixed_costs())
    update.message.reply_text(
        "💰 *Cost Control Management*\n\n"
        "Select an existing cost to edit, or add a new one:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_COSTS

def skip_cost_description_update(update, context):
    """Skip providing a description, clearing the existing one"""
    cost_id = context.user_data.get('editing_cost_id')
    if not cost_id:
        update.message.reply_text("❌ Error: Cost ID not found. Please try again.")
        return show_cost_control_menu(update, context)
    
    # Update in database with empty description
    result = DBUtils.update_fixed_cost(
        cost_id, 
        update.effective_user.id,
        {'description': ""}
    )
    
    if result['success']:
        update.message.reply_text("✅ Cost description cleared successfully.")
    else:
        update.message.reply_text(f"❌ Failed to update: {result.get('error', 'Unknown error')}")
    
    # Show cost menu again
    reply_markup = KeyboardBuilder.create_cost_control_keyboard(DBUtils.get_fixed_costs())
    update.message.reply_text(
        "💰 *Cost Control Management*\n\n"
        "Select an existing cost to edit, or add a new one:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_COSTS

def show_cost_summary(update, context):
    """Show summary of all costs by frequency"""
    query = update.callback_query
    query.answer()
    
    # Get summary from database
    summary = DBUtils.get_cost_summary()
    costs = DBUtils.get_fixed_costs()
    
    # Calculate yearly projection
    total_monthly = next((s['total_amount'] for s in summary if s['frequency'] == 'monthly'), 0)
    total_quarterly = next((s['total_amount'] for s in summary if s['frequency'] == 'quarterly'), 0)
    total_yearly = next((s['total_amount'] for s in summary if s['frequency'] == 'yearly'), 0)
    
    yearly_projection = (total_monthly * 12) + (total_quarterly * 4) + total_yearly
    
    # Create detailed message
    message = "📊 *Cost Summary*\n\n"
    
    # Group costs by frequency
    costs_by_frequency = {}
    for cost in costs:
        freq = cost['frequency']
        if freq not in costs_by_frequency:
            costs_by_frequency[freq] = []
        costs_by_frequency[freq].append(cost)
    
    # Show costs grouped by frequency
    frequencies = ['monthly', 'quarterly', 'yearly']
    for freq in frequencies:
        if freq in costs_by_frequency:
            freq_costs = costs_by_frequency[freq]
            freq_total = sum(c['amount'] for c in freq_costs)
            
            freq_title = freq.capitalize()
            message += f"*{freq_title} Costs:* {freq_total}€\n"
            
            for cost in freq_costs:
                message += f"• {cost['name']}: {cost['amount']}€\n"
            
            message += "\n"
    
    # Add projections
    message += "*Yearly Projection:*\n"
    message += f"• Monthly costs (x12): {total_monthly * 12}€\n"
    message += f"• Quarterly costs (x4): {total_quarterly * 4}€\n"
    message += f"• Yearly costs: {total_yearly}€\n"
    message += f"• Total yearly cost: {yearly_projection}€\n"
    
    # Add back button
    keyboard = [[InlineKeyboardButton("🔙 Back to cost menu", callback_data='admin_costs')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_COSTS
    
# End def to manage cost menu

# Start def to manage personal profile
def show_profile_menu(update, context):
    """Show profile menu options"""
    query = update.callback_query
    query.answer()
    
    reply_markup = KeyboardBuilder.create_profile_keyboard()
    
    query.edit_message_text(
        "👤 *Personal Profile*\n\n"
        "Manage your personal information here. This information will be used for hike registrations.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return PROFILE_MENU

def view_profile(update, context):
    """Show user profile information"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    profile = DBUtils.get_user_profile(user_id)
    
    if not profile:
        message = (
            "👤 *Your Profile*\n\n"
            "An error occurred retrieving your profile. Please try again later."
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        # Check if profile is using default values
        default_value = 'Not set'
        is_default = (
            profile.get('name') == default_value and
            profile.get('surname') == default_value and
            profile.get('email') == default_value and
            profile.get('phone') == default_value and
            profile.get('birth_date') == default_value
        )
        
        if is_default:
            # Profile has default values, prompt user to update
            message = (
                "👤 *Your Profile*\n\n"
                "Your profile is not complete. Please use the 'Edit profile' option to set up your profile information.\n\n"
                "All fields (name, surname, email, phone, birth date) are required for hike registration."
            )
            keyboard = [
                [InlineKeyboardButton("📝 Edit profile", callback_data='edit_profile')],
                [InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)        
        else:
            # Format birth date if exists
            birth_date = profile.get('birth_date', '')
            if birth_date:
                try:
                    # Try to convert to display format if stored in database format
                    birth_date = datetime.strptime(birth_date, '%d/%m/%Y').strftime('%d/%m/%Y')
                except ValueError:
                    # If it's already in display format or another format, use as is
                    pass

            # Show warning if any fields are still set to default value
            needs_update = []
            if profile.get('name') == default_value:
                needs_update.append('name')
            if profile.get('surname') == default_value:
                needs_update.append('surname')
            if profile.get('email') == default_value:
                needs_update.append('email')
            if profile.get('phone') == default_value:
                needs_update.append('phone')
            if profile.get('birth_date') == default_value:
                needs_update.append('birth date')
            
            update_warning = ""
            if needs_update:
                update_warning = (
                    f"\n\n⚠️ *Some information needs to be updated:*\n"
                    f"• {', '.join(needs_update)}\n\n"
                    f"These fields are required for hike registration."
                )
                
            message = (
                "👤 *Your Profile*\n\n"
                f"*Telegram ID:* {profile.get('telegram_id', '')}\n"
                f"*Username:* @{profile.get('username', '')}\n"
                f"*Name:* {profile.get('name', 'Not set')}\n"
                f"*Surname:* {profile.get('surname', 'Not set')}\n"
                f"*Email:* {profile.get('email', 'Not set')}\n"
                f"*Phone:* {profile.get('phone', 'Not set')}\n"
                f"*Birth Date:* {birth_date or 'Not set'}\n"
            )
        
            # Add guide status if applicable
            if profile.get('is_guide'):
                message += f"\n*Role:* 👑 Guide"
    
            # Back to profile menu button
            keyboard = [
                [InlineKeyboardButton("📝 Edit profile", callback_data='edit_profile')],
                [InlineKeyboardButton("🔙 Back to profile menu", callback_data='back_to_profile')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(text=message, parse_mode='Markdown', reply_markup=reply_markup)
    return PROFILE_MENU

def edit_profile_menu(update, context):
    """Show edit profile menu"""
    query = update.callback_query
    query.answer()
    
    reply_markup = KeyboardBuilder.create_edit_profile_keyboard()
    
    query.edit_message_text(
        "📝 *Edit Profile*\n\n"
        "Select the information you want to update:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return PROFILE_EDIT

def edit_profile_field(update, context):
    """Handle selection of which profile field to edit"""
    query = update.callback_query
    query.answer()
    
    field = query.data.replace('edit_', '')
    context.user_data['editing_field'] = field
    
    field_names = {
        'name': 'Name',
        'surname': 'Surname',
        'email': 'Email',
        'phone': 'Phone number',
        'birth_date': 'Birth date'
    }

    # Get current value from profile
    user_id = query.from_user.id
    profile = DBUtils.get_user_profile(user_id) or {}
    current_value = profile.get(field, 'Not set')
    
    # Don't show 'Not set' as current value
    current_value_text = ""
    if current_value != 'Not set':
        current_value_text = f"Current value: {current_value}\n\n"
    
    if field == 'birth_date':
        query.edit_message_text(
            "📅 Select the decade of your birth year (required):",
            reply_markup=create_year_selector()
        )
        return PROFILE_BIRTH_DATE
    else:
        query.edit_message_text(
            f"Please enter your {field_names.get(field, field)} (required):"
        )
        
        # Set appropriate state based on field
        states = {
            'name': PROFILE_NAME,
            'surname': PROFILE_SURNAME,
            'email': PROFILE_EMAIL,
            'phone': PROFILE_PHONE
        }
        return states.get(field, PROFILE_EDIT)

def save_profile_name(update, context):
    """Save name from user input"""
    user_id = update.effective_user.id
    name = update.message.text

    if not name.strip():
        update.message.reply_text(
            "⚠️ Name cannot be empty. Please enter your name:"
        )
        return PROFILE_NAME
    
    # Get current profile data
    profile = DBUtils.get_user_profile(user_id) or {}
    profile['name'] = name
    
    # Update profile in database
    result = DBUtils.update_user_profile(user_id, profile)
    
    if result['success']:
        update.message.reply_text(
            "✅ Your name has been updated successfully."
        )
    else:
        update.message.reply_text(
            f"❌ Error updating profile: {result.get('error', 'Unknown error')}"
        )
    
    # Return to edit menu
    reply_markup = KeyboardBuilder.create_edit_profile_keyboard()
    update.message.reply_text(
        "What else would you like to edit?",
        reply_markup=reply_markup
    )
    return PROFILE_EDIT

def save_profile_surname(update, context):
    """Save surname from user input"""
    user_id = update.effective_user.id
    surname = update.message.text

    if not surname.strip():
        update.message.reply_text(
            "⚠️ Surname cannot be empty. Please enter your surname:"
        )
        return PROFILE_SURNAME
    
    # Get current profile data
    profile = DBUtils.get_user_profile(user_id) or {}
    profile['surname'] = surname
    
    # Update profile in database
    result = DBUtils.update_user_profile(user_id, profile)
    
    if result['success']:
        update.message.reply_text(
            "✅ Your surname has been updated successfully."
        )
    else:
        update.message.reply_text(
            f"❌ Error updating profile: {result.get('error', 'Unknown error')}"
        )
    
    # Return to edit menu
    reply_markup = KeyboardBuilder.create_edit_profile_keyboard()
    update.message.reply_text(
        "What else would you like to edit?",
        reply_markup=reply_markup
    )
    return PROFILE_EDIT

def save_profile_email(update, context):
    """Save email from user input"""
    user_id = update.effective_user.id
    email = update.message.text

    if not email.strip():
        update.message.reply_text(
            "⚠️ Email cannot be empty. Please enter your email:"
        )
        return PROFILE_EMAIL
    
    # Get current profile data
    profile = DBUtils.get_user_profile(user_id) or {}
    profile['email'] = email
    
    # Update profile in database
    result = DBUtils.update_user_profile(user_id, profile)
    
    if result['success']:
        update.message.reply_text(
            "✅ Your email has been updated successfully."
        )
    else:
        update.message.reply_text(
            f"❌ Error updating profile: {result.get('error', 'Unknown error')}"
        )
    
    # Return to edit menu
    reply_markup = KeyboardBuilder.create_edit_profile_keyboard()
    update.message.reply_text(
        "What else would you like to edit?",
        reply_markup=reply_markup
    )
    return PROFILE_EDIT

def save_profile_phone(update, context):
    """Save phone number from user input"""
    user_id = update.effective_user.id
    phone = update.message.text

    if not phone.strip():
        update.message.reply_text(
            "⚠️ Phone number cannot be empty. Please enter your phone number:"
        )
        return PROFILE_PHONE
    
    # Get current profile data
    profile = DBUtils.get_user_profile(user_id) or {}
    profile['phone'] = phone
    
    # Update profile in database
    result = DBUtils.update_user_profile(user_id, profile)
    
    if result['success']:
        update.message.reply_text(
            "✅ Your phone number has been updated successfully."
        )
    else:
        update.message.reply_text(
            f"❌ Error updating profile: {result.get('error', 'Unknown error')}"
        )
    
    # Return to edit menu
    reply_markup = KeyboardBuilder.create_edit_profile_keyboard()
    update.message.reply_text(
        "What else would you like to edit?",
        reply_markup=reply_markup
    )
    return PROFILE_EDIT

def handle_profile_birth_date(update, context):
    """Handle date selection from calendar for profile"""
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    data = query.data.split('_')
    action = data[0]
    
    if action == 'decade':
        decade = int(data[1])
        query.edit_message_text(
            "📅 Select your birth year:",
            reply_markup=create_year_buttons(decade)
        )
        return PROFILE_BIRTH_DATE
        
    elif action == 'year':
        year = int(data[1])
        context.user_data['birth_year'] = year
        query.edit_message_text(
            "📅 Select birth month:",
            reply_markup=create_month_buttons(year)
        )
        return PROFILE_BIRTH_DATE
        
    elif action == 'month':
        year = int(data[1])
        month = int(data[2])
        query.edit_message_text(
            "📅 Select birth day:",
            reply_markup=create_calendar(year, month)
        )
        return PROFILE_BIRTH_DATE
        
    elif action == 'date':
        year = int(data[1])
        month = int(data[2])
        day = int(data[3])
        
        selected_date = f"{day:02d}/{month:02d}/{year}"
        context.user_data['birth_date'] = selected_date
        
        # Save birth date to user profile
        user_id = query.from_user.id
        profile = DBUtils.get_user_profile(user_id) or {}
        profile['birth_date'] = selected_date
        
        # Update profile in database
        result = DBUtils.update_user_profile(user_id, profile)
        
        if result['success']:
            query.edit_message_text(
                f"✅ Your birth date has been updated to {selected_date}."
            )
        else:
            query.edit_message_text(
                f"❌ Error updating birth date: {result.get('error', 'Unknown error')}"
            )
        
        # Return to edit menu
        reply_markup = KeyboardBuilder.create_edit_profile_keyboard()
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="What else would you like to edit?",
            reply_markup=reply_markup
        )
        return PROFILE_EDIT
    
    return PROFILE_BIRTH_DATE

def handle_profile_choice(update, context):
    """Handle profile menu choices"""
    query = update.callback_query
    logger.info(f"Profile choice: {query.data} by user {query.from_user.id}")
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
    
    if query.data == 'view_profile':
        return view_profile(update, context)
    
    elif query.data == 'edit_profile':
        return edit_profile_menu(update, context)
    
    elif query.data == 'back_to_profile':
        return show_profile_menu(update, context)
    
    elif query.data == 'back_to_menu':
        return menu(update, context)
    
    return PROFILE_MENU

def handle_save_profile(update, context):
    """Handle saving profile changes"""
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
    
    # Collect all profile data from context
    profile_data = {
        'name': context.user_data.get('profile_name'),
        'surname': context.user_data.get('profile_surname'),
        'email': context.user_data.get('profile_email'),
        'phone': context.user_data.get('profile_phone'),
        'birth_date': context.user_data.get('profile_birth_date')
    }
    
    # Update profile in database
    user_id = query.from_user.id
    result = DBUtils.update_user_profile(user_id, profile_data)
    
    if result['success']:
        query.edit_message_text(
            "✅ Your profile has been updated successfully."
        )
    else:
        query.edit_message_text(
            f"❌ Error updating profile: {result.get('error', 'Unknown error')}"
        )
    
    # Return to profile menu
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="👤 *Personal Profile*\n\n"
             "Manage your personal information here. This information will be used for hike registrations.",
        parse_mode='Markdown',
        reply_markup=KeyboardBuilder.create_profile_keyboard()
    )
    return PROFILE_MENU

# End def to manage personal profile

# Start def to query db
def show_query_db_menu(update, context):
    """Show database query menu for admins"""
    query = update.callback_query
    if query:
        query.answer()
    
    # Check if user is admin
    user_id = update.effective_user.id
    if not DBUtils.check_is_admin(user_id):
        if query:
            query.edit_message_text("⚠️ You don't have admin privileges to use this menu.")
        else:
            update.message.reply_text("⚠️ You don't have admin privileges to use this menu.")
        return CHOOSING
    
    # Create top-level keyboard
    keyboard = [
        [InlineKeyboardButton("📋 Predefined Queries", callback_data='predefined_queries')],
        [InlineKeyboardButton("✏️ Custom Query", callback_data='query_custom')],
        [InlineKeyboardButton("🔙 Back to admin menu", callback_data='back_to_admin')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        "🔍 *Database Query Menu*\n\n"
        "Select an option to query the database.\n"
        "For security reasons, only SELECT queries are allowed."
    )
    
    if query:
        query.edit_message_text(message_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        update.message.reply_text(message_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return ADMIN_QUERY_DB

def show_predefined_queries_menu(update, context):
    """Show predefined queries menu"""
    query = update.callback_query
    query.answer()
    logger.info("Showing predefined queries menu")
    
    # Load custom queries
    custom_queries = DBQueryUtils.load_custom_queries()
    
    # Create keyboard
    keyboard = [
        [InlineKeyboardButton("📊 List of tables", callback_data='query_tables')],
        [InlineKeyboardButton("👥 All users", callback_data='query_users')],
        [InlineKeyboardButton("🏔️ Future hikes", callback_data='query_hikes')]
    ]
    
    # Add custom queries
    for query_data in custom_queries:
        keyboard.append([
            InlineKeyboardButton(f"📊 {query_data['name']}", callback_data=f"query_custom_{query_data['name']}")
        ])
    
    # Add save new query option
    keyboard.append([InlineKeyboardButton("➕ Save new query", callback_data='query_save')])
    
    if custom_queries:
        keyboard.append([InlineKeyboardButton("❌ Delete saved query", callback_data='query_delete')])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "📋 *Predefined Queries*\n\n"
        "Select a query to execute or manage your saved queries.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_QUERY_DB

def handle_predefined_query(update, context):
    """Handle predefined query selection"""
    query = update.callback_query
    query.answer()
    
    query_type = query.data
    logger.info(f"Predefined query selected: {query_type}")
    
    # Explicitly set the current status
    context.chat_data['last_state'] = ADMIN_QUERY_DB
    
    try:
        if query_type == 'query_tables':
            tables_query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
            result = DBQueryUtils.execute_query(tables_query)
            query_text = escape_markdown_v2(tables_query)
            
        elif query_type == 'query_users':
            users_query = """
            SELECT * FROM users
            ORDER BY registration_timestamp DESC
            """
            result = DBQueryUtils.execute_query(users_query)
            query_text = escape_markdown_v2(users_query)
            
        elif query_type == 'query_hikes':
            hikes_query = """
            SELECT 
                h.id, h.hike_name, h.hike_date, h.max_participants, h.difficulty,
                h.latitude, h.longitude, h.is_active,
                (SELECT COUNT(*) FROM registrations r WHERE r.hike_id = h.id) as current_participants
            FROM hikes h
            WHERE h.hike_date >= date('now')
            ORDER BY h.hike_date ASC
            """
            result = DBQueryUtils.execute_query(hikes_query)
            query_text = escape_markdown_v2(hikes_query)
            
        elif query_type.startswith('query_custom_'):
            query_name = query_type.replace('query_custom_', '')
            custom_queries = DBQueryUtils.load_custom_queries()
            saved_query = next((q for q in custom_queries if q['name'] == query_name), None)
            
            if not saved_query:
                query.edit_message_text(
                    "⚠️ Query not found.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')
                    ]])
                )
                return ADMIN_QUERY_DB
            
            result = DBQueryUtils.execute_query(saved_query['query'])
            query_text = saved_query['query']
        else:
            query.edit_message_text(
                f"⚠️ Invalid query type: {query_type}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')
                ]])
            )
            return ADMIN_QUERY_DB
            
        # Saves the query result in the context
        context.user_data['query_result'] = result
        context.user_data['query_text'] = query_text

        logger.info(f"[DEBUG] Result: {result}")
        
        # Call explicitly display_query_results
        return display_query_results(update, context, result, query_text)
    except Exception as e:
        logger.error(f"Error executing predefined query: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            f"❌ Error executing query: {str(e)}\n\nTry again or check logs for details.",
            reply_markup=reply_markup
        )
        return ADMIN_QUERY_DB

def handle_custom_query_request(update, context):
    """Ask for a custom SQL query"""
    query = update.callback_query
    query.answer()

    context.chat_data['last_state'] = ADMIN_QUERY_EXECUTE
    
    # Create cancel button
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data='cancel_query')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "🔍 *Custom Query*\n\n"
        "Enter your SQL query.\n\n"
        "⚠️ *Notes:*\n"
        "• Only SELECT queries are allowed\n"
        "• Maximum timeout: 5 seconds\n"
        "• Maximum 200 rows displayed",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_QUERY_EXECUTE

def execute_custom_query(update, context):
    """Execute the custom query entered by the admin"""
    sql_query = update.message.text.strip()
    
    try:
        # Check and execute query
        result = DBQueryUtils.execute_query(sql_query)
        
        # Format and display results
        return display_query_results(update, context, result, sql_query)
        
    except Exception as e:
        logger.error(f"Error in execute_custom_query: {e}")
        keyboard = [
            [InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')],
            [InlineKeyboardButton("🔙 Back to admin menu", callback_data='back_to_admin')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Check if it's a timeout error
        if isinstance(e, TimeoutError) or "timeout" in str(e).lower():
            update.message.reply_text(
                "⏱️ *Timeout exceeded*\n\n"
                "The query execution exceeded the maximum allowed time (5 seconds).\n"
                "Try to optimize the query or narrow down the results.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            # General error
            update.message.reply_text(
                f"❌ *Error*\n\n{str(e)}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        return ADMIN_QUERY_DB

def display_query_results(update, context, result, query_text):
    """Format and display query results safely with Markdown escaping."""
    is_callback = isinstance(update.callback_query, CallbackQuery)

    if not result['success']:
        error_message = (
            f"❌ *Error executing query*\n\n"
            f"{escape_markdown_v2(result.get('error', 'Unknown error'))}"
        )
        keyboard = [
            [InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')],
            [InlineKeyboardButton("🔙 Back to admin menu", callback_data='back_to_admin')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
       
        if is_callback:
            update.callback_query.edit_message_text(error_message, parse_mode='MarkdownV2', reply_markup=reply_markup)
        else:
            update.message.reply_text(error_message, parse_mode='MarkdownV2', reply_markup=reply_markup)
        return ADMIN_QUERY_DB

    # Store query in context for possible save
    context.user_data['last_query'] = query_text
    context.user_data['query_results'] = result
   
    # Escape query text for safe display
    safe_query_text = escape_preformatted(query_text)

    # Escape header columns
    header = ' \\| '.join([escape_markdown_v2(str(col)) for col in result['column_names']])
    # Format results message
    message = f"🔍 *Query Results*\n\n```{safe_query_text}```\n\n"
   
    if result['row_count'] == 0:
        message += "✅ *Query executed successfully*, but no results were found\\.\n\n"
    else:
        # Add header with column names
        message += f"*Columns:* {header}\n\n"
       
        # Format each row
        for i, row in enumerate(result['rows']):
            if i >= 10:  # Show only first 10 rows in chat
                remaining = result['row_count'] - 10
                message += f"\n_...and {remaining} more results\\.\\.\\._"
                break
               
            row_values = []
            for col in result['column_names']:
                val = row[col]
                # Format value for display
                if val is None:
                    val = 'NULL'
                else:
                    val = str(val)
                    if len(val) > 20:
                        val = val[:17] + '...'
                # Escape markdown characters
                row_values.append(escape_markdown_v2(val))
               
            message += ' \\| '.join(row_values) + '\n'
   
    # Add execution info
    message += f"\n*Total rows:* {result['row_count']}"
    if result['hit_limit']:
        message += f" \\(limit of {MAX_ROWS} rows reached\\)"
   
    # Format and escape execution time
    exec_time_str = f"{result['execution_time']:.3f}"
    message += f"\n*Execution time:* {escape_markdown_v2(exec_time_str)} seconds"
   
    # Add action buttons
    keyboard = []
   
    # Determine if this is a predefined query or a saved query
    is_predefined_query = False

    # Check for predefined queries by exact match
    predefined_queries = [
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name",
        "SELECT * FROM users ORDER BY registration_timestamp DESC",
        "SELECT h.id, h.hike_name, h.hike_date, h.max_participants, h.difficulty, h.latitude, h.longitude, h.is_active, (SELECT COUNT(*) FROM registrations r WHERE r.hike_id = h.id) as current_participants FROM hikes h WHERE h.hike_date >= date('now') ORDER BY h.hike_date ASC"
    ]

    # Check if the query is one of the predefined ones (normalize whitespace for comparison)
    normalized_query = ' '.join(query_text.split())
    for predefined in predefined_queries:
        normalized_predefined = ' '.join(predefined.split())
        if normalized_query == normalized_predefined:
            is_predefined_query = True
            break

    # Check if this is a user-saved query
    custom_queries = DBQueryUtils.load_custom_queries()
    is_saved_query = any(q.get('query', '') == query_text for q in custom_queries)

    # Save query option only for custom queries that aren't already saved
    if not (is_predefined_query or is_saved_query):
        keyboard.append([InlineKeyboardButton("💾 Save this query", callback_data='save_last_query')])
   
    keyboard.append([InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')])
    keyboard.append([InlineKeyboardButton("🔙 Back to admin menu", callback_data='back_to_admin')])
    reply_markup = InlineKeyboardMarkup(keyboard)
   
    try:
        if is_callback:
            update.callback_query.edit_message_text(
                message,
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )
        else:
            update.message.reply_text(
                message,
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )
    except telegram.error.BadRequest as e:
        logger.error(f"[ERROR DISPLAYING QUERY RESULTS] {e}")
        try:
            # First attempt with a formatted error message
            fallback_message = (
                "⚠️ *Error displaying results*\n\n"
                f"`{escape_markdown_v2(str(e))}`\n\n"
                "_Possible causes: too much data or invalid characters\\._"
            )
            if is_callback:
                update.callback_query.edit_message_text(fallback_message, parse_mode='MarkdownV2', reply_markup=reply_markup)
            else:
                update.message.reply_text(fallback_message, parse_mode='MarkdownV2', reply_markup=reply_markup)
        except telegram.error.BadRequest:
            # If that also fails, try without formatting
            try:
                plain_message = "Error displaying results. Try a simpler query or fewer columns."
                if is_callback:
                    update.callback_query.edit_message_text(plain_message, reply_markup=reply_markup)
                else:
                    update.message.reply_text(plain_message, reply_markup=reply_markup)
            except telegram.error.BadRequest:
                # Last resort
                logger.error("Failed to display query results after multiple attempts")
   
    return ADMIN_QUERY_DB

def start_save_query(update, context):
    """Start the process of saving a new query"""
    query = update.callback_query
    query.answer()
    
    # to return to the default query menu
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data='predefined_queries')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query.data == 'query_save':
        # User wants to create a new query from scratch
        query.edit_message_text(
            "💾 *Save New Query*\n\n"
            "Enter the SQL query you want to save:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return ADMIN_QUERY_SAVE
    elif query.data == 'save_last_query':
        # User wants to save the last executed query
        if 'last_query' not in context.user_data:
            query.edit_message_text(
                "⚠️ No recent query to save.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')
                ]])
            )
            return ADMIN_QUERY_DB
        
        # Store the query and ask for a name
        context.user_data['saving_query'] = context.user_data['last_query']
        
        query.edit_message_text(
            "💾 *Save Query*\n\n"
            f"Query to save:\n```\n{context.user_data['saving_query']}\n```\n\n"
            "Enter a name for this query:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return ADMIN_QUERY_NAME
    
    return ADMIN_QUERY_DB

def save_query_text(update, context):
    """Save the query text entered by the admin"""
    query_text = update.message.text
    
    # Validate query
    if not DBQueryUtils.is_select_query(query_text):
        update.message.reply_text(
            "⚠️ Only SELECT queries are allowed for security reasons.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')
            ]])
        )
        return ADMIN_QUERY_DB
    
    # Test the query
    try:
        result = DBQueryUtils.execute_query(query_text)
        if not result['success']:
            update.message.reply_text(
                f"⚠️ The query is not valid: {result.get('error', 'Unknown error')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')
                ]])
            )
            return ADMIN_QUERY_DB
    except Exception as e:
        update.message.reply_text(
            f"⚠️ Error testing query: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')
            ]])
        )
        return ADMIN_QUERY_DB
    
    # Store the query and ask for a name
    context.user_data['saving_query'] = query_text
    
    update.message.reply_text(
        "💾 *Save Query*\n\n"
        f"Query to save:\n```\n{query_text}\n```\n\n"
        "Enter a name for this query:",
        parse_mode='Markdown'
    )
    return ADMIN_QUERY_NAME

def save_query_name(update, context):
    """Save the query with the given name"""
    query_name = update.message.text.strip()
    
    if not query_name:
        update.message.reply_text(
            "⚠️ The name cannot be empty. Enter a name for the query:"
        )
        return ADMIN_QUERY_NAME
    
    # Check for existing query with the same name
    custom_queries = DBQueryUtils.load_custom_queries()
    if any(q['name'] == query_name for q in custom_queries):
        # Ask for confirmation to overwrite
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, overwrite", callback_data=f'confirm_overwrite_{query_name}'),
                InlineKeyboardButton("❌ No, change name", callback_data='change_query_name')
            ],
            [InlineKeyboardButton("🔙 Cancel", callback_data='query_db')]
        ]
        
        update.message.reply_text(
            f"⚠️ A query with the name '{query_name}' already exists.\n"
            "Do you want to overwrite it?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_QUERY_DB
    
    # Save the query
    DBQueryUtils.save_custom_query(query_name, context.user_data['saving_query'])
    
    update.message.reply_text(
        f"✅ Query '{query_name}' saved successfully!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')
        ]])
    )
    return ADMIN_QUERY_DB

def start_delete_query(update, context):
    """Start the process of deleting a saved query"""
    query = update.callback_query
    query.answer()
    
    # Load custom queries
    custom_queries = DBQueryUtils.load_custom_queries()
    
    if not custom_queries:
        query.edit_message_text(
            "⚠️ There are no saved queries to delete.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')
            ]])
        )
        return ADMIN_QUERY_DB
    
    # Create keyboard with all saved queries
    keyboard = []
    for query_data in custom_queries:
        keyboard.append([
            InlineKeyboardButton(f"❌ {query_data['name']}", callback_data=f"delete_query_{query_data['name']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data='query_db')])
    
    query.edit_message_text(
        "❌ *Delete Saved Query*\n\n"
        "Select the query to delete:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_QUERY_DELETE

def confirm_delete_query(update, context):
    """Confirm and process query deletion"""
    query = update.callback_query
    query.answer()
    
    query_name = query.data.replace('delete_query_', '')
    
    # Ask for confirmation
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, delete", callback_data=f'confirm_delete_{query_name}'),
            InlineKeyboardButton("❌ No, cancel", callback_data='query_db')
        ]
    ]
    
    query.edit_message_text(
        f"⚠️ Are you sure you want to delete the query '{query_name}'?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_QUERY_DELETE

def delete_confirmed_query(update, context):
    """Delete the query after confirmation"""
    query = update.callback_query
    query.answer()
    
    query_name = query.data.replace('confirm_delete_', '')
    
    # Delete the query
    DBQueryUtils.delete_custom_query(query_name)
    
    query.edit_message_text(
        f"✅ Query '{query_name}' deleted successfully!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')
        ]])
    )
    return ADMIN_QUERY_DB

def handle_query_overwrite(update, context):
    """Handle query overwrite confirmation"""
    query = update.callback_query
    query.answer()
    
    if query.data == 'change_query_name':
        query.edit_message_text(
            "💾 *Save Query*\n\n"
            "Enter a different name for this query:"
        )
        return ADMIN_QUERY_NAME
    
    query_name = query.data.replace('confirm_overwrite_', '')
    
    # Save the query (overwrite)
    DBQueryUtils.save_custom_query(query_name, context.user_data['saving_query'])
    
    query.edit_message_text(
        f"✅ Query '{query_name}' updated successfully!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to query menu", callback_data='query_db')
        ]])
    )
    return ADMIN_QUERY_DB
# End def to query db


# Start def to manage maintenance

def show_maintenance_menu(update, context):
    """Show maintenance management menu"""
    query = update.callback_query
    query.answer()
    
    # Check if admin
    user_id = query.from_user.id
    if not DBUtils.check_is_admin(user_id):
        query.edit_message_text("⚠️ You don't have admin privileges to use this menu.")
        return CHOOSING
    
    # Get existing maintenance schedules
    schedules = DBUtils.get_maintenance_schedules()
    
    # Create and send keyboard
    reply_markup = KeyboardBuilder.create_maintenance_keyboard(schedules)
    
    query.edit_message_text(
        "🔧 *Maintenance Schedule Management*\n\n"
        "Here you can schedule maintenance windows to notify users when the bot might be unavailable.\n\n"
        "Select an existing schedule to edit, or create a new one:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_MAINTENANCE

def start_maintenance_creation(update, context):
    """Start creating a new maintenance schedule"""
    query = update.callback_query
    query.answer()
    
    query.edit_message_text(
        "📅 Please enter the date for scheduled maintenance (DD/MM/YYYY):"
    )
    return MAINTENANCE_DATE

def save_maintenance_date(update, context):
    """Save maintenance date"""
    # Validate date format
    date_str = update.message.text
    try:
        maintenance_date = datetime.strptime(date_str, '%d/%m/%Y')
        
        # Store in ISO format for database
        context.user_data['maintenance_date'] = maintenance_date.strftime('%Y-%m-%d')
        
    except ValueError:
        update.message.reply_text(
            "⚠️ Invalid date format. Please enter the date as DD/MM/YYYY:"
        )
        return MAINTENANCE_DATE
    
    # Ask for start time
    update.message.reply_text(
        "⏰ Please enter the start time (HH:MM) in 24-hour format:"
    )
    return MAINTENANCE_START_TIME

def save_maintenance_start_time(update, context):
    """Save maintenance start time"""
    # Validate time format
    time_str = update.message.text
    try:
        start_time = datetime.strptime(time_str, '%H:%M').time()
        context.user_data['maintenance_start'] = start_time.strftime('%H:%M:%S')
        
    except ValueError:
        update.message.reply_text(
            "⚠️ Invalid time format. Please enter the time as HH:MM (e.g., 14:30):"
        )
        return MAINTENANCE_START_TIME
    
    # Ask for end time
    update.message.reply_text(
        "⏰ Please enter the end time (HH:MM) in 24-hour format:"
    )
    return MAINTENANCE_END_TIME

def save_maintenance_end_time(update, context):
    """Save maintenance end time"""
    # Validate time format
    time_str = update.message.text
    try:
        end_time = datetime.strptime(time_str, '%H:%M').time()
        
        # Validate that end time is after start time
        start_time_str = context.user_data.get('maintenance_start')
        start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
        
        if end_time <= start_time:
            update.message.reply_text(
                "⚠️ End time must be after start time. Please enter a valid end time:"
            )
            return MAINTENANCE_END_TIME
            
        context.user_data['maintenance_end'] = end_time.strftime('%H:%M:%S')
        
    except ValueError:
        update.message.reply_text(
            "⚠️ Invalid time format. Please enter the time as HH:MM (e.g., 16:30):"
        )
        return MAINTENANCE_END_TIME
    
    # Ask for reason (optional)
    update.message.reply_text(
        "🗒 Please enter a reason for the maintenance (optional, press /skip to leave blank):"
    )
    return MAINTENANCE_REASON

def skip_maintenance_reason(update, context):
    """Skip providing a maintenance reason"""
    context.user_data['maintenance_reason'] = None
    return save_maintenance_schedule(update, context)

def save_maintenance_reason(update, context):
    """Save maintenance reason and complete schedule creation"""
    context.user_data['maintenance_reason'] = update.message.text
    return save_maintenance_schedule(update, context)

def save_maintenance_schedule(update, context):
    """Save the complete maintenance schedule to database"""
    user_id = update.effective_user.id
    
    # Collect data from context
    maintenance_data = {
        'maintenance_date': context.user_data.get('maintenance_date'),
        'start_time': context.user_data.get('maintenance_start'),
        'end_time': context.user_data.get('maintenance_end'),
        'reason': context.user_data.get('maintenance_reason')
    }
    
    # Save to database
    result = DBUtils.add_maintenance(
        user_id,
        maintenance_data['maintenance_date'],
        maintenance_data['start_time'],
        maintenance_data['end_time'],
        maintenance_data['reason']
    )
    
    if result['success']:
        # Format date and times for display
        display_date = datetime.strptime(maintenance_data['maintenance_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
        start_time = maintenance_data['start_time'].split('.')[0]
        end_time = maintenance_data['end_time'].split('.')[0]
        
        message = (
            f"✅ Maintenance schedule created successfully!\n\n"
            f"📅 Date: {display_date}\n"
            f"⏰ Time: {start_time} - {end_time}\n"
        )
        
        if maintenance_data['reason']:
            message += f"🗒 Reason: {maintenance_data['reason']}\n\n"
            
        message += "Users will be notified before the maintenance starts."
        
        # Create back button
        keyboard = [[InlineKeyboardButton("🔙 Back to maintenance menu", callback_data='admin_maintenance')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if isinstance(update, telegram.Update) and update.message:
            update.message.reply_text(message, reply_markup=reply_markup)
        else:
            context.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=reply_markup
            )
    else:
        error_message = f"❌ Failed to create maintenance schedule: {result.get('error', 'Unknown error')}"
        
        # Create back button
        keyboard = [[InlineKeyboardButton("🔙 Back to maintenance menu", callback_data='admin_maintenance')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if isinstance(update, telegram.Update) and update.message:
            update.message.reply_text(error_message, reply_markup=reply_markup)
        else:
            context.bot.send_message(
                chat_id=user_id,
                text=error_message,
                reply_markup=reply_markup
            )
    
    return ADMIN_MAINTENANCE

def handle_maintenance_selection(update, context):
    """Handle selection of existing maintenance schedule"""
    query = update.callback_query
    query.answer()
    
    # Extract maintenance ID from callback
    maintenance_id = int(query.data.replace('edit_maintenance_', ''))
    context.user_data['editing_maintenance_id'] = maintenance_id
    
    # Get maintenance details
    schedules = DBUtils.get_maintenance_schedules(include_past=True)
    selected_schedule = next((s for s in schedules if s['id'] == maintenance_id), None)
    
    if not selected_schedule:
        query.edit_message_text(
            "⚠️ Maintenance schedule not found. It may have been deleted."
        )
        return show_maintenance_menu(update, context)
    
    # Format date and times for display
    if isinstance(selected_schedule['maintenance_date'], str):
        display_date = datetime.strptime(selected_schedule['maintenance_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
    else:
        display_date = selected_schedule['maintenance_date'].strftime('%d/%m/%Y')
        
    start_time = selected_schedule['start_time']
    if isinstance(start_time, str):
        start_time = start_time.split('.')[0]
        
    end_time = selected_schedule['end_time']
    if isinstance(end_time, str):
        end_time = end_time.split('.')[0]
    
    # Create message
    message = (
        f"🔧 *Maintenance Schedule Details*\n\n"
        f"📅 Date: {display_date}\n"
        f"⏰ Time: {start_time} - {end_time}\n"
    )
    
    if selected_schedule.get('reason'):
        message += f"🗒 Reason: {selected_schedule['reason']}\n"
    
    # Add notification status
    if selected_schedule.get('sent_notification'):
        message += f"\n_✅ Notification has been sent to users_"
    else:
        message += f"\n_⏱ Notification will be sent 2 hours before maintenance_"
    
    # Create keyboard for actions
    reply_markup = KeyboardBuilder.create_maintenance_actions_keyboard(maintenance_id)
    
    query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_MAINTENANCE

def handle_maintenance_action(update, context):
    """Handle actions for a specific maintenance schedule"""
    query = update.callback_query
    query.answer()
    
    action = query.data.split('_')
    maintenance_id = int(action[-1])
    action_type = '_'.join(action[1:-1])  # edit_date, edit_time, edit_reason, delete
    
    context.user_data['editing_maintenance_id'] = maintenance_id
    
    if action_type == 'edit_date':
        query.edit_message_text(
            "📅 Please enter the new date for scheduled maintenance (DD/MM/YYYY):"
        )
        return MAINTENANCE_DATE
        
    elif action_type == 'edit_time':
        query.edit_message_text(
            "⏰ Please enter the new start time (HH:MM) in 24-hour format:"
        )
        return MAINTENANCE_START_TIME
        
    elif action_type == 'edit_reason':
        query.edit_message_text(
            "🗒 Please enter a new reason for the maintenance (or send /skip to clear):"
        )
        return MAINTENANCE_REASON
        
    elif action_type == 'delete':
        # Confirm deletion
        keyboard = [
            [
                InlineKeyboardButton("Yes, Delete ✅", callback_data=f'confirm_delete_maintenance_{maintenance_id}'),
                InlineKeyboardButton("No, Cancel ❌", callback_data=f'edit_maintenance_{maintenance_id}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "❓ Are you sure you want to delete this maintenance schedule?\n\n"
            "This action cannot be undone.",
            reply_markup=reply_markup
        )
        return ADMIN_MAINTENANCE
    
    return ADMIN_MAINTENANCE

def delete_maintenance_schedule(update, context):
    """Delete a maintenance schedule"""
    query = update.callback_query
    query.answer()
    
    maintenance_id = int(query.data.replace('confirm_delete_maintenance_', ''))
    user_id = query.from_user.id
    
    # Delete from database
    result = DBUtils.delete_maintenance(maintenance_id, user_id)
    
    if result['success']:
        query.edit_message_text(
            "✅ Maintenance schedule has been deleted successfully."
        )
    else:
        query.edit_message_text(
            f"❌ Failed to delete maintenance schedule: {result.get('error', 'Unknown error')}"
        )
    
    # Return to maintenance menu
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Returning to maintenance menu...",
        reply_markup=KeyboardBuilder.create_maintenance_keyboard(DBUtils.get_maintenance_schedules())
    )
    return ADMIN_MAINTENANCE

def update_maintenance_date(update, context):
    """Update date for existing maintenance"""
    maintenance_id = context.user_data.get('editing_maintenance_id')
    if not maintenance_id:
        update.message.reply_text("❌ Error: Maintenance ID not found. Please try again.")
        return show_maintenance_menu(update, context)
    
    # Validate date format
    date_str = update.message.text
    try:
        maintenance_date = datetime.strptime(date_str, '%d/%m/%Y')
        # Store in ISO format for database
        date_iso = maintenance_date.strftime('%Y-%m-%d')
        
        # Update in database
        result = DBUtils.update_maintenance(
            maintenance_id, 
            update.effective_user.id,
            maintenance_date=date_iso
        )
        
        if result['success']:
            update.message.reply_text(f"✅ Maintenance date updated to {date_str}.")
        else:
            update.message.reply_text(f"❌ Failed to update: {result.get('error', 'Unknown error')}")
            
    except ValueError:
        update.message.reply_text(
            "⚠️ Invalid date format. Please enter the date as DD/MM/YYYY:"
        )
        return MAINTENANCE_DATE
    
    # Show maintenance menu again
    reply_markup = KeyboardBuilder.create_maintenance_keyboard(DBUtils.get_maintenance_schedules())
    update.message.reply_text(
        "🔧 *Maintenance Schedule Management*\n\n"
        "Select an existing schedule to edit, or create a new one:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_MAINTENANCE

def update_maintenance_time(update, context):
    """Update start time for existing maintenance and request end time"""
    maintenance_id = context.user_data.get('editing_maintenance_id')
    if not maintenance_id:
        update.message.reply_text("❌ Error: Maintenance ID not found. Please try again.")
        return show_maintenance_menu(update, context)
    
    # Validate time format
    time_str = update.message.text
    try:
        start_time = datetime.strptime(time_str, '%H:%M').time()
        start_iso = start_time.strftime('%H:%M:%S')
        
        # Store for later
        context.user_data['new_maintenance_start'] = start_iso
        
        # Ask for end time
        update.message.reply_text(
            "⏰ Please enter the new end time (HH:MM) in 24-hour format:"
        )
        return MAINTENANCE_END_TIME
        
    except ValueError:
        update.message.reply_text(
            "⚠️ Invalid time format. Please enter the time as HH:MM (e.g., 14:30):"
        )
        return MAINTENANCE_START_TIME

def update_maintenance_end_time(update, context):
    """Update both start and end times for existing maintenance"""
    maintenance_id = context.user_data.get('editing_maintenance_id')
    if not maintenance_id:
        update.message.reply_text("❌ Error: Maintenance ID not found. Please try again.")
        return show_maintenance_menu(update, context)
    
    start_time = context.user_data.get('new_maintenance_start')
    
    # Validate time format
    time_str = update.message.text
    try:
        end_time = datetime.strptime(time_str, '%H:%M').time()
        
        # Validate that end time is after start time
        start_time_obj = datetime.strptime(start_time, '%H:%M:%S').time()
        
        if end_time <= start_time_obj:
            update.message.reply_text(
                "⚠️ End time must be after start time. Please enter a valid end time:"
            )
            return MAINTENANCE_END_TIME
            
        end_iso = end_time.strftime('%H:%M:%S')
        
        # Update in database
        result = DBUtils.update_maintenance(
            maintenance_id, 
            update.effective_user.id,
            start_time=start_time,
            end_time=end_iso
        )
        
        if result['success']:
            start_display = start_time[:5]  # HH:MM
            end_display = end_iso[:5]       # HH:MM
            update.message.reply_text(f"✅ Maintenance time updated to {start_display} - {end_display}.")
        else:
            update.message.reply_text(f"❌ Failed to update: {result.get('error', 'Unknown error')}")
            
    except ValueError:
        update.message.reply_text(
            "⚠️ Invalid time format. Please enter the time as HH:MM (e.g., 16:30):"
        )
        return MAINTENANCE_END_TIME
    
    # Show maintenance menu again
    reply_markup = KeyboardBuilder.create_maintenance_keyboard(DBUtils.get_maintenance_schedules())
    update.message.reply_text(
        "🔧 *Maintenance Schedule Management*\n\n"
        "Select an existing schedule to edit, or create a new one:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_MAINTENANCE

def update_maintenance_reason(update, context):
    """Update reason for existing maintenance"""
    maintenance_id = context.user_data.get('editing_maintenance_id')
    if not maintenance_id:
        update.message.reply_text("❌ Error: Maintenance ID not found. Please try again.")
        return show_maintenance_menu(update, context)
    
    reason = update.message.text
    
    # Update in database
    result = DBUtils.update_maintenance(
        maintenance_id, 
        update.effective_user.id,
        reason=reason
    )
    
    if result['success']:
        update.message.reply_text("✅ Maintenance reason updated successfully.")
    else:
        update.message.reply_text(f"❌ Failed to update: {result.get('error', 'Unknown error')}")
    
    # Show maintenance menu again
    reply_markup = KeyboardBuilder.create_maintenance_keyboard(DBUtils.get_maintenance_schedules())
    update.message.reply_text(
        "🔧 *Maintenance Schedule Management*\n\n"
        "Select an existing schedule to edit, or create a new one:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_MAINTENANCE

def skip_update_reason(update, context):
    """Skip providing a reason, clearing the existing one"""
    maintenance_id = context.user_data.get('editing_maintenance_id')
    if not maintenance_id:
        update.message.reply_text("❌ Error: Maintenance ID not found. Please try again.")
        return show_maintenance_menu(update, context)
    
    # Update in database with empty reason
    result = DBUtils.update_maintenance(
        maintenance_id, 
        update.effective_user.id,
        reason=""  # Set to empty string to clear
    )
    
    if result['success']:
        update.message.reply_text("✅ Maintenance reason cleared successfully.")
    else:
        update.message.reply_text(f"❌ Failed to update: {result.get('error', 'Unknown error')}")
    
    # Show maintenance menu again
    reply_markup = KeyboardBuilder.create_maintenance_keyboard(DBUtils.get_maintenance_schedules())
    update.message.reply_text(
        "🔧 *Maintenance Schedule Management*\n\n"
        "Select an existing schedule to edit, or create a new one:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_MAINTENANCE

# Maintenance notification
def check_and_send_maintenance_notifications(context):
    """Check for maintenance scheduled today or tomorrow and send notifications"""
    try:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Get maintenance scheduled for today or tomorrow
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT 
            id,
            maintenance_date,
            start_time,
            end_time,
            reason,
            sent_notification
        FROM maintenance
        WHERE 
            maintenance_date IN (?, ?) AND
            (
                (maintenance_date = ? AND sent_notification < 1) OR 
                (maintenance_date = ? AND sent_notification < 2)
            )
        """, (today, tomorrow, today, tomorrow))
        
        schedules = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        for maintenance in schedules:
            # Format date and times for display
            if isinstance(maintenance['maintenance_date'], str):
                maintenance_date = datetime.strptime(maintenance['maintenance_date'], '%Y-%m-%d').date()
                display_date = maintenance_date.strftime('%d/%m/%Y')
            else:
                maintenance_date = maintenance['maintenance_date']
                display_date = maintenance_date.strftime('%d/%m/%Y')
                
            if isinstance(maintenance['start_time'], str):
                start_time = maintenance['start_time'].split('.')[0]  # Remove microseconds
                start_time_display = start_time[:5]  # Just HH:MM
            else:
                start_time_display = maintenance['start_time'].strftime('%H:%M')
                
            if isinstance(maintenance['end_time'], str):
                end_time = maintenance['end_time'].split('.')[0]  # Remove microseconds
                end_time_display = end_time[:5]  # Just HH:MM
            else:
                end_time_display = maintenance['end_time'].strftime('%H:%M')
            
            # Determine notification type (day before or day of)
            is_today = (maintenance_date == today)
            
            # Create notification message
            message = (
                "🔧 *SCHEDULED MAINTENANCE NOTICE* 🔧\n\n"
                f"The bot will be undergoing maintenance "
            )
            
            if is_today:
                message += f"*TODAY* ({display_date}):\n"
            else:
                message += f"*TOMORROW* ({display_date}):\n"
                
            message += (
                f"⏰ *Time:* {start_time_display} - {end_time_display}\n\n"
            )
            
            if maintenance.get('reason'):
                message += f"*Reason:* {maintenance['reason']}\n\n"
                
            message += (
                "During this period, the bot may be unresponsive or have limited functionality. "
                "We apologize for any inconvenience and appreciate your patience.\n\n"
                "_This is an automated message. Please do not reply._"
            )
            
            # Get all users
            users = DBUtils.get_all_users()
            
            # Send notifications
            notification_count = 0
            for user_id in users:
                try:
                    context.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    notification_count += 1
                except Exception as e:
                    logger.error(f"Failed to send maintenance notification to user {user_id}: {e}")
            
            # Update notification status
            # For "tomorrow" maintenance, set sent_notification to 1
            # For "today" maintenance, set sent_notification to 2
            new_status = 2 if is_today else 1
            
            conn = DBUtils.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE maintenance
            SET sent_notification = ?
            WHERE id = ? AND sent_notification < ?
            """, (new_status, maintenance['id'], new_status))
            conn.commit()
            conn.close()
            
            logger.info(f"Maintenance notification ({new_status}) sent to {notification_count} users for maintenance ID {maintenance['id']}")
            
    except Exception as e:
        logger.error(f"Error checking maintenance notifications: {e}")

# End def to manage maintenance

def check_telegram_stars_availability(bot):
    """Check if Telegram Stars are available for this bot"""
    try:
        # Get bot info to check properties
        bot_info = bot.get_me()
        logger.info(f"Bot info: {bot_info}")
        
        # Log bot properties that might affect Stars functionality
        logger.info(f"Bot username: {bot_info.username}")
        logger.info(f"Bot can_join_groups: {bot_info.can_join_groups}")
        logger.info(f"Bot can_read_all_group_messages: {bot_info.can_read_all_group_messages}")
        logger.info(f"Bot supports_inline_queries: {bot_info.supports_inline_queries}")
        
        return True
    except Exception as e:
        logger.error(f"Error checking bot properties: {e}")
        return False

def test_telegram_stars(update, context):
    """Test function for Telegram Stars donation"""
    try:
        # Create a minimal test invoice
        prices = [LabeledPrice('Test Donation', 100)]  # $1.00
        
        # Send the minimal test invoice
        context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title="Test Donation",
            description="This is a test donation.",
            payload="test_payload",
            provider_token="",  # Empty for Telegram Stars
            currency="USD",
            prices=prices,
            # Make sure to include all required parameters
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False
        )
        
        return True
    except Exception as e:
        logger.error(f"Test Telegram Stars error: {e}")
        update.message.reply_text(f"Error testing Telegram Stars: {str(e)}")
        return False

# Start handle hikes signup
def handle_hike_signup(update, context):
    """Handle initial signup for a hike, checking profile information first"""
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    # Check hike availability before starting questionnaire
    available_hikes = DBUtils.get_available_hikes(query.from_user.id)
    
    if not available_hikes:
        keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "There are no available hikes at the moment.",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    # Store available hikes for later use
    context.user_data['available_hikes'] = available_hikes

    # Check if profile info exists
    user_id = query.from_user.id
    profile = DBUtils.get_user_profile(user_id)
    
    # Check if profile has all required information
    has_complete_profile = (
        profile and
        profile.get('name') not in [None, '', 'Not set'] and
        profile.get('surname') not in [None, '', 'Not set'] and
        profile.get('email') not in [None, '', 'Not set'] and
        profile.get('phone') not in [None, '', 'Not set'] and
        profile.get('birth_date') not in [None, '', 'Not set']
    )
    
    if has_complete_profile:
        # Show profile information and ask for confirmation
        name_surname = f"{profile.get('name')} {profile.get('surname')}"
        email = profile.get('email')
        phone = profile.get('phone')
        birth_date = profile.get('birth_date')
        
        message = (
            "📋 *Your profile information:*\n\n"
            f"*Name and surname:* {name_surname}\n"
            f"*Email:* {email}\n"
            f"*Phone:* {phone}\n"
            f"*Birth date:* {birth_date}\n\n"
            "Is this information correct? If you select 'Yes', you'll continue with the registration. "
            "If you select 'No', you'll be directed to your profile to update it."
        )
        
        keyboard = [
            [
                InlineKeyboardButton("Yes ✅", callback_data='confirm_profile_yes'),
                InlineKeyboardButton("No ❌", callback_data='confirm_profile_no')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Store profile info for later use if confirmed
        context.user_data['profile_info'] = {
            'name_surname': name_surname,
            'email': email,
            'phone': phone,
            'birth_date': birth_date
        }
        
        return HIKE_CHOICE
    else:
        # Profile is incomplete, direct to regular form or profile
        missing_fields = []
        if not profile or profile.get('name') in [None, '', 'Not set']:
            missing_fields.append("name")
        if not profile or profile.get('surname') in [None, '', 'Not set']:
            missing_fields.append("surname")
        if not profile or profile.get('email') in [None, '', 'Not set']:
            missing_fields.append("email")
        if not profile or profile.get('phone') in [None, '', 'Not set']:
            missing_fields.append("phone")
        if not profile or profile.get('birth_date') in [None, '', 'Not set']:
            missing_fields.append("birth date")
            
        message = (
            "⚠️ *Your profile is incomplete*\n\n"
            f"The following information is missing: {', '.join(missing_fields)}.\n\n"
            "Would you like to update your profile first or continue with the registration form?"
        )
        
        keyboard = [
            [InlineKeyboardButton("Update Profile 📝", callback_data='update_profile_first')],
            [InlineKeyboardButton("Continue with Form 📋", callback_data='continue_with_form')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return HIKE_CHOICE

def handle_profile_confirmation(update, context):
    """Handle response to profile confirmation question"""
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
    
    if query.data == 'confirm_profile_yes':
        # User confirmed profile information, move to medical conditions
        context.user_data['name_surname'] = context.user_data['profile_info']['name_surname']
        context.user_data['email'] = context.user_data['profile_info']['email']
        context.user_data['phone'] = context.user_data['profile_info']['phone']
        context.user_data['birth_date'] = context.user_data['profile_info']['birth_date']
        
        query.edit_message_text(
            "🏥 Medical conditions\n"
            "_Do you have any medical conditions that might create difficulties for you "
            "(Knee pain, cardiopathy, allergies etc.)?_",
            parse_mode='Markdown'
        )
        return MEDICAL
    
    elif query.data == 'confirm_profile_no':
        # User wants to update profile first
        return show_profile_menu(update, context)
    
    elif query.data == 'update_profile_first':
        # User wants to update incomplete profile
        return show_profile_menu(update, context)
    
    elif query.data == 'continue_with_form':
        # User wants to continue with regular form despite incomplete profile
        query.edit_message_text("👋 Name and surname?")
        return NAME
    
    return HIKE_CHOICE

# End handle hikes signup

def handle_menu_choice(update, context):
    """Handle menu choice selections"""
    query = update.callback_query
    logger.info(f"Menu choice: {query.data} by user {query.from_user.id}")
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        logger.error(f"Error in query.answer(): {e}")
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
    
    if not check_user_membership(update, context):
        return handle_non_member(update, context)

    if query.data == 'personal_profile':
        return show_profile_menu(update, context)
    
    elif query.data == 'manage_hikes':
        reply_markup = KeyboardBuilder.create_manage_hikes_keyboard()
        query.edit_message_text(
            "🏔️ *Hike Management*\n\n"
            "What would you like to do?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif query.data == 'signup':
        return handle_hike_signup(update, context)
    
    elif query.data == 'myhikes':
        return show_my_hikes(query, context)

    elif query.data == 'calendar':
        return show_hike_calendar(query, context)
    
    elif query.data == 'links':
        reply_markup = KeyboardBuilder.create_links_keyboard()
        
        query.edit_message_text(
            "Here are some useful links:",
            reply_markup=reply_markup
        )
        return CHOOSING

    elif query.data == 'donation':
        reply_markup = KeyboardBuilder.create_donation_keyboard()
        query.edit_message_text(
            "Thank you for considering supporting our hiking community! 💖\n\n"
            "Choose your preferred donation method:",
            reply_markup=reply_markup
        )
        return DONATION
    
    elif query.data == 'back_to_menu':
        return menu(update, context)
    
    elif query.data == 'admin_menu':
        # Check if user is admin
        user_id = query.from_user.id
        if not DBUtils.check_is_admin(user_id):
            query.edit_message_text(
                "⚠️ You don't have admin privileges to use this menu."
            )
            return CHOOSING
        
        reply_markup = KeyboardBuilder.create_admin_keyboard()
        
        query.edit_message_text(
            "👑 *Admin Menu*\n\n"
            "What would you like to manage?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return ADMIN_MENU

def handle_donation(update, context):
    """Handle donation choices"""
    query = update.callback_query
    logger.info(f"Donation choice: {query.data} by user {query.from_user.id}")
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
    
    if query.data == 'donation_stars':
        try:
            # Define donation amounts with your requested values
            donation_options = [
                LabeledPrice('Small Support ☕', 299),   # $2.99
                LabeledPrice('Regular Support 🍕', 499),  # $4.99
                LabeledPrice('Generous Support 🏔️', 999),  # $9.99
                LabeledPrice('Super Support 🌟', 1999)   # $19.99
            ]
            
            # Send invoice with more logging and error handling
            logger.info("Attempting to send invoice...")
            
            # Send invoice with minimal required parameters to debug
            context.bot.send_invoice(
                chat_id=query.message.chat_id,
                title="Support Hikings Rome",
                description="Your donation helps us organize better hikes and maintain our community!",
                payload="donation_payload",
                provider_token="",  # Empty string for Telegram Stars
                currency="USD",
                prices=donation_options
            )
            
            logger.info("Invoice sent successfully")
            
            query.edit_message_text(
                "I've sent you the donation options! "
                "Thank you for supporting Hikings Rome! 🙏"
            )
            
            return CHOOSING
            
        except Exception as e:
            # Log the specific error
            logger.error(f"Error sending invoice: {e}")
            query.edit_message_text(
                "Sorry, there was an error processing your donation request. "
                "Please try again later or use PayPal instead."
            )
            return CHOOSING
    
    return CHOOSING

def precheckout_callback(update, context):
    """Handle pre-checkout"""
    query = update.pre_checkout_query
    
    # Always accept
    query.answer(ok=True)

def successful_payment_callback(update, context):
    """Handle successful payment"""
    payment = update.message.successful_payment
    amount = payment.total_amount / 100  # Convert to dollars
    
    update.message.reply_text(
        f"Thank you for your donation of ${amount:.2f}! 💖\n\n"
        f"Your support helps us organize better hikes and maintain our community. "
        f"We appreciate your contribution to Hikings Rome!"
    )
    
    # Get the donor information
    donor_name = update.effective_user.first_name
    donor_username = update.effective_user.username or 'no username'
    donor_id = update.effective_user.id
    
    # Create notification message
    notification = (
        f"💰 New donation received!\n"
        f"Amount: ${amount:.2f}\n"
        f"From: {donor_name} (@{donor_username})\n"
        f"User ID: {donor_id}"
    )
    
    # Notify all admin users
    try:
        # Get all admin users from database
        admin_users = DBUtils.get_all_admins()
        
        for admin in admin_users:
            try:
                context.bot.send_message(
                    chat_id=admin['telegram_id'],
                    text=notification
                )
                logger.info(f"Donation notification sent to admin {admin['telegram_id']}")
            except Exception as e:
                logger.error(f"Failed to notify admin {admin['telegram_id']}: {e}")
    except Exception as e:
        logger.error(f"Failed to get admin list: {e}")

def handle_admin_choice(update, context):
    """Handle admin menu choices"""
    query = update.callback_query
    logger.info(f"Admin choice: {query.data} by user {query.from_user.id}")
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
    
    # Check admin status
    user_id = query.from_user.id
    if not DBUtils.check_is_admin(user_id):
        query.edit_message_text(
            "⚠️ You don't have admin privileges to use this menu."
        )
        return CHOOSING
    
    if query.data == 'admin_create_hike':
        query.edit_message_text(
            "🏔️ *Create New Hike*\n\n"
            "Let's set up a new hike. First, what's the name of the hike?",
            parse_mode='Markdown'
        )
        return ADMIN_HIKE_NAME
    
    elif query.data == 'admin_manage_hikes':
        # Get all active hikes
        hikes = DBUtils.get_available_hikes(include_inactive=True)
    
        if not hikes:
            keyboard = [[InlineKeyboardButton("🔙 Back to admin menu", callback_data='back_to_admin')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "There are no hikes at the moment.",
                reply_markup=reply_markup
            )
            return ADMIN_MENU
        
        # Filter active and inactive hikes
        active_hikes = [h for h in hikes if h['is_active'] == 1]
        inactive_hikes = [h for h in hikes if h['is_active'] == 0]
        
        context.user_data['admin_hikes'] = hikes
        
        # Create message with sections for active and inactive hikes
        message = "📝 *Manage Hikes*\n\n"
        
        if active_hikes:
            message += "*Active hikes:*\n"
            for h in active_hikes:
                hike_date = datetime.strptime(h['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
                spots_left = h['max_participants'] - h['current_participants']
                message += f"• {hike_date} - {h['hike_name']} ({spots_left} spots left)\n"
        else:
            message += "*No active hikes*\n"
        
        if inactive_hikes:
            message += "\n*Inactive/Cancelled hikes:*\n"
            for h in inactive_hikes:
                hike_date = datetime.strptime(h['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
                message += f"• {hike_date} - {h['hike_name']} (cancelled)\n"
        
        # Create keyboard for hike selection
        reply_markup = KeyboardBuilder.create_admin_hikes_keyboard(hikes)
        
        query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return ADMIN_MENU

    elif query.data == 'admin_costs':
        return show_cost_control_menu(update, context)

    elif query.data == 'back_to_admin':
        reply_markup = KeyboardBuilder.create_admin_keyboard()
        
        query.edit_message_text(
            "👑 *Admin Menu*\n\n"
            "What would you like to manage?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return ADMIN_MENU
    
    elif query.data == 'query_db':
        return show_query_db_menu(update, context)
    
    elif query.data == 'admin_add_admin':
        query.edit_message_text(
            "👑 *Add Admin*\n\n"
            "Please enter the Telegram ID of the user you want to make an admin:"
        )
        return ADMIN_ADD_ADMIN

    elif query.data == 'admin_maintenance':
        return show_maintenance_menu(update, context)
    
    elif query.data.startswith('admin_hike_'):
        hike_id = int(query.data.replace('admin_hike_', ''))
        context.user_data['selected_admin_hike'] = hike_id
    
        # Find the hike details
        hikes = context.user_data.get('admin_hikes', [])
        selected_hike = next((h for h in hikes if h['id'] == hike_id), None)
        
        if not selected_hike:
            query.edit_message_text(
                "Hike not found. Please try again."
            )
            return ADMIN_MENU
        
        # Check if hike is active
        is_active = selected_hike.get('is_active', 1) == 1
        
        hike_date = datetime.strptime(selected_hike['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
        
        # Create appropriate keyboard based on active status
        reply_markup = KeyboardBuilder.create_admin_hike_options_keyboard(hike_id, is_active)
        
        status_text = "Active" if is_active else "Cancelled"
        status_emoji = "🟢" if is_active else "🔴"

        # Get the number of guides registered
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT COUNT(*) as guide_count FROM registrations r
        JOIN users u ON r.telegram_id = u.telegram_id
        WHERE r.hike_id = ? AND u.is_guide = 1
        """, (hike_id,))
        guide_result = cursor.fetchone()
        conn.close()
        
        registered_guides = guide_result['guide_count'] if guide_result else 0
        total_guides = selected_hike.get('guides', 1)  # Default to 1 if not specified
        
        query.edit_message_text(
            f"🏔️ *{selected_hike['hike_name']}*\n\n"
            f"Date: {hike_date}\n"
            f"Status: {status_emoji} {status_text}\n"
            f"Participants: {selected_hike['current_participants']}/{selected_hike['max_participants']}\n"
            f"Guides: {registered_guides}/{total_guides}\n"
            f"Difficulty: {selected_hike.get('difficulty', 'Not set')}\n\n"
            f"What would you like to do with this hike?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return ADMIN_MENU
    
    elif query.data.startswith('admin_edit_'):
        # Implement edit hike functionality
        hike_id = int(query.data.replace('admin_edit_', ''))
        context.user_data['editing_hike_id'] = hike_id
        
        query.edit_message_text(
            "✏️ *Edit Hike*\n\n"
            "What's the new name for this hike?",
            parse_mode='Markdown'
        )
        return ADMIN_HIKE_NAME
    
    elif query.data.startswith('admin_participants_'):
        # Implement view participants functionality
        hike_id = int(query.data.replace('admin_participants_', ''))
        
        # Get hike details
        hikes = context.user_data.get('admin_hikes', [])
        selected_hike = next((h for h in hikes if h['id'] == hike_id), None)
        
        if not selected_hike:
            query.edit_message_text(
                "Hike not found. Please try again."
            )
            return ADMIN_MENU
        
        # Get participants
        participants = DBUtils.get_hike_participants(hike_id)
        
        if not participants:
            query.edit_message_text(
                f"No participants registered for hike: {selected_hike['hike_name']}\n\n"
                f"Use /admin to go back to the admin menu."
            )
            return ADMIN_MENU
        
        # Format date for display
        hike_date = datetime.strptime(selected_hike['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')

        # Count regular participants (non-guides)
        regular_participants = sum(1 for p in participants if not p.get('is_guide'))
        guide_participants = sum(1 for p in participants if p.get('is_guide'))
        
        # Create message with participants info
        message = f"🏔️ *{selected_hike['hike_name']}* - {hike_date}\n"
        message += f"👥 *Participants: {regular_participants}/{selected_hike['max_participants']}*\n"
        message += f"👑 *Guides: {guide_participants}/{selected_hike.get('guides', 1)}*\n\n"

        # First list guides
        guide_count = 0
        for i, p in enumerate(participants, 1):
            if p.get('is_guide'):
                guide_count += 1
                message += f"*👑 GUIDE {guide_count}. {p['name_surname']}*\n"
                message += f"📱 {p['phone']} | 📧 {p['email']}\n"
                message += f"📍 {p['location']} | 🚗 Car share: {'✅' if p.get('car_sharing') else '❌'}\n"
                
                if p.get('notes'):
                    message += f"📝 Notes: {p['notes']}\n"
                
                # Add separator between participants
                message += "\n" + "—" * 10 + "\n\n"
        
        # Then list regular participants
        reg_count = 0
        for i, p in enumerate(participants, 1):
            if not p.get('is_guide'):
                reg_count += 1
                message += f"*{reg_count}. {p['name_surname']}*\n"
                message += f"📱 {p['phone']} | 📧 {p['email']}\n"
                message += f"📍 {p['location']} | 🚗 Car share: {'✅' if p.get('car_sharing') else '❌'}\n"
            
                if p.get('notes'):
                    message += f"📝 Notes: {p['notes']}\n"
            
                # Add separator between participants
                if reg_count < regular_participants:
                    message += "\n" + "—" * 10 + "\n\n"
        
        # Create back button
        keyboard = [[InlineKeyboardButton("🔙 Back to hike options", callback_data=f'admin_hike_{hike_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except telegram.error.BadRequest as e:
            # Handle case where message is too long
            if "Message is too long" in str(e):
                # Split the message if it's too long
                chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
                
                # Send first chunk with edit_message_text
                query.edit_message_text(
                    chunks[0] + "\n\n_(continued in next message...)_",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
                # Send remaining chunks as new messages
                for chunk in chunks[1:]:
                    context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=chunk,
                        parse_mode='Markdown'
                    )
            else:
                # For other errors, send as plain text
                query.edit_message_text(
                    "Participants list (formatting removed due to length):\n\n" + 
                    message.replace('*', ''),
                    reply_markup=reply_markup
                )
        
        return ADMIN_MENU
    
    elif query.data.startswith('admin_cancel_'):
        # Implement cancel hike functionality
        # This would need careful handling to notify registered participants
        hike_id = int(query.data.replace('admin_cancel_', ''))
        
        # For now, just confirm cancellation
        keyboard = [
            [
                InlineKeyboardButton("Yes, Cancel Hike", callback_data=f'confirm_cancel_hike_{hike_id}'),
                InlineKeyboardButton("No, Keep Hike", callback_data='admin_manage_hikes')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "⚠️ *Cancel Hike*\n\n"
            "Are you sure you want to cancel this hike? "
            "This will notify all registered participants and remove their registrations.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return ADMIN_MENU
    
    elif query.data.startswith('admin_reactivate_'):
        hike_id = int(query.data.replace('admin_reactivate_', ''))
        
        # For confirmation, show dialog
        keyboard = [
            [
                InlineKeyboardButton("Yes, Reactivate", callback_data=f'confirm_reactivate_hike_{hike_id}'),
                InlineKeyboardButton("No, Keep Cancelled", callback_data=f'admin_hike_{hike_id}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "🔄 *Reactivate Hike*\n\n"
            "Are you sure you want to reactivate this cancelled hike?\n\n"
            "This will make the hike visible again to users.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return ADMIN_MENU
    
    elif query.data.startswith('confirm_reactivate_hike_'):
        # Process hike reactivation
        hike_id = int(query.data.replace('confirm_reactivate_hike_', ''))
        user_id = query.from_user.id
        
        # Reactivate the hike in the database
        result = DBUtils.reactivate_hike(hike_id, user_id)
        
        if result['success']:
            hike_info = result.get('hike_info', {})
            hike_name = hike_info.get('hike_name', 'Unknown hike')
            
            if 'hike_date' in hike_info:
                hike_date = datetime.strptime(hike_info['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
            else:
                hike_date = 'Unknown date'
            
            query.edit_message_text(
                f"✅ Hike '{hike_name}' on {hike_date} has been reactivated successfully.\n\n"
                f"It is now visible to users again."
            )
        else:
            query.edit_message_text(
                f"❌ Failed to reactivate hike: {result.get('error', 'Unknown error')}."
            )
        
        # Return to admin menu after a short delay
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Returning to admin menu...",
            reply_markup=KeyboardBuilder.create_admin_keyboard()
        )
        return ADMIN_MENU
    
    elif query.data.startswith('confirm_cancel_hike_'):
        # Implement confirmed hike cancellation
        hike_id = int(query.data.replace('confirm_cancel_hike_', ''))
        user_id = query.from_user.id
        
        # Cancel the hike in the database
        result = DBUtils.cancel_hike(hike_id, user_id)
        
        if result['success']:
            # Get hike details
            hikes = context.user_data.get('admin_hikes', [])
            selected_hike = next((h for h in hikes if h['id'] == hike_id), None)
            
            if selected_hike:
                hike_name = selected_hike['hike_name']
                hike_date = datetime.strptime(selected_hike['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
                
                # Send notification to registered participants if any
                registrations = result.get('registrations', [])
                notification_count = 0
                
                for reg in registrations:
                    try:
                        context.bot.send_message(
                            chat_id=reg['telegram_id'],
                            text=(
                                f"⚠️ *Important Notification*\n\n"
                                f"We're sorry to inform you that the following hike has been cancelled:\n\n"
                                f"🏔️ *{hike_name}*\n"
                                f"📅 *Date:* {hike_date}\n\n"
                                f"If you have any questions, please contact the organizers or email hikingsrome@gmail.com."
                            ),
                            parse_mode='Markdown'
                        )
                        notification_count += 1
                    except Exception as e:
                        logger.error(f"Failed to notify user {reg['telegram_id']}: {e}")
                
                query.edit_message_text(
                    f"✅ Hike '{hike_name}' on {hike_date} has been cancelled successfully.\n\n"
                    f"Notifications sent to {notification_count} out of {len(registrations)} registered participants."
                )
            else:
                query.edit_message_text(
                    "✅ Hike has been cancelled successfully."
                )
        else:
            query.edit_message_text(
                f"❌ Failed to cancel hike: {result.get('error', 'Unknown error')}."
            )
        
        # Return to admin menu after a short delay
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Returning to admin menu...",
            reply_markup=KeyboardBuilder.create_admin_keyboard()
        )
        return ADMIN_MENU
    
    return ADMIN_MENU

def add_admin_handler(update, context):
    """Handle adding a new admin"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if not DBUtils.check_is_admin(user_id):
        update.message.reply_text(
            "⚠️ You don't have admin privileges to use this command."
        )
        return ConversationHandler.END
    
    # Get new admin ID from message
    try:
        new_admin_id = int(update.message.text.strip())
    except ValueError:
        update.message.reply_text(
            "⚠️ Invalid Telegram ID. Please enter a valid numeric ID."
        )
        return ADMIN_ADD_ADMIN
    
    # Check if user exists and add as admin
    if not DBUtils.check_user_exists(new_admin_id):
        update.message.reply_text(
            "⚠️ This user has not interacted with the bot yet. "
            "They need to use /start first."
        )
        return ADMIN_MENU
    
    result = DBUtils.add_admin(new_admin_id, user_id)
    
    if result['success']:
        update.message.reply_text(
            f"✅ User with ID {new_admin_id} has been added as an admin successfully."
        )
    else:
        update.message.reply_text(
            f"❌ Failed to add admin: {result['error']}"
        )
    
    # Return to admin menu
    reply_markup = KeyboardBuilder.create_admin_keyboard()
    update.message.reply_text(
        "What would you like to do next?",
        reply_markup=reply_markup
    )
    return ADMIN_MENU

def admin_save_hike_name(update, context):
    """Save hike name from admin input"""
    context.chat_data['last_state'] = ADMIN_HIKE_NAME
    context.user_data['hike_name'] = update.message.text
    
    # Ask for hike date
    update.message.reply_text(
        "📅 What's the date for this hike?\n"
        "Please enter the date in format DD/MM/YYYY."
    )
    return ADMIN_HIKE_DATE

def admin_save_hike_date(update, context):
    """Save hike date from admin input"""
    context.chat_data['last_state'] = ADMIN_HIKE_DATE
    
    # Validate date format
    date_str = update.message.text
    try:
        hike_date = datetime.strptime(date_str, '%d/%m/%Y')
        
        # Check if date is in the future
        if hike_date.date() <= date.today():
            update.message.reply_text(
                "⚠️ The date must be in the future. Please enter a valid future date:"
            )
            return ADMIN_HIKE_DATE
            
        # Store in ISO format for database
        context.user_data['hike_date'] = hike_date.strftime('%Y-%m-%d')
        
    except ValueError:
        update.message.reply_text(
            "⚠️ Invalid date format. Please enter the date as DD/MM/YYYY:"
        )
        return ADMIN_HIKE_DATE
    
    # Ask for number of guides
    update.message.reply_text(
        "👥 How many guides?"
    )
    return ADMIN_HIKE_GUIDES

def admin_save_guides(update, context):
    """Save number of guides from admin input"""
    context.chat_data['last_state'] = ADMIN_HIKE_GUIDES
    
    # Validate number
    try:
        num_guides = int(update.message.text)
        if num_guides <= 0:
            raise ValueError("Must be positive")
            
        context.user_data['guides'] = num_guides
        
    except ValueError:
        update.message.reply_text(
            "⚠️ Please enter a valid positive number:"
        )
        return ADMIN_HIKE_GUIDES
    
    # Ask for maximum participants
    update.message.reply_text(
        "👥 What's the maximum number of participants for this hike (excluding guides)?"
    )
    return ADMIN_HIKE_MAX_PARTICIPANTS

def admin_save_max_participants(update, context):
    """Save maximum participants from admin input"""
    context.chat_data['last_state'] = ADMIN_HIKE_MAX_PARTICIPANTS
    
    # Validate number
    try:
        max_participants = int(update.message.text)
        if max_participants <= 0:
            raise ValueError("Must be positive")
            
        context.user_data['max_participants'] = max_participants
        
    except ValueError:
        update.message.reply_text(
            "⚠️ Please enter a valid positive number:"
        )
        return ADMIN_HIKE_MAX_PARTICIPANTS
    
    # Ask for location
    update.message.reply_text(
        "📍 Please enter the location coordinates for this hike.\n"
        "Format: latitude,longitude (e.g., 41.9028,12.4964)"
    )
    return ADMIN_HIKE_LOCATION

def admin_save_location(update, context):
    """Save hike location from admin input"""
    context.chat_data['last_state'] = ADMIN_HIKE_LOCATION
    
    # Validate coordinates
    coords_str = update.message.text
    try:
        lat, lon = map(float, coords_str.split(','))
        
        # Basic validation
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError("Invalid coordinates range")
            
        context.user_data['latitude'] = lat
        context.user_data['longitude'] = lon
        
    except (ValueError, IndexError):
        update.message.reply_text(
            "⚠️ Invalid coordinates format. Please enter as latitude,longitude:"
        )
        return ADMIN_HIKE_LOCATION
    
    # Ask for difficulty
    reply_markup = KeyboardBuilder.create_difficulty_keyboard()
    update.message.reply_text(
        "📊 Select the difficulty level for this hike:",
        reply_markup=reply_markup
    )
    return ADMIN_HIKE_DIFFICULTY

def admin_save_difficulty(update, context):
    """Save hike difficulty from admin selection"""
    query = update.callback_query
    query.answer()
    
    difficulty = query.data.replace('difficulty_', '')
    context.user_data['difficulty'] = difficulty.capitalize()

    # Show fixed costs verification before asking for description
    # Get current fixed costs
    fixed_costs = DBUtils.get_fixed_costs()

    # Format costs into message
    costs_message = "🔍 *Are the fixed costs correct?*\n\n"
    for cost in fixed_costs:
        costs_message += f"• {cost['name']}: {cost['amount']}€ ({cost['frequency']})\n"

    costs_message += "\nPlease verify these costs before continuing with hike creation."

    # Create confirmation buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, continue", callback_data='costs_verified'),
            InlineKeyboardButton("❌ No, need to update", callback_data='update_costs')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Ask for description
    query.edit_message_text(
        costs_message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_HIKE_DESCRIPTION

def handle_costs_verification(update, context):
    """Handle response to fixed costs verification"""
    query = update.callback_query
    query.answer()
    
    if query.data == 'costs_verified':
        # Continue with hike creation - ask for variable costs
        query.edit_message_text(
            "💰 *Variable Costs Entry*\n\n"
            "Please enter the variable costs for this specific hike (tolls, gasoline, etc.).\n"
            "Enter a number (e.g., 15.50):"
        )
        return ADMIN_HIKE_VARIABLE_COSTS
    
    elif query.data == 'update_costs':
        # Redirect to the costs management panel
        query.edit_message_text(
            "⚠️ Hike creation cancelled. Redirecting to cost management..."
        )
        
        # Clear hike creation data
        for key in ['hike_name', 'hike_date', 'max_participants', 'latitude', 
                    'longitude', 'difficulty', 'guides']:
            if key in context.user_data:
                del context.user_data[key]
        
        # Show cost control menu after a short delay
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="💰 *Cost Control Management*\n\n"
                "Here you can manage fixed costs for your operation.\n\n"
                "Select an existing cost to edit, or add a new one:",
            parse_mode='Markdown',
            reply_markup=KeyboardBuilder.create_cost_control_keyboard(DBUtils.get_fixed_costs())
        )
        return ADMIN_COSTS

def admin_save_variable_costs(update, context):
    """Save variable costs for this hike"""
    try:
        # Get the variable costs input
        variable_costs_str = update.message.text.strip()
        
        # Clean and convert to float
        cleaned_amount = variable_costs_str.replace(',', '.')
        
        # Check for multiple decimal points
        if cleaned_amount.count('.') > 1:
            update.message.reply_text(
                "⚠️ Invalid number format. Please enter a valid amount (e.g., 15.50):"
            )
            return ADMIN_HIKE_VARIABLE_COSTS
        
        # Convert to float and validate
        variable_costs = float(cleaned_amount)
        
        if variable_costs < 0:
            update.message.reply_text(
                "⚠️ Variable costs cannot be negative. Please enter a valid amount:"
            )
            return ADMIN_HIKE_VARIABLE_COSTS
        
        # Store the variable costs
        context.user_data['variable_costs'] = variable_costs
        
        # Now continue with description
        update.message.reply_text(
            "📝 Please enter a description for this hike. "
            "Include any important details like meeting point, what to bring, etc."
        )
        return ADMIN_HIKE_DESCRIPTION
        
    except ValueError:
        update.message.reply_text(
            "⚠️ Please enter a valid number for variable costs (e.g., 15.50):"
        )
        return ADMIN_HIKE_VARIABLE_COSTS

def admin_save_description(update, context):
    """Save hike description from admin input"""
    context.chat_data['last_state'] = ADMIN_HIKE_DESCRIPTION
    context.user_data['description'] = update.message.text
    
    # Show summary and confirm
    hike_data = context.user_data
    
    # Format date for display
    display_date = datetime.strptime(hike_data['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
    
    summary = (
        f"🏔️ *New Hike Summary*\n\n"
        f"Name: {hike_data['hike_name']}\n"
        f"Date: {display_date}\n"
        f"Guides: {hike_data['guides']}\n"
        f"Max Participants: {hike_data['max_participants']}\n"
        f"Location: {hike_data['latitude']}, {hike_data['longitude']}\n"
        f"Difficulty: {hike_data['difficulty']}\n\n"
        f"Description:\n{hike_data['description']}\n\n"
        f"Is this correct?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("Yes, Create Hike", callback_data='confirm_create_hike'),
            InlineKeyboardButton("No, Cancel", callback_data='cancel_create_hike')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        summary,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADMIN_CONFIRM_HIKE

def admin_confirm_hike(update, context):
    """Handle confirmation of new hike creation"""
    query = update.callback_query
    query.answer()
    
    if query.data == 'confirm_create_hike':
        # Save the hike to database
        hike_data = {
            'hike_name': context.user_data.get('hike_name'),
            'hike_date': context.user_data.get('hike_date'),
            'max_participants': context.user_data.get('max_participants'),
            'guides': context.user_data.get('guides', 0),
            'latitude': context.user_data.get('latitude'),
            'longitude': context.user_data.get('longitude'),
            'difficulty': context.user_data.get('difficulty'),
            'description': context.user_data.get('description')
        }
        
        result = DBUtils.add_hike(hike_data, query.from_user.id)
        
        if result['success']:
            query.edit_message_text(
                "✅ New hike created successfully!"
            )
        else:
            query.edit_message_text(
                f"❌ Failed to create hike: {result['error']}"
            )
    else:
        query.edit_message_text(
            "❌ Hike creation cancelled."
        )
    
    # Return to admin menu
    reply_markup = KeyboardBuilder.create_admin_keyboard()
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="What would you like to do next?",
        reply_markup=reply_markup
    )
    return ADMIN_MENU

def cmd_privacy(update, context):
    """Handle /privacy command - show and manage privacy settings"""
    user_id = update.effective_user.id
    username = update.effective_user.username or 'Not set'
    
    if not check_user_membership(update, context):
        return handle_non_member(update, context)
    
    # Add or update user in database
    DBUtils.add_or_update_user(user_id, username)
    
    # Check current privacy settings
    privacy_settings = DBUtils.get_privacy_settings(user_id)
    
    if privacy_settings and privacy_settings.get('basic_consent'):
        # If user already gave consent, show current settings
        message = (
            "🔐 *Your current privacy settings:*\n\n"
            f"• Basic consent (Required): ✅\n"
            f"• Share contacts for car sharing: {'✅' if privacy_settings.get('car_sharing_consent') else '❌'}\n"
            f"• Photo sharing consent: {'✅' if privacy_settings.get('photo_consent') else '❌'}\n"
            f"• Marketing communications: {'✅' if privacy_settings.get('marketing_consent') else '❌'}\n\n"
            "Would you like to modify these settings?"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ Modify settings", callback_data='privacy_modify')],
            [InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]
        ]
    else:
        # If user never gave consent
        message = (
            "🔐 *Privacy Policy*\n\n"
            "Please review our privacy policy and provide your consent preferences.\n\n"
            "*Required consent:*\n"
            "• Collection of basic data for hike registration\n"
            "• Emergency contact information\n"
            "• Age verification\n\n"
            "*Optional consents:*\n"
            "• Share contacts for car sharing arrangements\n"
            "• Photo sharing during hikes\n"
            "• Marketing communications"
        )
        
        keyboard = [
            [InlineKeyboardButton("📜 View full policy", url="https://www.hikingsrome.com/privacy")],
            [InlineKeyboardButton("✅ Set privacy preferences", callback_data='privacy_start')]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        update.callback_query.edit_message_text(
            message, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(
            message, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
    
    return PRIVACY_CONSENT

def handle_privacy_choices(update, context):
    """Handle privacy consent choices"""
    query = update.callback_query
    choice = query.data.replace('privacy_', '')
    logger.info(f"Privacy choice: {choice}")
    
    if choice == 'start' or choice == 'modify':
        # Initialize basic choices
        privacy_settings = DBUtils.get_privacy_settings(query.from_user.id)
        
        # Initialize choices based on existing record if available
        context.user_data['privacy_choices'] = {
            'basic_consent': True,  # Always true, required
            'car_sharing_consent': privacy_settings.get('car_sharing_consent', False) if privacy_settings else False,
            'photo_consent': privacy_settings.get('photo_consent', False) if privacy_settings else False,
            'marketing_consent': privacy_settings.get('marketing_consent', False) if privacy_settings else False
        }
        
        message_text = (
            "🔐 *Privacy Settings*\n\n"
            "Basic consent is required and includes:\n"
            "• Collection of basic data for registration\n"
            "• Emergency contact information\n"
            "• Age verification\n\n"
            "Optional consents (click to toggle):"
        )
        
        reply_markup = KeyboardBuilder.create_privacy_settings_keyboard(context.user_data['privacy_choices'])
        
        try:
            query.edit_message_text(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except telegram.error.BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
                
        return PRIVACY_CONSENT
        
    elif choice in ['carsharing', 'photos', 'marketing']:
        # Toggle specific consent
        consent_mapping = {
            'carsharing': 'car_sharing_consent',
            'photos': 'photo_consent',
            'marketing': 'marketing_consent'
        }
        
        # Initialize if not exists
        if 'privacy_choices' not in context.user_data:
            privacy_settings = DBUtils.get_privacy_settings(query.from_user.id)
            context.user_data['privacy_choices'] = {
                'basic_consent': True,
                'car_sharing_consent': privacy_settings.get('car_sharing_consent', False) if privacy_settings else False,
                'photo_consent': privacy_settings.get('photo_consent', False) if privacy_settings else False,
                'marketing_consent': privacy_settings.get('marketing_consent', False) if privacy_settings else False
            }
        
        # Toggle consent
        consent_key = consent_mapping[choice]
        current_value = context.user_data['privacy_choices'][consent_key]
        context.user_data['privacy_choices'][consent_key] = not current_value
        
        reply_markup = KeyboardBuilder.create_privacy_settings_keyboard(context.user_data['privacy_choices'])
        
        try:
            query.edit_message_text(
                text="🔐 *Privacy Settings*\n\n"
                "Basic consent is required and includes:\n"
                "• Collection of basic data for registration\n"
                "• Emergency contact information\n"
                "• Age verification\n\n"
                "Optional consents (click to toggle):",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except telegram.error.BadRequest as e:
            if "Message is not modified" in str(e):
                # Force update by adding invisible character
                query.edit_message_text(
                    text="🔐 *Privacy Settings*\n\n"
                         "Basic consent is required and includes:\n"
                         "• Collection of basic data for registration\n"
                         "• Emergency contact information\n"
                         "• Age verification\n\n"
                         "Optional consents (click to toggle):\u200B",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                logger.error(f"Error updating message: {e}")
                
        return PRIVACY_CONSENT
        
    elif choice == 'save':
        try:
            choices = context.user_data['privacy_choices']
            
            # Update settings in database
            settings = {
                'basic_consent': True,  # Always required
                'car_sharing_consent': choices.get('car_sharing_consent', False),
                'photo_consent': choices.get('photo_consent', False),
                'marketing_consent': choices.get('marketing_consent', False),
                'consent_version': '1.0'
            }
            
            DBUtils.update_privacy_settings(query.from_user.id, settings)
            
            # Show confirmation
            keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
            
            message = (
                "✅ Privacy settings saved successfully!\n\n"
                "*Your current settings:*\n"
                "• Basic consent (Required): ✅\n"
                f"• Share contacts for car sharing: {'✅' if choices.get('car_sharing_consent') else '❌'}\n"
                f"• Photo sharing: {'✅' if choices.get('photo_consent') else '❌'}\n"
                f"• Marketing communications: {'✅' if choices.get('marketing_consent') else '❌'}"
            )
            
            query.edit_message_text(
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            return CHOOSING
            
        except Exception as e:
            logger.error(f"Error saving privacy choices: {e}")
            query.answer("Error saving preferences. Please try again.", show_alert=True)
            return PRIVACY_CONSENT
            
    return CHOOSING

def cmd_bug(update, context):
    """Handle /bug command - report a bug"""
    if not check_user_membership(update, context):
        return handle_non_member(update, context)
    
    logger.info("Bug command called")
    
    message = (
        "🐛 Found a bug? Looks like our robot friends need some maintenance!\n\n"
        "Please send an email to *hikingsrome@gmail.com* describing what happened. "
        "Screenshots are worth a thousand bug reports! 📸\n\n"
        "_Don't worry, even the most advanced AI occasionally trips over its own algorithms!_ 🤖"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in cmd_bug: {e}")
        update.message.reply_text(
            message.replace('*', '').replace('_', ''),
            reply_markup=reply_markup
        )
    
    return CHOOSING

def handle_lost_conversation(update, context):
    """Handle cases where conversation state is lost"""
    message = (
        "🤖 *Oops! Server Update Detected!* 🔄\n\n"
        "Hey there! While you were filling out the form, I received some fancy new updates. "
        "Unfortunately, that means I lost track of where we were... 😅\n\n"
        "Could you help me out by starting fresh with /menu? "
        "I promise to keep all your answers safe this time! 🚀\n\n"
        "_P.S. Sorry for the interruption - even robots need occasional upgrades!_ ✨"
    )
    
    try:
        # If it's a callback query, respond to avoid loading spinner
        if isinstance(update, telegram.Update) and update.callback_query:
            update.callback_query.answer()
            update.callback_query.edit_message_text(
                text=message,
                parse_mode='Markdown'
            )
        else:
            # If it's a regular message
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in handle_lost_conversation: {e}")
        # Fallback without markdown if needed
        try:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message.replace('*', '').replace('_', '')
            )
        except:
            pass
            
    return ConversationHandler.END

def restart(update, context):
    """Handle /restart command - reset the bot state"""
    logger.info(f"Restart called by user {update.effective_user.id}")
    user_id = update.effective_user.id
    current_state = context.chat_data.get('last_state')
    
    if not check_user_membership(update, context):
        return handle_non_member(update, context)
        
    # If user was in the middle of filling a form, ask for confirmation
    non_form_states = [None, CHOOSING, PRIVACY_CONSENT, IMPORTANT_NOTES, ADMIN_MENU]
    if current_state and current_state not in non_form_states:
        logger.info("User in form - asking confirmation")
        reply_markup = KeyboardBuilder.create_yes_no_keyboard('yes_restart', 'no_restart')
        
        update.message.reply_text(
            "⚠️ You are in the middle of registration.\n"
            "Are you sure you want to restart? All progress will be lost.",
            reply_markup=reply_markup
        )
        return current_state
        
    # If no form in progress, simply reset the bot
    logger.info("No form in progress - resetting bot")
    context.user_data.clear()
    context.chat_data.clear()
    
    return menu(update, context)

def handle_restart_confirmation(update, context):
    """Handle restart confirmation"""
    logger.info("Handling restart confirmation")
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    if query.data == 'yes_restart':
        try:
            query.message.delete()  # Delete confirmation message
        except:
            pass
        context.user_data.clear()
        context.chat_data.clear()
        return menu(update, context)
    else:
        current_state = context.chat_data.get('last_state', CHOOSING)
        try:
            query.edit_message_text("✅ Restart cancelled. You can continue from where you left off.")
            # Send appropriate question based on state
            if current_state == NAME:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="👋 Name and surname?"
                )
            elif current_state == EMAIL:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="📧 Email?"
                )
            elif current_state == PHONE:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="📱 Phone number?"
                )
            # Add more states as needed...
        except Exception as e:
            logger.error(f"Error in handle_restart_confirmation: {e}")
            # Fallback in case of error
            try:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Please continue with your previous answer."
                )
            except:
                pass
                
        return current_state

def show_my_hikes(update, context):
    """Handle viewing registered hikes"""
    if isinstance(update, CallbackQuery):
        user_id = update.from_user.id
        query = update
    else:
        user_id = update.message.from_user.id
        query = None
        
    hikes = DBUtils.get_user_hikes(user_id)
    
    if not hikes:
        keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "You are not registered for any hikes yet."
        if query:
            query.edit_message_text(message, reply_markup=reply_markup)
        else:
            update.message.reply_text(message, reply_markup=reply_markup)
        return CHOOSING
        
    context.user_data['my_hikes'] = hikes
    context.user_data['current_hike_index'] = 0
    
    return show_hike_details(update, context)

def show_hike_details(update, context):
    """Show details of a specific hike the user is registered for"""
    hikes = context.user_data['my_hikes']
    current_index = context.user_data['current_hike_index']
    hike = hikes[current_index]
    
    # Format date for display
    if isinstance(hike['hike_date'], str):
        hike_date = datetime.strptime(hike['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
    else:
        hike_date = hike['hike_date'].strftime('%d/%m/%Y')
        
    # Create navigation buttons
    reply_markup = KeyboardBuilder.create_hike_navigation_keyboard(current_index, len(hikes))
    
    # Prepare the message
    message_text = (
        f"🗓 *Date:* {hike_date}\n"
        f"🏃 *Hike:* {hike['hike_name']}\n"
        f"🚗 *Car sharing:* {'Yes' if hike.get('car_sharing') else 'No'}\n\n"
        f"Hike {current_index + 1} of {len(hikes)}"
    )
    
    if isinstance(update, CallbackQuery):
        update.edit_message_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    return CHOOSING

def handle_hike_navigation(update, context):
    """Handle navigation between user's hikes"""
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    if query.data == 'next_hike':
        context.user_data['current_hike_index'] += 1
    elif query.data == 'prev_hike':
        context.user_data['current_hike_index'] -= 1
        
    return show_hike_details(query, context)

def handle_cancel_request(update, context):
    """Handle initial cancellation request"""
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    # Get hike index to cancel
    hike_index = int(query.data.split('_')[2])
    hike = context.user_data['my_hikes'][hike_index]
    context.user_data['hike_to_cancel'] = hike
    
    reply_markup = KeyboardBuilder.create_yes_no_keyboard('confirm_cancel', 'abort_cancel')
    
    # Format date for display
    if isinstance(hike['hike_date'], str):
        hike_date = datetime.strptime(hike['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
    else:
        hike_date = hike['hike_date'].strftime('%d/%m/%Y')
    
    query.edit_message_text(
        f"Are you sure you want to cancel your registration for:\n\n"
        f"🗓 {hike_date}\n"
        f"🏃 {hike['hike_name']}?",
        reply_markup=reply_markup
    )
    return CHOOSING

def show_hike_calendar(update, context):
    """Show upcoming hikes in a calendar view"""
    if isinstance(update, CallbackQuery):
        query = update
        user_id = query.from_user.id
    else:
        user_id = update.message.from_user.id
        query = None
    
    # Get all available hikes, including those the user is already registered for
    # and show them in a calendar view
    hikes = DBUtils.get_available_hikes(include_inactive=False, include_registered=True)
    
    if not hikes:
        keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "There are no upcoming hikes in the calendar."
        if query:
            query.edit_message_text(message, reply_markup=reply_markup)
        else:
            update.message.reply_text(message, reply_markup=reply_markup)
        return CHOOSING
    
    # Group hikes by month
    hikes_by_month = {}
    for hike in hikes:
        hike_date = datetime.strptime(hike['hike_date'], '%Y-%m-%d')
        month_key = hike_date.strftime('%B %Y')  # "January 2023"
        
        if month_key not in hikes_by_month:
            hikes_by_month[month_key] = []
        
        hikes_by_month[month_key].append(hike)
    
    # Format the calendar message
    calendar_message = "📅 *Upcoming Hikes Calendar*\n\n"
    
    for month, month_hikes in sorted(hikes_by_month.items(), key=lambda x: datetime.strptime(x[0], '%B %Y')):
        calendar_message += f"*{month}*\n"
        
        # Sort hikes by date within the month
        month_hikes.sort(key=lambda x: x['hike_date'])
        
        for hike in month_hikes:
            hike_date = datetime.strptime(hike['hike_date'], '%Y-%m-%d')
            day_name = hike_date.strftime('%A')  # Get day name (Monday, Tuesday, etc.)
            date_str = hike_date.strftime('%d/%m')  # Format as day/month
            
            # Check if spots are available
            spots_left = hike['max_participants'] - hike['current_participants']
            if spots_left > 0:
                status = f"🟢 {spots_left} spots left"
            else:
                status = "⚫ Fully booked"
            
            # Add difficulty if available
            difficulty = f" - {hike['difficulty']}" if hike.get('difficulty') else ""
            
            calendar_message += f"• {day_name} {date_str}: {hike['hike_name']}{difficulty} ({status})\n"
        
        calendar_message += "\n"
    
    # Add back button
    keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the message
    if query:
        query.edit_message_text(
            text=calendar_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(
            text=calendar_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    return CHOOSING

def handle_cancel_confirmation(update, context):
    """Handle confirmation of hike cancellation"""
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    if query.data == 'abort_cancel':
        return show_hike_details(query, context)
        
    hike_to_cancel = context.user_data['hike_to_cancel']
    user_id = query.from_user.id
    
    # Cancel registration in database
    result = DBUtils.cancel_registration(user_id, hike_to_cancel['registration_id'])

    keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if result['success']:
        query.edit_message_text(
            "✅ Registration successfully cancelled.",
            reply_markup=reply_markup
        )
    else:
        query.edit_message_text(
            f"❌ Could not cancel registration: {result.get('error', 'Unknown error')}.",
            reply_markup=reply_markup
        )
        
    return CHOOSING

# Registration form handlers
def save_name(update, context):
    """Save name from user input"""
    context.chat_data['last_state'] = NAME
    context.user_data['name_surname'] = update.message.text
    update.message.reply_text("📧 Email?")
    return EMAIL

def save_email(update, context):
    """Save email from user input"""
    context.chat_data['last_state'] = EMAIL
    context.user_data['email'] = update.message.text
    update.message.reply_text("📱 Phone number (with international prefix)?")
    return PHONE

def save_phone(update, context):
    """Save phone number from user input"""
    context.chat_data['last_state'] = PHONE
    context.user_data['phone'] = update.message.text
    update.message.reply_text(
        "📅 Select the decade of your birth year:",
        reply_markup=create_year_selector()
    )
    return BIRTH_DATE

def create_year_selector():
    """Create keyboard for selecting birth year decade"""
    current_year = date.today().year
    current_month = date.today().month
    current_day = date.today().day

    keyboard = []
    decades = list(range(1980, (current_year - 18) + 1, 10))
    for i in range(0, len(decades), 2):
        row = []
        for year in decades[i:i+2]:
            row.append(InlineKeyboardButton(
                f"{year}s",
                callback_data=f'decade_{year}'
            ))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def create_year_buttons(decade):
    """Create keyboard for selecting specific year within decade"""
    keyboard = []
    current_year = date.today().year
    end_year = min(decade + 10, current_year - 18 + 1)
    years = list(range(decade, end_year))
    for i in range(0, len(years), 3):
        row = []
        for year in years[i:i+3]:
            row.append(InlineKeyboardButton(
                str(year),
                callback_data=f'year_{year}'
            ))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def create_month_buttons(year):
    """Create keyboard for selecting birth month"""
    keyboard = []
    current_date = date.today()
    limit_date = date(current_date.year - 18, current_date.month, current_date.day)

    if year == limit_date.year:
        max_month = limit_date.month
    else:
        max_month = 12

    for i in range(1, max_month + 1, 3):
        row = []
        for month in range(i, min(i + 3, max_month + 1)):
            row.append(InlineKeyboardButton(
                month_name[month],
                callback_data=f'month_{year}_{month}'
            ))
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)

def create_calendar(year, month):
    """Create calendar for selecting birth day"""
    keyboard = []
    current_date = date.today()
    limit_date = date(current_date.year - 18, current_date.month, current_date.day)

    keyboard.append([
        InlineKeyboardButton("<<", callback_data=f'year_{year-1}_{month}'),
        InlineKeyboardButton(f"{year}", callback_data=f'ignore'),
        InlineKeyboardButton(">>", callback_data=f'year_{year+1}_{month}')
    ])

    keyboard.append([
        InlineKeyboardButton("<<", callback_data=f'month_{year}_{month-1}'),
        InlineKeyboardButton(f"{month_name[month]}", callback_data=f'ignore'),
        InlineKeyboardButton(">>", callback_data=f'month_{year}_{month+1}')
    ])

    keyboard.append([
        InlineKeyboardButton(day, callback_data='ignore')
        for day in ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
    ])

    for week in monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data='ignore'))
            else:
                selected_date = date(year, month, day)
                if selected_date <= limit_date:
                    row.append(InlineKeyboardButton(
                        str(day),
                        callback_data=f'date_{year}_{month}_{day}'
                    ))
                else:
                    row.append(InlineKeyboardButton(" ", callback_data='ignore'))
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)

def handle_calendar(update, context):
    """Handle date selection from calendar"""
    context.chat_data['last_state'] = BIRTH_DATE
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    data = query.data.split('_')
    action = data[0]
    
    if action == 'decade':
        decade = int(data[1])
        query.edit_message_text(
            "📅 Select your birth year:",
            reply_markup=create_year_buttons(decade)
        )
        return BIRTH_DATE
        
    elif action == 'year':
        year = int(data[1])
        context.user_data['birth_year'] = year
        query.edit_message_text(
            "📅 Select birth month:",
            reply_markup=create_month_buttons(year)
        )
        return BIRTH_DATE
        
    elif action == 'month':
        year = int(data[1])
        month = int(data[2])
        query.edit_message_text(
            "📅 Select birth day:",
            reply_markup=create_calendar(year, month)
        )
        return BIRTH_DATE
        
    elif action == 'date':
        year = int(data[1])
        month = int(data[2])
        day = int(data[3])
        
        selected_date = f"{day:02d}/{month:02d}/{year}"
        context.user_data['birth_date'] = selected_date
        
        query.edit_message_text(f"📅 Selected birth date: {selected_date}")
        
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🏥 Medical conditions\n"
                 "_Do you have any medical conditions that might create difficulties for you "
                 "(Knee pain, cardiopathy, allergies etc.)?_",
            parse_mode='Markdown'
        )
        return MEDICAL
        
    return BIRTH_DATE

def save_medical(update, context):
    """Save medical conditions from user input"""
    context.chat_data['last_state'] = MEDICAL
    context.user_data['medical_conditions'] = update.message.text
    context.user_data['selected_hikes'] = []
    
    # Get available hikes
    available_hikes = context.user_data['available_hikes']
    reply_markup = KeyboardBuilder.create_hikes_selection_keyboard(available_hikes)
    
    update.message.reply_text(
        "🎯 Choose the hike(s) you want to participate in:\n\n"
        "🟢 Many spots available\n"
        "🔴 Last spot available\n"
        "⚫ Fully booked\n\n"
        "_Click on the hike name to select/deselect._\n"
        "_Click '✅ Confirm selection' when done._",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return HIKE_CHOICE

def handle_hike(update, context):
    """Handle hike selection"""
    context.chat_data['last_state'] = HIKE_CHOICE
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    # Ignore clicks on info rows and separators
    if query.data == 'ignore':
        return HIKE_CHOICE
        
    if query.data.startswith('info_hike'):
        # For clicks on date, show info message
        hike_idx = int(query.data.split('_')[1].replace('hike', ''))
        hike = context.user_data['available_hikes'][hike_idx]
        available_spots = hike['max_participants'] - hike['current_participants']
        
        if available_spots > 0:
            query.answer(
                f"Click on the hike name below to select/deselect",
                show_alert=False
            )
        else:
            query.answer(
                "This hike is fully booked",
                show_alert=True
            )
        return HIKE_CHOICE
        
    if query.data.startswith('select_hike'):
        hike_idx = int(query.data.replace('select_hike', ''))
        selected_hikes = context.user_data.get('selected_hikes', [])
        available_hikes = context.user_data['available_hikes']
        
        # Check if spots are still available
        hike = available_hikes[hike_idx]
        available_spots = hike['max_participants'] - hike['current_participants']
        
        if available_spots <= 0:
            query.answer("This hike is fully booked", show_alert=True)
            return HIKE_CHOICE
            
        if hike_idx in selected_hikes:
            selected_hikes.remove(hike_idx)
            query.answer("Hike deselected")
        else:
            selected_hikes.append(hike_idx)
            query.answer("Hike selected")
            
        context.user_data['selected_hikes'] = selected_hikes
        
        # Update keyboard with new selections
        reply_markup = KeyboardBuilder.create_hikes_selection_keyboard(
            available_hikes, 
            selected_hikes
        )
        query.edit_message_reply_markup(reply_markup=reply_markup)
        return HIKE_CHOICE
        
    elif query.data == 'confirm_hikes':
        selected_hikes = context.user_data.get('selected_hikes', [])
        if not selected_hikes:
            query.answer("❗ Please select at least one hike!", show_alert=True)
            return HIKE_CHOICE
            
        # Store selected hikes details
        available_hikes = context.user_data['available_hikes']
        context.user_data['selected_hikes_details'] = [
            available_hikes[idx] for idx in selected_hikes
        ]
        
        # Next question
        keyboard = [
            [
                InlineKeyboardButton("Yes ✅", callback_data='yes_eq'),
                InlineKeyboardButton("No ❌", callback_data='no_eq')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🎒 Do you have all the necessary equipment?\n"
                 "_You can find the required equipment on the hike webpage.\n"
                 "Remember, you could be excluded on the day of the event if you do not "
                 "meet the required equipment standards._",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return EQUIPMENT
        
    return HIKE_CHOICE

def handle_equipment(update, context):
    """Handle equipment question response"""
    context.chat_data['last_state'] = EQUIPMENT
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    context.user_data['has_equipment'] = True if query.data == 'yes_eq' else False
    
    reply_markup = KeyboardBuilder.create_car_share_keyboard()
    
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="🚗 Do you have a car you can share?\n"
             "_Don't worry, we will share tolls and fuel. Let us know seats number "
             "in the notes section at the bottom of the form._",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return CAR_SHARE

def handle_car_share(update, context):
    """Handle car sharing question response"""
    context.chat_data['last_state'] = CAR_SHARE
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    context.user_data['car_sharing'] = True if query.data == 'yes_car' else False
    
    # Start location selection process
    reply_markup = KeyboardBuilder.create_location_keyboard()
    
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="📍 What is your starting point?\n"
             "_This information helps us organize transport and meeting points_",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return LOCATION_CHOICE

def handle_location_choice(update, context):
    """Handle location choice response"""
    query = update.callback_query
    query.answer()
    
    if query.data == 'outside_rome':
        query.edit_message_text(
            "🌍 Please specify your location (e.g., Frascati, Tivoli, etc.):"
        )
        return CUSTOM_QUARTIERE
        
    # Create keyboard for municipi
    reply_markup = KeyboardBuilder.create_municipi_keyboard(municipi_data.keys())
    
    query.edit_message_text(
        "🏛 Select your municipio:",
        reply_markup=reply_markup
    )
    return QUARTIERE_CHOICE

def handle_quartiere_choice(update, context):
    """Handle municipio selection"""
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    municipio = query.data.replace('mun_', '')
    context.user_data['selected_municipio'] = municipio
    
    quartieri = municipi_data[municipio]
    reply_markup = KeyboardBuilder.create_quartiere_keyboard(quartieri)
    
    query.edit_message_text(
        f"🏘 Select your area in Municipio {municipio}:",
        reply_markup=reply_markup
    )
    return FINAL_LOCATION

def handle_final_location(update, context):
    """Handle quartiere selection"""
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    if query.data == 'back_municipi':
        return handle_location_choice(update, context)
        
    if query.data == 'other_area':
        query.edit_message_text("📍 Please specify your area in this municipio:")
        return CUSTOM_QUARTIERE
        
    quartiere = query.data.replace('q_', '')
    municipio = context.user_data['selected_municipio']
    location = f"Municipio {municipio} - {quartiere}"
    context.user_data['location'] = location
    
    return handle_reminder_preferences(update, context)

def handle_custom_location(update, context):
    """Handle custom location input"""
    context.chat_data['last_state'] = CUSTOM_QUARTIERE
    
    if 'selected_municipio' in context.user_data:
        # Custom area in a municipio
        municipio = context.user_data['selected_municipio']
        location = f"Municipio {municipio} - {update.message.text}"
    else:
        # Location outside Rome
        location = f"Outside Rome - {update.message.text}"
        
    context.user_data['location'] = location
    
    # Create and send reminder panel
    reply_markup = KeyboardBuilder.create_reminder_keyboard()
    
    update.message.reply_text(
        "⏰ Would you like to receive reminders before the hike?\n"
        "_Choose your preferred reminder option:_",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return REMINDER_CHOICE

def handle_reminder_preferences(update, context):
    """Send reminder preference selection"""
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    reply_markup = KeyboardBuilder.create_reminder_keyboard()
    
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="⏰ Would you like to receive reminders before the hike?\n"
             "_Choose your preferred reminder option:_",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return REMINDER_CHOICE

def save_reminder_preference(update, context):
    """Handle reminder preference selection"""
    context.chat_data['last_state'] = REMINDER_CHOICE
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    reminder_choice = query.data.replace('reminder_', '')
    reminder_mapping = {
        '5': '5 days',
        '2': '2 days',
        'both': '5 and 2 days',
        'none': 'No reminders'
    }
    context.user_data['reminder_preference'] = reminder_mapping[reminder_choice]
    
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="📝 Something important we need to know?\n"
             "_Whatever you want to tell us. If you share the car, remember the number of available seats._",
        parse_mode='Markdown'
    )
    return NOTES

def save_notes(update, context):
    """Save additional notes from user"""
    context.chat_data['last_state'] = NOTES
    context.user_data['notes'] = update.message.text
    
    reply_markup = KeyboardBuilder.create_final_notes_keyboard()
    
    update.message.reply_text(
        "⚠️ *IMPORTANT NOTES*\n"
        "Please note that you may be excluded from the event if all available spots are taken.\n"
        "Additionally, you could be excluded on the day of the event if you do not meet the required equipment standards.\n"
        "It's essential to ensure you have all necessary gear to participate in the hike safely.\n"
        "For any information, please contact us at hikingsrome@gmail.com",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return IMPORTANT_NOTES

def handle_final_choice(update, context):
    """Handle final confirmation of registration"""
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    if query.data == 'accept':
        # Check if selected hikes are still available
        selected_hikes = context.user_data.get('selected_hikes_details', [])
        user_id = query.from_user.id
        
        # Validate and save each hike registration
        success_count = 0
        error_messages = []
        
        for hike in selected_hikes:
            # Prepare registration data
            registration_data = {
                'name_surname': context.user_data.get('name_surname', ''),
                'email': context.user_data.get('email', ''),
                'phone': context.user_data.get('phone', ''),
                'birth_date': context.user_data.get('birth_date', ''),
                'medical_conditions': context.user_data.get('medical_conditions', ''),
                'has_equipment': context.user_data.get('has_equipment', False),
                'car_sharing': context.user_data.get('car_sharing', False),
                'location': context.user_data.get('location', ''),
                'notes': context.user_data.get('notes', ''),
                'reminder_preference': context.user_data.get('reminder_preference', 'No reminders')
            }
            
            # Add registration to database
            result = DBUtils.add_registration(user_id, hike['id'], registration_data)
            
            if result['success']:
                success_count += 1
            else:
                error_messages.append(f"Hike '{hike['hike_name']}': {result['error']}")
        
        # Display results
        keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if success_count == len(selected_hikes):
            query.edit_message_text(
                "✅ Thanks for signing up for the hike(s).",
                reply_markup=reply_markup
            )
        elif success_count > 0:
            # Some registrations succeeded, some failed
            query.edit_message_text(
                f"✅ {success_count} out of {len(selected_hikes)} registrations were successful.\n\n"
                f"The following errors occurred:\n"
                f"{', '.join(error_messages)}",
                reply_markup=reply_markup
            )
        else:
            # All registrations failed
            query.edit_message_text(
                f"❌ Registration failed for all selected hikes.\n\n"
                f"Errors:\n"
                f"{', '.join(error_messages)}",
                reply_markup=reply_markup
            )
    else:
        keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "❌ We are sorry but accepting these rules is necessary to participate in the walks.\n"
            "Thank you for your time.",
            reply_markup=reply_markup
        )
        
    return CHOOSING

def cancel(update, context):
    """Handle /cancel command"""
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        '❌ Operation cancelled.',
        reply_markup=reply_markup
    )
    return CHOOSING

def handle_invalid_message(update, context):
    """Handle invalid or unexpected messages"""
    if not check_user_membership(update, context):
        return handle_non_member(update, context)
        
    # States where the user is not filling out a form
    non_form_states = [None, CHOOSING, PRIVACY_CONSENT, IMPORTANT_NOTES, ADMIN_MENU]
    
    if context.chat_data.get('last_state') in non_form_states:
        update.message.reply_text(
            "⚠️ If you need to access the menu, use the /menu command."
        )
        return ConversationHandler.END
    else:
        reply_markup = KeyboardBuilder.create_yes_no_keyboard('restart_yes', 'restart_no')
        update.message.reply_text(
            "❓ Do you want to start a new form?",
            reply_markup=reply_markup
        )
        return context.chat_data.get('last_state')

def handle_restart_choice(update, context):
    """Handle choice to restart or continue"""
    query = update.callback_query
    
    try:
        query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e) or "Message is not modified" in str(e):
            return handle_lost_conversation(update, context)
        raise
        
    if query.data == 'restart_yes':
        context.user_data.clear()
        query.message.reply_text("👋 Name and surname?")
        return NAME
    else:
        query.edit_message_text(
            "ℹ️ If you need help, send a message in the telegram group or send an email to hikingsrome@gmail.com"
        )
        return ConversationHandler.END

def check_and_send_reminders(context):
    """Check for reminders to send"""
    try:
        # Check for reminders 5 days before hike
        reminders_5_days = DBUtils.get_users_for_reminder(5)
        for reminder in reminders_5_days:
            send_reminder(context, reminder, 5)
            
        # Check for reminders 2 days before hike
        reminders_2_days = DBUtils.get_users_for_reminder(2)
        for reminder in reminders_2_days:
            send_reminder(context, reminder, 2)
            
    except Exception as e:
        logger.error(f"Error checking reminders: {e}")

def send_reminder(context, reminder_data, days_before):
    """Send a reminder to a specific user"""
    try:
        weather_api = os.environ.get('OPENWEATHER_API_KEY')
        telegram_id = reminder_data['telegram_id']
        hike_name = reminder_data['hike_name']
        
        # Format date for display
        if isinstance(reminder_data['hike_date'], str):
            hike_date = datetime.strptime(reminder_data['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
        else:
            hike_date = reminder_data['hike_date'].strftime('%d/%m/%Y')
        
        # Get weather forecast if API key is available
        weather_msg = ""
        if weather_api and reminder_data.get('latitude') and reminder_data.get('longitude'):
            weather = WeatherUtils.get_weather_forecast(
                reminder_data['latitude'],
                reminder_data['longitude'],
                reminder_data['hike_date'],
                weather_api
            )
            
            if weather:
                weather_msg = WeatherUtils.format_weather_message(weather, days_before)
                
        # Build and send reminder message
        message = (
            f"⏰ *Reminder*: You have an upcoming hike!\n\n"
            f"🗓 *Date:* {hike_date}\n"
            f"🏃 *Hike:* {hike_name}\n\n"
            f"{weather_msg}\n\n"
            f"_Remember to check the required equipment and be prepared!_"
        )
        
        context.bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")

def cleanup(updater=None):
    """Cleanup function to be called on exit"""
    try:
        if updater:
            updater.stop()
            logger.info("Bot stopped")
    except:
        pass

def main():
    """Main function to run the bot"""
    # Load environment variables
    TOKEN = os.environ.get('TELEGRAM_TOKEN')
    if not TOKEN:
        logger.error("No TELEGRAM_TOKEN provided in environment variables")
        sys.exit(1)
        
    # Setup request parameters
    request_kwargs = {
        'read_timeout': 6,
        'connect_timeout': 7,
    }
    
    # Create updater and dispatcher
    updater = Updater(
        TOKEN,
        use_context=True,
        request_kwargs=request_kwargs
    )
    
    # Register cleanup function
    atexit.register(lambda: cleanup(updater))
    
    dp = updater.dispatcher
    check_telegram_stars_availability(updater.bot)
    # Setup rate limiter
    rate_limiter = RateLimiter(max_requests=5, time_window=60)  # 5 requests per minute
    dp.bot_data['rate_limiter'] = rate_limiter
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('menu', menu),
            CommandHandler('start', menu),
            CommandHandler('restart', restart),
            CommandHandler('admin', cmd_admin),
            CallbackQueryHandler(handle_restart_choice, pattern='^restart_'),
            CommandHandler('privacy', cmd_privacy),
            CommandHandler('bug', cmd_bug)
        ],
        states={
            CHOOSING: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CommandHandler('admin', cmd_admin),
                CallbackQueryHandler(handle_menu_choice, pattern='^(personal_profile|manage_hikes|signup|myhikes|calendar|links|donation|back_to_menu|admin_menu)$'),
                CallbackQueryHandler(handle_hike_navigation, pattern='^(prev_hike|next_hike)$'),
                CallbackQueryHandler(handle_cancel_request, pattern='^cancel_hike_\\d+$'),
                CallbackQueryHandler(handle_cancel_confirmation, pattern='^(confirm_cancel|abort_cancel)$'),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$')
            ],
            DONATION: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_donation, pattern='^donation_'),
                CallbackQueryHandler(menu, pattern='^back_to_menu$')
            ],
            PROFILE_MENU: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_profile_choice, pattern='^(view_profile|edit_profile|back_to_profile|back_to_menu)$')
            ],
            PROFILE_EDIT: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(edit_profile_field, pattern='^edit_'),
                CallbackQueryHandler(handle_save_profile, pattern='^save_profile$'),
                CallbackQueryHandler(show_profile_menu, pattern='^back_to_profile$'),
                CallbackQueryHandler(menu, pattern='^back_to_menu$')
            ],
            PROFILE_NAME: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, save_profile_name)
            ],
            PROFILE_SURNAME: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, save_profile_surname)
            ],
            PROFILE_EMAIL: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, save_profile_email)
            ],
            PROFILE_PHONE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, save_profile_phone)
            ],
            PROFILE_BIRTH_DATE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_profile_birth_date)
            ],            
            ADMIN_MENU: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CommandHandler('admin', cmd_admin),
                CallbackQueryHandler(handle_admin_choice, pattern='^admin_'),
                CallbackQueryHandler(show_maintenance_menu, pattern='^admin_maintenance$'),
                CallbackQueryHandler(handle_admin_choice, pattern='^confirm_cancel_hike_'),
                CallbackQueryHandler(handle_admin_choice, pattern='^confirm_reactivate_hike_'),
                CallbackQueryHandler(show_query_db_menu, pattern='^query_db$'),
                CallbackQueryHandler(handle_admin_choice, pattern='^back_to_admin$'),
                CallbackQueryHandler(menu, pattern='^back_to_menu$')
            ],
            ADMIN_HIKE_NAME: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, admin_save_hike_name)
            ],
            ADMIN_HIKE_DATE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, admin_save_hike_date)
            ],
            ADMIN_HIKE_GUIDES: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, admin_save_guides)
            ],
            ADMIN_HIKE_MAX_PARTICIPANTS: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, admin_save_max_participants)
            ],
            ADMIN_HIKE_LOCATION: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, admin_save_location)
            ],
            ADMIN_HIKE_DIFFICULTY: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(admin_save_difficulty, pattern='^difficulty_')
            ],
            ADMIN_HIKE_DESCRIPTION: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_costs_verification, pattern='^(costs_verified|update_costs)$'),
                MessageHandler(Filters.text & ~Filters.command, admin_save_description)
            ],
            ADMIN_CONFIRM_HIKE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(admin_confirm_hike, pattern='^(confirm_create_hike|cancel_create_hike)$')
            ],
            ADMIN_COSTS: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(start_cost_creation, pattern='^add_cost$'),
                CallbackQueryHandler(show_cost_summary, pattern='^cost_summary$'),
                CallbackQueryHandler(handle_cost_selection, pattern='^edit_cost_\\d+$'),
                CallbackQueryHandler(handle_cost_action, pattern='^cost_'),
                CallbackQueryHandler(update_cost_frequency, pattern='^frequency_'),
                CallbackQueryHandler(delete_cost, pattern='^confirm_delete_cost_\\d+$'),
                CallbackQueryHandler(handle_admin_choice, pattern='^back_to_admin$'),
                CallbackQueryHandler(handle_admin_choice, pattern='^admin_costs$'),
                CallbackQueryHandler(menu, pattern='^back_to_menu$')
            ],
            COST_NAME: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CommandHandler('cancel', lambda u, c: show_cost_control_menu(u, c)),
                MessageHandler(Filters.text & ~Filters.command, 
                              lambda u, c: update_cost_name(u, c) if 'editing_cost_id' in c.user_data 
                                         else save_cost_name(u, c))
            ],
            COST_AMOUNT: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CommandHandler('cancel', lambda u, c: show_cost_control_menu(u, c)),
                MessageHandler(Filters.text & ~Filters.command, 
                              lambda u, c: update_cost_amount(u, c) if 'editing_cost_id' in c.user_data 
                                         else save_cost_amount(u, c))
            ],
            COST_FREQUENCY: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CommandHandler('cancel', lambda u, c: show_cost_control_menu(u, c)),
                CallbackQueryHandler(update_cost_frequency, pattern='^frequency_'),
                CallbackQueryHandler(save_cost_frequency, pattern='^new_frequency_')
            ],
            COST_DESCRIPTION: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CommandHandler('cancel', lambda u, c: show_cost_control_menu(u, c)),
                CommandHandler('skip', 
                              lambda u, c: skip_cost_description_update(u, c) if 'editing_cost_id' in c.user_data 
                                         else skip_cost_description(u, c)),
                MessageHandler(Filters.text & ~Filters.command, 
                              lambda u, c: update_cost_description(u, c) if 'editing_cost_id' in c.user_data 
                                         else save_cost_description(u, c))
            ], 
            ADMIN_ADD_ADMIN: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, add_admin_handler)
            ],
            ADMIN_MAINTENANCE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(start_maintenance_creation, pattern='^add_maintenance$'),
                CallbackQueryHandler(handle_maintenance_selection, pattern='^edit_maintenance_\\d+$'),
                CallbackQueryHandler(handle_maintenance_action, pattern='^maintenance_'),
                CallbackQueryHandler(delete_maintenance_schedule, pattern='^confirm_delete_maintenance_\\d+$'),
                CallbackQueryHandler(show_maintenance_menu, pattern='^admin_maintenance$'),
                CallbackQueryHandler(handle_admin_choice, pattern='^back_to_admin$'),
                CallbackQueryHandler(menu, pattern='^back_to_menu$')
            ],
            ADMIN_QUERY_DB: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CommandHandler('cancel', lambda u, c: show_query_db_menu(u, c)),
                CallbackQueryHandler(show_query_db_menu, pattern='^query_db$'),
                CallbackQueryHandler(show_predefined_queries_menu, pattern='^predefined_queries$'),
                CallbackQueryHandler(handle_predefined_query, pattern='^query_(tables|users|hikes|custom_.+)$'),
                CallbackQueryHandler(handle_custom_query_request, pattern='^query_custom$'),
                CallbackQueryHandler(start_save_query, pattern='^(query_save|save_last_query)$'),
                CallbackQueryHandler(start_delete_query, pattern='^query_delete$'),
                CallbackQueryHandler(confirm_delete_query, pattern='^delete_query_.+$'),
                CallbackQueryHandler(delete_confirmed_query, pattern='^confirm_delete_.+$'),
                CallbackQueryHandler(handle_query_overwrite, pattern='^(confirm_overwrite_.+|change_query_name)$'),
                CallbackQueryHandler(handle_admin_choice, pattern='^back_to_admin$'),
                CallbackQueryHandler(menu, pattern='^back_to_menu$')
            ],
            ADMIN_QUERY_EXECUTE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CommandHandler('cancel', lambda u, c: show_query_db_menu(u, c)),
                CallbackQueryHandler(show_query_db_menu, pattern='^query_db$'),
                CallbackQueryHandler(show_predefined_queries_menu, pattern='^cancel_query$'),
                MessageHandler(Filters.text & ~Filters.command, execute_custom_query)
            ],
            ADMIN_QUERY_SAVE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(show_predefined_queries_menu, pattern='^predefined_queries$'),
                MessageHandler(Filters.text & ~Filters.command, save_query_text)
            ],
            ADMIN_QUERY_NAME: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(show_predefined_queries_menu, pattern='^predefined_queries$'),
                MessageHandler(Filters.text & ~Filters.command, save_query_name)
            ],
            ADMIN_QUERY_DELETE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CommandHandler('cancel', lambda u, c: show_predefined_queries_menu(u, c)),
                CallbackQueryHandler(show_predefined_queries_menu, pattern='^predefined_queries$'),
                CallbackQueryHandler(confirm_delete_query, pattern='^delete_query_.+$'),
                CallbackQueryHandler(delete_confirmed_query, pattern='^confirm_delete_.+$'),
                CallbackQueryHandler(show_query_db_menu, pattern='^query_db$'),
                CallbackQueryHandler(handle_admin_choice, pattern='^back_to_admin$'),
                CallbackQueryHandler(menu, pattern='^back_to_menu$')
            ],
            MAINTENANCE_DATE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, 
                              lambda u, c: update_maintenance_date(u, c) if 'editing_maintenance_id' in c.user_data 
                                         else save_maintenance_date(u, c))
            ],
            MAINTENANCE_START_TIME: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, 
                              lambda u, c: update_maintenance_time(u, c) if 'editing_maintenance_id' in c.user_data and 'new_maintenance_start' not in c.user_data 
                                         else save_maintenance_start_time(u, c))
            ],
            MAINTENANCE_END_TIME: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                MessageHandler(Filters.text & ~Filters.command, 
                              lambda u, c: update_maintenance_end_time(u, c) if 'editing_maintenance_id' in c.user_data and 'new_maintenance_start' in c.user_data 
                                         else save_maintenance_end_time(u, c))
            ],
            MAINTENANCE_REASON: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CommandHandler('skip', 
                              lambda u, c: skip_update_reason(u, c) if 'editing_maintenance_id' in c.user_data 
                                         else skip_maintenance_reason(u, c)),
                MessageHandler(Filters.text & ~Filters.command, 
                              lambda u, c: update_maintenance_reason(u, c) if 'editing_maintenance_id' in c.user_data 
                                         else save_maintenance_reason(u, c))
            ],            
            PRIVACY_CONSENT: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CommandHandler('privacy', cmd_privacy),
                CallbackQueryHandler(handle_privacy_choices, pattern='^privacy_'),
                CallbackQueryHandler(handle_menu_choice, pattern='^back_to_menu$')
            ],
            NAME: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                MessageHandler(Filters.text & ~Filters.command, save_name)
            ],
            EMAIL: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                MessageHandler(Filters.text & ~Filters.command, save_email)
            ],
            PHONE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                MessageHandler(Filters.text & ~Filters.command, save_phone)
            ],
            BIRTH_DATE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_calendar)
            ],
            MEDICAL: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                MessageHandler(Filters.text & ~Filters.command, save_medical)
            ],
            HIKE_CHOICE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_profile_confirmation, pattern='^(confirm_profile_yes|confirm_profile_no|update_profile_first|continue_with_form)$'),
                CallbackQueryHandler(handle_hike)
            ],
            EQUIPMENT: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_equipment)
            ],
            CAR_SHARE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_car_share)
            ],
            LOCATION_CHOICE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_location_choice)
            ],
            QUARTIERE_CHOICE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_quartiere_choice)
            ],
            FINAL_LOCATION: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_final_location)
            ],
            CUSTOM_QUARTIERE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                MessageHandler(Filters.text & ~Filters.command, handle_custom_location)
            ],
            REMINDER_CHOICE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(save_reminder_preference, pattern='^reminder_')
            ],
            NOTES: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                MessageHandler(Filters.text & ~Filters.command, save_notes)
            ],
            IMPORTANT_NOTES: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_final_choice)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('restart', restart),
            MessageHandler(Filters.text & ~Filters.command, handle_invalid_message)
        ],
        allow_reentry=True
    )
    
    # Add job scheduler for reminders
    job_queue = updater.job_queue
    job_queue.run_daily(
        callback=check_and_send_reminders,
        time=datetime_time(hour=9, minute=0, tzinfo=rome_tz)  # Send reminders at 9:00 Rome time
    )
    # Check maintenance notification every 15 mins
    job_queue.run_daily(
        callback=check_and_send_maintenance_notifications,
        time=datetime_time(hour=9, minute=30, tzinfo=rome_tz)  # Send maintenance alert at 9:30 Rome time
    )
    
    # Register handlers
    # adds the main conversation manager
    dp.add_handler(conv_handler)
    # This handler catches the ‘back_to_menu’ callback which is not intercepted by the conversation handler
    dp.add_handler(CallbackQueryHandler(menu, pattern='^back_to_menu$'))
    # This is the error handler
    dp.add_error_handler(error_handler)
    # This handles the checkout stages of payment
    dp.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    # This handles successfully completed payments
    dp.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))
    # This is the test command for payments with Telegram Stars
    dp.add_handler(CommandHandler('test_stars', test_telegram_stars))
    
    # Start the bot
    try:
        updater.start_polling(
            drop_pending_updates=True,
            timeout=30,
            poll_interval=1.0,
            allowed_updates=['message', 'callback_query']
        )
        logger.info("Bot started! Press CTRL+C to stop.")
        
        check_and_send_maintenance_notifications(updater)
        
        updater.idle()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        try:
            # Try to restart polling in case of error
            time.sleep(5)
            updater.start_polling(
                drop_pending_updates=True,
                timeout=15,
                poll_interval=0.5,
                allowed_updates=['message', 'callback_query']
            )
            logger.info("Bot restarted after error!")
            updater.idle()
        except Exception as e:
            logger.error(f"Fatal error starting bot: {e}")
            raise

if __name__ == '__main__':
    main()
