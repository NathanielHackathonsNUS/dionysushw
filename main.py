from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    Filters,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
)
import logging, math, pytz, pandas as pd, parsedatetime as pdt
from datetime import datetime, time, timedelta

TOKEN = "YOUR_TOKEN"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation States for Registratoin, Teacher Menu and Student Menu
END = ConversationHandler.END

(REGISTER, REG_TEACHER_DETAILS, REG_TEACHER_CONFIRM, REG_STUDENT_CONFIRM) = range(4)

(
    TEACHER_MENU,
    TEACHER_HW_NAME,
    TEACHER_HW_DEADLINE,
    TEACHER_VIEWING,
    TEACHER_ADD_HW_RETURN,
) = range(4, 9)

(
    STUDENT_MENU,
    STUDENT_POMODORO_TASK,
    STUDENT_POMODORO_DURATION,
    STUDENT_POMODORO_IN_SESSION,
    STUDENT_COMPLETED_TASKS,
    STUDENT_VIEW_SUBJECT,
    STUDENT_VIEWING,
) = range(9, 16)

# Getting dataframes from CSV
users_csv = "users.csv"
users_df = pd.read_csv(users_csv, index_col=0)

hw_csv = "hw.csv"
hw_df = pd.read_csv(hw_csv, index_col=0)

# Helper Functions
def _format_pomodoro(pomodoros):
    """Receives a list of pomodoros and returns formatted text"""
    # Empty pomodoro list
    if not pomodoros:
        return "No tasks completed!"

    # Iterating through pomodoro list
    text = ""
    for pomodoro in pomodoros:
        text += (
            f"{str(pomodoro['task'])}:\n"
            f"{str(pomodoro['start_time'])} TO {str(pomodoro['end_time'])}\n\n"
        )

    return text


def _subject_buttons(subj_list):
    """Receives a list of subjects and returns a structured matrix of InlineKeyboardButtons"""
    buttons = []

    # Maximising number of buttons to 2 per row
    for count, subject in enumerate(subj_list):
        if not count % 2:
            buttons.append([])
        subject = subject.capitalize()
        callback = subject.lower()
        buttons[math.floor(count / 2)].append(
            InlineKeyboardButton(subject, callback_data=callback)
        )

    # Adding standalone back button
    buttons.append([InlineKeyboardButton("Back", callback_data="back_student_menu")])

    return buttons


