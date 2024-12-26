import os
from logging import getLogger

import pandas as pd
from datetime import datetime, date
from calendar import monthrange

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackContext, Filters,
    ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler
)

from config import DOWNLOAD_DIR, DOWNLOAD_URLS
from selenium_driver import selenium_download_all

logger = getLogger(__name__)

# Состояния
WELCOME, CHOOSING, TYPING_START_DATE, TYPING_END_DATE = range(4)

# Фильтры
FILTER_FN = 'FILTER_FN'
FILTER_TARIFF = 'FILTER_TARIFF'


# ========== 1. Приветственное сообщение (5 кнопок) ==========

def welcome(update: Update, context: CallbackContext) -> int:
    """
    Приветственное сообщение со списком 5 кнопок:
      - ФН текущего месяца
      - ФН следующего месяца
      - ОФД текущего месяца
      - ОФД следующего месяца
      - Другое
    """
    msg = update.effective_message  # универсальный "Message"

    keyboard = [
        [
            InlineKeyboardButton("ФН текущего месяца", callback_data="FN_THIS_MONTH"),
            InlineKeyboardButton("ФН следующего месяца", callback_data="FN_NEXT_MONTH")
        ],
        [
            InlineKeyboardButton("ОФД текущего месяца", callback_data="OFD_THIS_MONTH"),
            InlineKeyboardButton("ОФД следующего месяца", callback_data="OFD_NEXT_MONTH")
        ],
        [InlineKeyboardButton("Другое", callback_data="CUSTOM_CHOICE")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg.reply_text(
        text="Что будем выгружать?",
        reply_markup=reply_markup
    )

    return WELCOME


def welcome_choice(update: Update, context: CallbackContext) -> int:
    """Обработчик нажатия кнопок в приветственном меню."""
    query = update.callback_query
    query.answer()
    choice = query.data

    # Если выбрано "Другое", идём на старый сценарий CHOOSING (ФН/ОФД + ручные даты)
    if choice == "CUSTOM_CHOICE":
        # Вместо того, чтобы просто менять текст, 
        # отправляем inline-клавиатуру (ФН / ОФД).
        keyboard = [
            [InlineKeyboardButton("Сортировка по сроку ФН", callback_data=FILTER_FN)],
            [InlineKeyboardButton("Сортировка по тарифу ОФД", callback_data=FILTER_TARIFF)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text="Выберите, какой тип документа выгрузить:",
            reply_markup=reply_markup
        )
        return CHOOSING


    # Определяем тип фильтра (ФН или ОФД) и даты (текущий / следующий месяц)
    today = date.today()
    if choice == "FN_THIS_MONTH":
        filter_type = FILTER_FN
        year, month = today.year, today.month
    elif choice == "FN_NEXT_MONTH":
        filter_type = FILTER_FN
        year, month = today.year, today.month + 1
        if month == 13:
            month = 1
            year += 1
    elif choice == "OFD_THIS_MONTH":
        filter_type = FILTER_TARIFF
        year, month = today.year, today.month
    elif choice == "OFD_NEXT_MONTH":
        filter_type = FILTER_TARIFF
        year, month = today.year, today.month + 1
        if month == 13:
            month = 1
            year += 1
    else:
        # fallback
        filter_type = FILTER_FN
        year, month = today.year, today.month

    # Формируем даты
    start_date = datetime(year, month, 1)
    last_day = monthrange(year, month)[1]
    end_date = datetime(year, month, last_day)

    # Сохраняем в user_data, если нужно
    context.user_data['selected_filter'] = filter_type
    context.user_data['start_date'] = start_date
    context.user_data['end_date'] = end_date

    query.edit_message_text(text="Идёт обработка данных. Пожалуйста, подождите...")

    # Запуск обработки
    # Передаём update, context, msg=query.message
    return process_data(
        update=update,
        context=context,
        msg=query.message,
        selected_filter=filter_type,
        start_date=start_date,
        end_date=end_date
    )


# ========== 2. Сценарий "Другое": выбор ФН / ОФД + ручной ввод дат ==========

def choosing(update: Update, context: CallbackContext) -> int:
    """Старый сценарий: выбор ФН / ОФД + ручные даты."""
    keyboard = [
        [InlineKeyboardButton("Сортировка по сроку ФН", callback_data=FILTER_FN)],
        [InlineKeyboardButton("Сортировка по тарифу ОФД", callback_data=FILTER_TARIFF)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        'Выберите, какой тип документа выгрузить:',
        reply_markup=reply_markup
    )
    return CHOOSING


def choose_filter(update: Update, context: CallbackContext) -> int:
    """Обработка выбора ФН / ОФД в режиме 'другое'."""
    query = update.callback_query
    query.answer()

    selected_filter = query.data
    context.user_data['selected_filter'] = selected_filter

    query.edit_message_text(
        text="С какой даты искать? Введите в формате ДД.ММ.ГГГГ\n\n Чтобы отменить, нажмите /cancel"
    )
    return TYPING_START_DATE


def input_start_date(update: Update, context: CallbackContext) -> int:
    """Ввод начальной даты (ручной)."""
    text = update.message.text

    if text == '/cancel':
        return cancel(update, context)

    try:
        start_date = datetime.strptime(text, "%d.%m.%Y")
        context.user_data['start_date'] = start_date
        update.message.reply_text("По какую дату?\n\n Отменить - /cancel")
        return TYPING_END_DATE
    except ValueError:
        update.message.reply_text(
            "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n\n Чтобы отменить, нажмите /cancel"
        )
        return TYPING_START_DATE


def input_end_date(update: Update, context: CallbackContext) -> int:
    """Ввод конечной даты (ручной)."""
    text = update.message.text
    if text == '/cancel':
        return cancel(update, context)

    try:
        end_date = datetime.strptime(text, "%d.%m.%Y")
        start_date = context.user_data['start_date']
        if end_date < start_date:
            update.message.reply_text("Конечная дата меньше начальной...")
            return TYPING_END_DATE

        context.user_data['end_date'] = end_date
        update.message.reply_text("Идёт обработка данных. Подождите...")

        selected_filter = context.user_data['selected_filter']

        # Запуск обработки, передавая update.message как msg
        return process_data(
            update=update,
            context=context,
            msg=update.message,
            selected_filter=selected_filter,
            start_date=start_date,
            end_date=end_date
        )

    except ValueError:
        update.message.reply_text(
            "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n\n Чтобы отменить, нажмите /cancel"
        )
        return TYPING_END_DATE


# ========== 3. Команда cancel и возврат в главное меню ==========

def cancel(update: Update, context: CallbackContext):
    """Команда для возврата на исходную (главное меню)."""
    # Возвращаемся к состоянию WELCOME
    return welcome(update, context)


# ========== 4. Подготовка DataFrame ==========

def prepare_dataframe(df, selected_filter, start_date, end_date):
    """Подготовка и фильтрация данных в DataFrame."""
    df["ИНН"] = df["ИНН"].astype(str)
    df["Заводской номер ККТ"] = df["Заводской номер ККТ"].astype(str)

    date_columns = ["Окончание срока ФН", "Касса оплачена до", "Дата последнего ФД"]
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    columns_to_keep = [
        "Название организации",
        "ИНН",
        "Модель кассы",
        "Заводской номер ККТ",
        "Тип ФН",
        "Окончание срока ФН",
        "Касса оплачена до",
        "Дата последнего ФД",
        "Примечание"
    ]

    date_column = ''
    lifetime = ''
    if selected_filter == FILTER_FN:
        lifetime = ", Срок ФН: " + df["Окончание срока ФН"].dt.strftime('%d.%m.%Y').fillna('')
        date_column = "Окончание срока ФН"
    elif selected_filter == FILTER_TARIFF:
        lifetime = ", Срок ОФД: " + df["Касса оплачена до"].dt.strftime('%d.%m.%Y').fillna('')
        date_column = "Касса оплачена до"

    df["Примечание"] = (
        "Модель: " + df["Модель кассы"].fillna('') +
        ", Номер: " + df["Заводской номер ККТ"].fillna('') +
        ", Тип ФН: " + df["Тип ФН"].fillna('') +
        lifetime +
        ", Последний ФД: " + df["Дата последнего ФД"].dt.strftime('%d.%m.%Y').fillna('')
    )

    df = df[columns_to_keep]
    mask = df[date_column].between(start_date, end_date)
    df = df[mask]

    return df


# ========== 5. Основная функция process_data ==========

def process_data(
    update: Update,
    context: CallbackContext,
    msg,  # объект telegram.Message (update.message или update.callback_query.message)
    selected_filter,
    start_date,
    end_date
) -> int:
    """
    Универсальная функция обработки (скачивание, подготовка, отправка).
    При отсутствии файлов или по завершении, возвращаемся в меню через cancel(update, context).
    """

    from logging import getLogger
    from config import DOWNLOAD_DIR, DOWNLOAD_URLS
    from selenium_driver import selenium_download_all

    logger = getLogger(__name__)

    file_name = f'{start_date.strftime("%d.%m.%Y")}-{end_date.strftime("%d.%m.%Y")}_{selected_filter}.xlsx'

    try:
        logger.info("Начало загрузки файлов...")
        downloaded_file_paths = selenium_download_all(DOWNLOAD_URLS)

        if not downloaded_file_paths:
            logger.warning("Нет файлов для обработки. Проверьте скачанные файлы.")
            msg.reply_text("Никаких данных для обработки не получено.")
            return cancel(update, context)

        # Обработка xlsx
        processed_dfs = []
        for file_path in downloaded_file_paths:
            logger.info(f"Обработка файла: {file_path}")
            df = pd.read_excel(file_path)
            df_prepared = prepare_dataframe(df, selected_filter, start_date, end_date)

            if not df_prepared.empty:
                processed_dfs.append(df_prepared)
                logger.info(f"Файл {file_path} обработан успешно.")
            else:
                logger.warning(f"После фильтрации данных из файла {file_path} нет.")
            os.remove(file_path)  # чистим скачанные файлы

        if not processed_dfs:
            logger.warning("После фильтрации данных нет результатов.")
            msg.reply_text("После фильтрации данных нет результатов.")
            return cancel(update, context)

        # Объединение и сохранение итогового Excel
        combined_df = pd.concat(processed_dfs, ignore_index=True)
        if selected_filter == FILTER_FN:
            date_column = "Окончание срока ФН"
        else:
            date_column = "Касса оплачена до"

        sorted_df = combined_df.sort_values(by=date_column, ascending=True)

        cols_to_drop = [
            "Модель кассы", "Заводской номер ККТ",
            "Тип ФН", "Дата последнего ФД",
            "Окончание срока ФН", "Касса оплачена до"
        ]
        df_filtered = sorted_df.drop(columns=cols_to_drop)

        output_file_path = os.path.join(DOWNLOAD_DIR, file_name)
        with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
            df_filtered.to_excel(writer, index=False, sheet_name='Данные')
            worksheet = writer.sheets['Данные']
            for idx, col in enumerate(df_filtered.columns):
                series = df_filtered[col].astype(str)
                max_len = max(series.map(len).max() if not series.empty else len(col), len(str(col))) + 2
                worksheet.set_column(idx, idx, max_len)

        # Отправка результата пользователю
        with open(output_file_path, 'rb') as file:
            msg.reply_document(document=file, filename=file_name)
        os.remove(output_file_path)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке и обработке файлов: {e}")
        msg.reply_text("Ошибка. Зафиксировано в логах. Сообщите администратору.")
    finally:
        # В любом случае, возвращаемся в главное меню
        return cancel(update, context)


# ========== 6. ConversationHandler ==========

def get_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('start', welcome)],
        states={
            WELCOME: [CallbackQueryHandler(welcome_choice, pattern="^(FN_THIS_MONTH|FN_NEXT_MONTH|OFD_THIS_MONTH|OFD_NEXT_MONTH|CUSTOM_CHOICE)$")],
            CHOOSING: [CallbackQueryHandler(choose_filter, pattern=f"^{FILTER_FN}$|^{FILTER_TARIFF}$")],
            TYPING_START_DATE: [MessageHandler(Filters.text & ~Filters.command, input_start_date)],
            TYPING_END_DATE: [MessageHandler(Filters.text & ~Filters.command, input_end_date)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
