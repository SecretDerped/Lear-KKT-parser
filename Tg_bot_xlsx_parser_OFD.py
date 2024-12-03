import os
from logging import getLogger

import pandas as pd
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (CallbackContext, Filters,
                          ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler)

from config import DOWNLOAD_DIR, DOWNLOAD_URLS
from selenium_driver import selenium_download_all

logger = getLogger(__name__)

# Определяем состояния разговора
CHOOSING, TYPING_START_DATE, TYPING_END_DATE = range(3)
# Определяем фильтры
FILTER_FN = 'FILTER_FN'
FILTER_TARIFF = 'FILTER_TARIFF'


def start(update: Update, context: CallbackContext) -> int:
    """Функция начала разговора"""
    keyboard = [
        [InlineKeyboardButton("Сортировка по сроку ФН", callback_data=FILTER_FN)],
        [InlineKeyboardButton("Сортировка по тарифу ОФД", callback_data=FILTER_TARIFF)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        'Выберите, какой тип документа выгрузить:',
        reply_markup=reply_markup)
    return CHOOSING


def cancel(update: Update, context: CallbackContext):
    """Команда для возврата на исходную"""
    return start(update, context)


# Обработка выбора пользователя
def choose_filter(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    # Сохраняем выбранный фильтр
    selected_filter = query.data
    context.user_data['selected_filter'] = selected_filter

    # Спрашиваем начальную дату
    query.edit_message_text(
        text="С какой даты искать? Введите в формате ДД.ММ.ГГГГ\n\n Чтобы отменить, нажмите /cancel")
    return TYPING_START_DATE


# Обработка ввода начальной даты
def input_start_date(update: Update, context: CallbackContext) -> int:
    text = update.message.text

    if text == '/cancel':
        return cancel(update, context)

    try:
        start_date = datetime.strptime(text, "%d.%m.%Y")
        context.user_data['start_date'] = start_date
        update.message.reply_text("По какую дату?\n\n Отменить - /cancel")
        return TYPING_END_DATE
    except ValueError:
        update.message.reply_text("Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n\n Чтобы отменить, нажмите /cancel")
        return TYPING_START_DATE


# Обработка ввода конечной даты
def input_end_date(update: Update, context: CallbackContext) -> int:
    text = update.message.text

    if text == '/cancel':
        return cancel(update, context)

    try:
        end_date = datetime.strptime(text, "%d.%m.%Y")
        start_date = context.user_data['start_date']

        if end_date < start_date:
            update.message.reply_text(
                "Конечная дата меньше начальной. Введите корректную дату.\n\n Чтобы отменить, нажмите /cancel")
            return TYPING_END_DATE

        context.user_data['end_date'] = end_date

        # Теперь можем обработать данные и отправить файл
        update.message.reply_text("Идет обработка данных. Подождите, пожалуйста...")

        # Запускаем функцию обработки данных и переходим в состояние CHOOSING
        return process_data(update, context)

    except ValueError:
        update.message.reply_text("Пожалуйста, введите дату в формате ДД.ММ.ГГГГ")
        return TYPING_END_DATE


def prepare_dataframe(df, selected_filter, start_date, end_date):
    # Преобразуем ИНН и Заводской номер ККТ в строки, чтобы избежать форматирования как чисел
    df["ИНН"] = df["ИНН"].astype(str)
    df["Заводской номер ККТ"] = df["Заводской номер ККТ"].astype(str)

    # Преобразуем даты в формат datetime
    date_columns = ["Окончание срока ФН", "Касса оплачена до", "Дата последнего ФД"]
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Оставляем только нужные колонки
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
    # Фильтруем данные
    df = df[columns_to_keep]
    mask = df[date_column].between(start_date, end_date)
    df = df[mask]

    return df


# Функция обработки данных и отправки файла
def process_data(update: Update, context: CallbackContext):
    selected_filter = context.user_data['selected_filter']
    start_date = context.user_data['start_date']
    end_date = context.user_data['end_date']
    file_name = f'{start_date.strftime("%d.%m.%Y")}-{end_date.strftime("%d.%m.%Y")}_{selected_filter}.xlsx'

    try:
        # Список URL для скачивания
        urls = DOWNLOAD_URLS
        logger.info("Начало загрузки файлов.")

        # Скачиваем файлы из списка URL
        downloaded_file_paths = selenium_download_all(urls)

        if not downloaded_file_paths:
            logger.warning("Нет файлов для обработки. Проверьте скачанные файлы.")
            update.message.reply_text("Никаких данных для обработки не получено.")
            return

        # Обрабатываем каждый скачанный файл
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
            os.remove(file_path)

        if not processed_dfs:
            logger.warning("После фильтрации данных из всех файлов нет результатов.")
            update.message.reply_text("После фильтрации данных нет результатов.")
            return

            # Объединяем все обработанные DataFrame в один
        combined_df = pd.concat(processed_dfs, ignore_index=True)
        # Опционально: удаляем исходные колонки, которые теперь находятся в "Примечание"

        date_column = "Касса оплачена до"
        if selected_filter == FILTER_FN:
            date_column = "Окончание срока ФН"
        sorted_df = combined_df.sort_values(by=date_column, ascending=True)

        cols_to_drop = ["Модель кассы", "Заводской номер ККТ",
                        "Тип ФН", "Дата последнего ФД",
                        "Окончание срока ФН", "Касса оплачена до"]
        df_filtered = sorted_df.drop(columns=cols_to_drop)

        # Сохранение объединённого DataFrame в новый Excel-файл
        output_file_path = os.path.join(DOWNLOAD_DIR, file_name)
        with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
            df_filtered.to_excel(writer, index=False, sheet_name='Данные')

            worksheet = writer.sheets['Данные']
            for idx, col in enumerate(df_filtered.columns):
                series = df_filtered[col].astype(str)
                max_len = max(series.map(len).max() if not series.empty else len(col), len(str(col))) + 2
                worksheet.set_column(idx, idx, max_len)

        # Отправляем файл пользователю
        with open(output_file_path, 'rb') as file:
            update.message.reply_document(document=file, filename=file_name)
        os.remove(output_file_path)
        update.message.reply_text("Готово!")

    except Exception as e:
        logger.exception(f"Ошибка при загрузке и обработке файлов: {e}")
        update.message.reply_text("Ошибка. Зафиксировано в логах. Сообщите администратору.")

    finally:
        # Предлагаем пользователю снова выбрать действия
        # Возврат к состоянию CHOOSING
        return cancel(update, context)


def get_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [CallbackQueryHandler(choose_filter, pattern=f"^{FILTER_FN}$|^{FILTER_TARIFF}$")],
            TYPING_START_DATE: [MessageHandler(Filters.text & ~Filters.command, input_start_date)],
            TYPING_END_DATE: [MessageHandler(Filters.text & ~Filters.command, input_end_date)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