# Registration Conversation
def start(update, context):
    """Entry point for all new users. Registers them as teacher or student user type."""
    global users_df

    # Checking if user already has a type
    chat_id = update.effective_chat.id
    index = users_df[users_df["chat_id"] == chat_id].index
    user_type = users_df.loc[index, "user_type"].to_string(index=False)

    # Filtering out users new and unregistered users
    if user_type == "student" or user_type == "teacher":
        buttons = [[InlineKeyboardButton(f"Click to return.", callback_data="cancel")]]
        keyboard = InlineKeyboardMarkup(buttons)
        text = f"You have already been as a {user_type}.\nReturn and type /{user_type} to begin."

        update.message.reply_text(text)
        return END

    # Prompting new user type inputs
    else:
        buttons = [
            [
                InlineKeyboardButton("Teacher", callback_data="reg_teacher"),
                InlineKeyboardButton("Student", callback_data="reg_student"),
            ],
            [InlineKeyboardButton("Cancel", callback_data="cancel")],
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        text = "Are you a teacher or a student?"

    if update.message:
        user_name = update.message.from_user.name
        chat_id = update.effective_chat.id
        update.message.reply_text(text, reply_markup=keyboard)

        # Saving new users to the dataframe
        if chat_id not in users_df["chat_id"].to_list():
            row = pd.Series(
                data={"chat_id": chat_id, "user_name": user_name}, name="row"
            )
            users_df = users_df.append(row, ignore_index=True)
            users_df.to_csv(users_csv)

    # User chose not to confirm their submission
    elif update.callback_query.data:
        user_data = context.user_data
        user_data.clear()

        query = update.callback_query

        user_name = query.from_user.name
        chat_id = query.chat_instance

        query.answer()
        query.edit_message_text(text, reply_markup=keyboard)

    return REGISTER


def reg_student_confirm(update, context):
    """Confirm student's registration"""
    buttons = [
        [
            InlineKeyboardButton(
                "Register as 'Student'", callback_data="student_confirm"
            )
        ],
        [InlineKeyboardButton("Back", callback_data="not_confirmed")],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "Are you sure? This choice cannot be changed.", reply_markup=keyboard
    )

    return REG_STUDENT_CONFIRM


def reg_student_final(update, context):
    """Saving students's confirmation details"""
    global users_df

    # Creating an initial empty pomodoros list for students
    user_data = context.user_data
    if "pomodoros" not in user_data.keys():
        user_data["pomodoros"] = []

    query = update.callback_query
    query.answer()

    # Saving student's details to users dataframe
    chat_id = update.effective_chat.id
    index = users_df[users_df["chat_id"] == chat_id].index

    users_df.loc[index, "user_type"] = "student"
    users_df.loc[index, "teacher_subject"] = "NaN"
    users_df.to_csv(users_csv)

    query.edit_message_text(
        "You have been successfully registered. Please input '/student' to proceed."
    )
    return END


def reg_teacher_details(update, context):
    """Prompt teacher for their subject"""
    query = update.callback_query
    query.answer()

    query.edit_message_text("Send the subject you're teaching. e.g. 'Physics'")
    return REG_TEACHER_DETAILS


def reg_teacher_confirm(update, context):
    """Confirm teacher's registration choice"""
    subject = update.message.text.capitalize()

    # Temporary storage for subject
    user_data = context.user_data
    user_data["teacher_subject"] = subject

    buttons = [
        [
            InlineKeyboardButton(
                f"Register as '{subject} Teacher'", callback_data="teacher_confirm"
            )
        ],
        [InlineKeyboardButton("Back", callback_data="not_confirmed")],
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    update.message.reply_text(
        "Are you sure? This choice cannot be changed.", reply_markup=keyboard
    )

    return REG_TEACHER_CONFIRM


def reg_teacher_final(update, context):
    """Saving teacher's confirmation details"""
    # Retrieving data from temporary storage
    user_data = context.user_data
    subject = user_data["teacher_subject"]

    # Saving teacher's details to users dataframe
    chat_id = update.effective_chat.id
    index = users_df[users_df["chat_id"] == chat_id].index

    users_df.loc[index, "user_type"] = "teacher"
    users_df.loc[index, "teacher_subject"] = subject
    users_df.to_csv(users_csv)

    query = update.callback_query
    query.answer()
    query.edit_message_text(
        f"You have been successfully registered as the {subject} teacher. Please input '/teacher' to proceed."
    )
    return END


# Teacher Conversation
def teacher(update, context):
    """Teacher Main Menu"""
    global users_df

    chat_id = update.effective_chat.id
    user_data = context.user_data
    user_data["chat_id"] = chat_id

    # Getting user's type
    index = users_df[users_df["chat_id"] == chat_id].index
    user_type = users_df.loc[index, "user_type"].to_string(index=False)

    # Rejecting students
    if user_type == "student":
        update.message.reply_text(
            "You are registered as a student! Did you mean to type /student?"
        )
        return END

    # Rejecting new users
    elif user_type != "teacher":
        update.message.reply_text("You have not registered yet! Send /start to begin.")
        return END

    buttons = [
        [
            InlineKeyboardButton("Add homework", callback_data="add_hw"),
            InlineKeyboardButton("View homework", callback_data="view_hw"),
        ],
        [InlineKeyboardButton("Cancel", callback_data="cancel")],
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    text = "Teacher's Menu"

    if update.message:
        update.message.reply_text(text, reply_markup=keyboard)

    elif update.callback_query:
        query = update.callback_query
        query.answer()
        query.edit_message_text(text, reply_markup=keyboard)

    return TEACHER_MENU


def teacher_add_hw_name(update, context):
    """Prompting for name of homework"""
    query = update.callback_query
    query.answer()
    query.edit_message_text("What is the name of the homework?")

    return TEACHER_HW_NAME


def teacher_add_hw_deadline(update, context):
    """Prompting for deadline and temporarily storing task name"""
    user_data = context.user_data
    user_data["task"] = update.message.text.replace(",", " ")
    user_data["chat_id"] = update.effective_chat.id

    update.message.reply_text(
        "What is the deadline of the homework?\n" "e.g. tomorrow, or 25 July"
    )

    return TEACHER_HW_DEADLINE


def teacher_add_hw_confirm(update, context):
    """Validating deadline input and confirming teacher's new homework details"""
    user_data = context.user_data
    task = user_data["task"]

    message = update.message

    # Getting date from string
    cal = pdt.Calendar()
    time_struct, parse_status = cal.parse(message.text)

    # parsedatetime was not able to get a date from the input
    if not parse_status:
        update.message.reply_text(
            "We didn't understand your input.\n\n"
            "What is the deadline of the homework?\n"
            "e.g. tomorrow, or 25 July"
        )
        return TEACHER_HW_DEADLINE

    deadline = datetime.date(datetime(*time_struct[:6]))

    # Checking if teacher tried to set deadline in the past
    if deadline < datetime.date(datetime.now()):
        update.message.reply_text(
            "Your students can't travel to the past.\n"
            "Please set a deadline for the future!\n\n"
            "What is the deadline of the homework?\n"
            "e.g. tomorrow, or 25 July"
        )
        return TEACHER_HW_DEADLINE

    str_deadline = deadline.strftime("%d/%m")
    user_data["deadline"] = deadline

    buttons = [
        [
            InlineKeyboardButton(
                f"Confirm {task} by {str_deadline}",
                callback_data="confirm_add_hw",
            )
        ],
        [
            InlineKeyboardButton(
                "Return to Teacher Main Menu",
                callback_data="back_teacher_menu",
            )
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    message.reply_text("Please confirm new homework task.", reply_markup=keyboard)
    return TEACHER_ADD_HW_RETURN


def teacher_add_hw_done(update, context):
    """Saves the new homework in the dataframe then returns to main menu"""
    global hw_df
    user_data = context.user_data

    # Homework details
    task = user_data["task"]
    deadline = user_data["deadline"]

    # Getting subject taught by user
    chat_id = user_data["chat_id"]
    index = users_df[users_df["chat_id"] == chat_id].index
    subj = users_df.loc[index, "teacher_subject"].to_string(index=False)

    # Adding to dataframe
    row = pd.Series(data={"subj": subj, "task": task, "deadline": deadline}, name="row")
    hw_df = hw_df.append(row, ignore_index=True)
    hw_df.to_csv(hw_csv)

    user_data.clear()

    return teacher(update, context)


def teacher_view_hw(update, context):
    """For teacher to view their list of homework"""
    query = update.callback_query
    query.answer()

    # Getting subject taught by user
    user_data = context.user_data
    chat_id = user_data["chat_id"]
    index = users_df[users_df["chat_id"] == chat_id].index
    subj = users_df.loc[index, "teacher_subject"].to_string(index=False)

    buttons = [
        [
            InlineKeyboardButton(
                "Return to Teacher Main Menu",
                callback_data="back_teacher_menu",
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # Taking part of the dataframe with only the related subjects
    subj_indices = hw_df[hw_df["subj"] == subj].index
    subj_df = hw_df.iloc[subj_indices]

    subj_df["deadline"] = pd.to_datetime(subj_df["deadline"])

    # Formatting string for list of homework
    text = f"Homework for {subj}\n\n"
    for row in subj_df.itertuples():
        task = getattr(row, "task")
        deadline = getattr(row, "deadline")
        deadline = deadline.strftime("%d %b %y")
        text += f"- {task} by {deadline}\n"

    # Default text for no homework
    text = "No homework yet for {subj}!" if text == f"Homework for {subj}\n\n" else text

    query.edit_message_text(text, reply_markup=keyboard)

    return TEACHER_VIEWING


# Student Conversation
def student(update, context):
    """Student Main Menu"""
    global users_df

    chat_id = update.effective_chat.id

    index = users_df[users_df["chat_id"] == chat_id].index
    user_type = users_df.loc[index, "user_type"].to_string(index=False)
    # Rejecting teachers
    if user_type == "teacher":
        update.message.reply_text(
            "You are registered as a teacher! Did you mean to type /teacher?"
        )
        return END

    # Rejecting new users
    elif user_type != "student":
        update.message.reply_text("You have not registered yet! Send /start to begin.")
        return END

    user_data = context.user_data

    # Creating another pomodoro list in case it was cleared prior
    if "pomodoros" not in user_data.keys():
        user_data["pomodoros"] = []

    buttons = [
        [
            InlineKeyboardButton("Pomodoro", callback_data="pomodoro"),
            InlineKeyboardButton("Homework", callback_data="homework"),
        ],
        [
            InlineKeyboardButton("Completed Tasks", callback_data="completed_tasks"),
            InlineKeyboardButton("Cancel", callback_data="cancel"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    if update.message:
        update.message.reply_text("Student's Menu", reply_markup=keyboard)
        return STUDENT_MENU

    query = update.callback_query
    query.answer()

    # Student was sent here to clear history
    if query.data == "clear_history":
        user_data["pomodoros"] = []

        query.edit_message_text(
            "History Cleared!\n\nStudent's Menu", reply_markup=keyboard
        )

    elif query.data == "back_student_menu":
        query.edit_message_text("Student's Menu", reply_markup=keyboard)

    return STUDENT_MENU


def student_pomodoro_init(update, context):
    """Prompting student for name/title of pomodoro"""
    query = update.callback_query
    query.answer()

    query.edit_message_text(
        "What is the name of your pomodoro session? e.g. Physics Homework"
    )
    return STUDENT_POMODORO_TASK


def student_pomodoro_duration(update, context):
    """Prompting user for duration of pomodoro then storing name/title"""
    message = update.message
    user_data = context.user_data

    task = message.text.capitalize()

    # Adding in a pomodoro
    if "pomodoros" not in user_data.keys():
        user_data["pomodoros"] = []

    user_data["pomodoros"].append(
        {
            "task": task,
            "start_time": datetime.now().strftime("%d/%m %I:%M %p"),
            "end_time": None,
            "duration": None,
        }
    )

    message.reply_text(
        "How long is your pomodoro session in minutes? (180 minutes maximum)"
    )

    return STUDENT_POMODORO_DURATION


def student_pomodoro_start(update, context):
    """Validating duration input then starting pomodoro session"""
    message = update.message
    duration = int(message.text)

    # Filtering out invalid duratioin input
    if duration < 0:
        message.reply_text(
            "Positive duration please!😀\n"
            "How long is your pomodoro session in minutes? (180 minutes maximum)"
        )
        return STUDENT_POMODORO_DURATION

    elif duration > 180:
        message.reply_text(
            "Please choose a duration less than 180 minutes!😀\n"
            "How long is your pomodoro session in minutes? (180 minutes maximum)"
        )
        return STUDENT_POMODORO_DURATION

    # Storing pomodoro information in user_data
    user_data = context.user_data
    user_data["pomodoros"][-1]["duration"] = duration
    user_data["pomodoros"][-1]["end_time"] = (
        datetime.now() + timedelta(minutes=duration)
    ).strftime("%d/%m %I:%M %p")
    task = user_data["pomodoros"][-1]["task"]
    end_time = user_data["pomodoros"][-1]["end_time"]
    plural = "" if duration == 1 else "s"
    update.message.reply_text(
        f"Pomodoro Session {task} for {duration} minute{plural} ending at {end_time}"
    )

    # Sending a scheduled message
    user_data["message_id"] = message.message_id
    context.job_queue.run_once(
        student_end_pomodoro, duration * 60, context=update.message.chat_id
    )
    return STUDENT_POMODORO_IN_SESSION


def student_pomodoro_in_session(update, context):
    """Sends a user a response if any update received during pomodoro session"""
    user_data = context.user_data
    end_time = user_data["pomodoros"][-1]["end_time"]
    update.message.reply_text(f"Please focus on your pomodoro task until {end_time}")
    return STUDENT_POMODORO_IN_SESSION


def student_end_pomodoro(context):
    """Informing user that session is done"""
    buttons = [
        [InlineKeyboardButton("Back to Menu", callback_data="back_student_menu")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    context.bot.send_message(
        chat_id=context.job.context,
        text=f"Pomdoro Session done!",
        reply_markup=keyboard,
    )
    return STUDENT_POMODORO_IN_SESSION


def student_completed_tasks(update, context):
    """Showing completed pomodoro tasks"""
    buttons = [
        [
            InlineKeyboardButton("Clear History", callback_data="clear_history"),
            InlineKeyboardButton("Back to Menu", callback_data="back_student_menu"),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    text = _format_pomodoro(context.user_data["pomodoros"])

    if update.message:
        update.message.reply_text(text, reply_markup=keyboard)

    elif update.callback_query:
        query = update.callback_query
        query.answer()
        query.edit_message_text(text, reply_markup=keyboard)

    return STUDENT_COMPLETED_TASKS


def student_view_subject(update, context):
    """Prompting for which of the subjects the users would want to view"""
    query = update.callback_query
    query.answer()

    # Taking all the unique subjects in the homework dataframe
    subj_list = hw_df["subj"].unique().tolist()
    buttons = _subject_buttons(subj_list)

    keyboard = InlineKeyboardMarkup(buttons)

    query.edit_message_text("Which subject do you wish to view", reply_markup=keyboard)
    return STUDENT_VIEW_SUBJECT


def student_view_homework(update, context):
    """Showing students the subject-specific task"""
    query = update.callback_query
    query.answer()

    subj = query.data.capitalize()

    subj_indices = hw_df[hw_df["subj"] == subj].index
    subj_df = hw_df.iloc[subj_indices]

    # Text formatting for homework list
    subj_df["deadline"] = pd.to_datetime(subj_df["deadline"])
    text = f"Homework for {subj}\n\n"
    for row in subj_df.itertuples():
        task = getattr(row, "task")
        deadline = getattr(row, "deadline")
        deadline = deadline.strftime("%d %b %y")
        text += f"- {task} by {deadline}\n"

    buttons = [[InlineKeyboardButton("Back", callback_data="back_subjects")]]
    keyboard = InlineKeyboardMarkup(buttons)

    query.edit_message_text(text, reply_markup=keyboard)

    return STUDENT_VIEWING


def cancel(update, context):
    """Ends Conversation"""
    query = update.callback_query
    if query:
        query.answer()
        query.edit_message_text(
            "Send /teacher or /student to start the bot again. Goodbye!"
        )
    else:
        update.message.reply_text(
            "Send /teacher or /student to start the bot again. Goodbye!"
        )
    return END


# Daily Homework Cleaning
def homework_clearing(context):
    '''Removing old homework daily'''
    global hw_df
    hw_df["deadline"] = pd.to_datetime(hw_df["deadline"])
    hw_df = hw_df[hw_df["deadline"] > datetime.now()]
    hw_df.to_csv(hw_csv)


# Helper Commands
def help(update, _):
    """Sends all possible interactions"""
    update.message.reply_text(
        "Here is the list of commands you can send:\n\n"
        "/start to register (for new users)\n"
        "/student if you're a student"
        "/start if you're a teacher"
        "/help for more information"
    )


def main():
    # Initialisation
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Registration Conversation
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER: [
                CallbackQueryHandler(reg_student_confirm, pattern="^reg_student$"),
                CallbackQueryHandler(reg_teacher_details, pattern="^reg_teacher$"),
            ],
            REG_TEACHER_DETAILS: [
                MessageHandler(Filters.text & ~(Filters.command), reg_teacher_confirm)
            ],
            REG_TEACHER_CONFIRM: [
                CallbackQueryHandler(reg_teacher_final, pattern="^teacher_confirm$"),
                CallbackQueryHandler(start, pattern="^not_confirmed$"),
            ],
            REG_STUDENT_CONFIRM: [
                CallbackQueryHandler(reg_student_final, pattern="^student_confirm$"),
                CallbackQueryHandler(start, pattern="^not_confirmed$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
    )

    # Teacher Conversation
    teacher_conv = ConversationHandler(
        entry_points=[CommandHandler("teacher", teacher)],
        states={
            TEACHER_MENU: [
                CallbackQueryHandler(teacher_add_hw_name, pattern="^add_hw$"),
                CallbackQueryHandler(teacher_view_hw, pattern="^view_hw$"),
            ],
            TEACHER_VIEWING: [
                CallbackQueryHandler(teacher, pattern="^back_teacher_menu$"),
            ],
            TEACHER_HW_NAME: [
                MessageHandler(
                    Filters.text & ~(Filters.command), teacher_add_hw_deadline
                )
            ],
            TEACHER_HW_DEADLINE: [
                MessageHandler(
                    Filters.text & ~(Filters.command), teacher_add_hw_confirm
                )
            ],
            TEACHER_ADD_HW_RETURN: [
                CallbackQueryHandler(teacher_add_hw_done, pattern="^confirm_add_hw$"),
                CallbackQueryHandler(teacher, pattern="^back_teacher_menu$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CommandHandler("cancel", "cancel"),
        ],
    )

    # Student Conversation
    student_conv = ConversationHandler(
        entry_points=[CommandHandler("student", student)],
        states={
            STUDENT_MENU: [
                CallbackQueryHandler(student_pomodoro_init, pattern="^pomodoro$"),
                CallbackQueryHandler(student_view_subject, pattern="^homework$"),
                CallbackQueryHandler(
                    student_completed_tasks, pattern="^completed_tasks$"
                ),
            ],
            STUDENT_POMODORO_TASK: [
                MessageHandler(
                    Filters.text & ~(Filters.command), student_pomodoro_duration
                )
            ],
            STUDENT_POMODORO_DURATION: [
                MessageHandler(
                    Filters.regex("^[-0-9]+$"),
                    student_pomodoro_start,
                    pass_job_queue=True,
                ),
            ],
            STUDENT_POMODORO_IN_SESSION: [
                MessageHandler(Filters.all, student_pomodoro_in_session),
                CallbackQueryHandler(student, pattern="^back_student_menu$"),
            ],
            STUDENT_COMPLETED_TASKS: [
                CallbackQueryHandler(
                    student, pattern="^(clear_history|back_student_menu)$"
                )
            ],
            STUDENT_VIEW_SUBJECT: [
                CallbackQueryHandler(student, pattern="^back_student_menu$"),
                CallbackQueryHandler(student_view_homework),
            ],
            STUDENT_VIEWING: [
                CallbackQueryHandler(student_view_subject, pattern="back_subjects"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CommandHandler("cancel", "cancel"),
        ],
    )

    dispatcher.add_handler(reg_conv)
    dispatcher.add_handler(teacher_conv)
    dispatcher.add_handler(student_conv)

    # Job for daily homework reset at 8am
    job_queue = updater.job_queue
    job_queue.run_daily(
        homework_clearing,
        time=time(hour=8, tzinfo=pytz.timezone("Asia/Singapore")),
        days=(0, 1, 2, 3, 4, 5, 6),
    )

    # Commands
    dispatcher.add_handler(CommandHandler("help", help))

    # Polling
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
