import pandas as pd
from config import DOWNLOAD_DIR, FILTER_FN, FILTER_TARIFF

def form_sigma_dataframe(data):
    columns_to_keep = [
        'Название организации',
        'ИНН',
        'Окончание срока ФН',
        'Тариф Sigma',
        'Касса оплачена до',
        'Тип бизнеса',
        'Кол-во касс',
        'Срок модуля "Маркировка"',
        'Примечание',
        'Источник'
    ]

    # Создаем DataFrame и трансформируем за один проход
    df = pd.DataFrame(data).rename(columns={
        'companyName': 'Название организации',
        'INN': 'ИНН',
        'businessType': 'Тип бизнеса',
        'endTrialDate': 'Срок модуля "Маркировка"',
        'tariff': 'Тариф Sigma',
        'disconnectDate': 'Касса оплачена до',
        'fiscalExpiration': 'Окончание срока ФН',
        'deviceCount': 'Кол-во касс'
    })
    df['Примечание'] = 'Указан срок оплаты касс по тарифам Sigma'
    df['Источник'] = 'АТОЛ Sigma'
    # Упорядочиваем колонки
    df = df[columns_to_keep]
    
    return df


def form_odf_ru_dataframe(df: pd.DataFrame, selected_filter, start_date, end_date):
    """Подготовка и фильтрация данных с сайта "ofd.ru" в DataFrame."""

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
        "Адрес расчетов",
        "Примечание",
        "Источник"
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
    
    df["Источник"] = 'Пётр сервис'

    df = df[columns_to_keep]
    mask = df[date_column].between(start_date, end_date)
    df = df[mask]

    return df

def form_one_ofd_dataframe(df: pd.DataFrame, selected_filter, start_date, end_date):
    """Подготовка и фильтрация данных с сайта "1-ofd.org" в DataFrame."""
    
    df["Регистрационный номер ККТ"] = df["Регистрационный номер ККТ   "].astype(str)
    df["Номер ФН"] = df["Номер ФН   "].astype(str)

    date_columns = ["Дата окончание действия ФН   ", "Дата остановки тарифа   "]
    for col in date_columns:
        df[col.strip()] = pd.to_datetime(df[col], errors='coerce')

    columns_to_keep = [
        "Название организации",
        "Регистрационный номер ККТ",
        "Номер ФН",
        "Адрес расчетов",
        "Окончание срока ФН",
        "Касса оплачена до",
        "Примечание",
        "Источник"
    ]

    date_column = ''
    lifetime = ''
    if selected_filter == FILTER_FN:
        lifetime = ", Срок ФН: " + df["Дата окончание действия ФН"].dt.strftime('%d.%m.%Y').fillna('')
        date_column = "Окончание срока ФН"
    elif selected_filter == FILTER_TARIFF:
        lifetime = ", Срок ОФД: " + df["Дата остановки тарифа"].dt.strftime('%d.%m.%Y').fillna('')
        date_column = "Касса оплачена до"

    df["Примечание"] = (
        "РНК: " + df["Регистрационный номер ККТ"].fillna('') +
        ", Статус тарифа: " + df["Статус тарификации   "].fillna('') + ' ' + df['Наименование тарифа   '].fillna('') +
        lifetime
    )
    
    # Для корректной сортировки результатов в таблице по датам назовём колонки так же, как в первой таблице
    df["Источник"] = 'Первый ОФД'
    df["Название организации"] = df['Клиент   ']
    df['Окончание срока ФН'] = df['Дата окончание действия ФН']
    df['Касса оплачена до'] = df['Дата остановки тарифа']
    df['Адрес расчетов'] = df['Адрес торговой точки   ']

    df = df[columns_to_keep]
    mask = df[date_column].between(start_date, end_date)
    df = df[mask]

    return df