from concurrent.futures import ThreadPoolExecutor
import logging
import os
import sys
import threading
import time
import traceback
from typing import List

from selenium_driver import WebdriverProfile
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common import InvalidSessionIdException, TimeoutException

from config import DOWNLOAD_DIR, MAX_WORKERS


logger = logging.getLogger(__name__)

download_lock = threading.Lock() # Глобальная блокировка для операций с файлами в общем каталоге загрузок

def download_files(msg,  # объект telegram.Message (update.message или update.callback_query.message)
                          selected_filter,
                          start_date,
                          end_date,
                          urls: List[str]):
    try:
        browser = WebdriverProfile()
        logger.info("Chrome запущен.")
        downloaded_files = []

        if not urls:
            logger.warning("Список URL пуст.")
            return downloaded_files

        for index, url in enumerate(urls, start=1):
            counter = f'{index}/{len(urls)}'
            before_download = set(os.listdir(DOWNLOAD_DIR))  # Сохраняем текущие файлы
            logger.debug(f"{before_download = }")
            logger.info(f"Переход к URL {index}/{len(urls)}: {url}")
            try:
                if 'pk.ofd.ru/api/' in url:
                    browser.ofd_ru_download(url)
                    msg.reply_text(f"{counter}. Данные от OFD.ru получены.")
                elif 'org.1-ofd.ru/api/' in url:
                    browser.one_ofd_download(url)
                    msg.reply_text(f'{counter}. Данные от "Первый ОФД" получены.')
                elif 'sigma' in url:
                    browser.atol_sigma_download(url, start_date, end_date, selected_filter)
                    msg.reply_text(f"{counter}. Данные по АТОЛ Sigma получены.")
                elif 'kassatka' in url:
                    #browser.kassatka_download(url)
                    msg.reply_text(f"{counter}. Данные по Кассатке получены.")
                else:
                    raise Exception('Unexceptional URL')
            except InvalidSessionIdException:
                logger.critical(f'{traceback.format_exc()}')
                browser.close()
                msg.reply_text(f"{counter}: внутренняя ошибка. Запустите программу выгрузки заново.")
                sys.exit(1)
            except Exception as e:
                logger.warning(f'{e}: {traceback.format_exc()}')
                if '--headless' not in browser.options.arguments:
                    time.sleep(36000)
                    return False
                msg.reply_text(f"{counter}: не удалось выгрузить данные из {url}")
                continue

            # Ожидаем появления нового файла и проверки его статуса
            try:
                WebDriverWait(browser.driver, 30).until(
                    lambda driver: any(file.endswith('.xlsx') and file not in before_download for file in os.listdir(DOWNLOAD_DIR))
                )
            except TimeoutException:
                logger.error(f"Загрузка из {url} не завершается.")
                continue

            # Проверка, что файл завершил загрузку и не является .crdownload
            after_download = set(os.listdir(DOWNLOAD_DIR))
            new_files = after_download - before_download  # Определяем новые файлы
            logger.debug(f"Новые файлы: {new_files}")

            counter = 1
            for file_name in new_files:
                if file_name.endswith('.xlsx'):
                    src_path = os.path.join(DOWNLOAD_DIR, file_name)

                    # Подождём, пока файл не станет доступен (не будет .crdownload)
                    while file_name.endswith('.crdownload') or not os.path.exists(src_path):
                        logger.debug(f"Файл {file_name} ещё не готов, ожидаем...")
                        time.sleep(1)
                        file_name = os.listdir(DOWNLOAD_DIR)[-1]  # Обновляем имя файла, если оно изменилось
                        src_path = os.path.join(DOWNLOAD_DIR, file_name)

                    # Переименовываем файл
                    new_file_name = f"{counter}.xlsx"
                    dest_path = os.path.join(DOWNLOAD_DIR, new_file_name)

                    while os.path.exists(dest_path):  # Если такой файл уже существует, пробуем другой номер
                        counter += 1
                        new_file_name = f"{counter}.xlsx"
                        dest_path = os.path.join(DOWNLOAD_DIR, new_file_name)

                    os.rename(src_path, dest_path)
                    downloaded_files.append(dest_path)
                    logger.info(f"Файл переименован и скачан: {new_file_name}")
                    counter += 1

            # Обновляем список файлов для следующей итерации
            before_download = after_download
    finally:
        browser.close() # Браузер необхоодимо закрывать после каждой сессии, иначе будет либо утечка памяти,
    # либо  программа крашнется, попытавшись включить уже включчённую сессию.
    # Контекстный менеджер не поддерживается вебдрайвером, потому конструкция try/finally.

    return downloaded_files

def download_one_file(url: str,
                      index: int,
                      total: int,
                      selected_filter,
                      start_date,
                      end_date,
                      msg) -> List[str]:
    """Создаёт новый инстанс вебдрайвера и загружает 1 файл"""
    try:
        browser = WebdriverProfile()
        # Зафиксируем состояние директории загрузки перед закачкой. Это нужно, чтобы
        # предотвратить гонку между инстансами, когда они обращаются к одному и тому же каталогу.
        # Можно было и попроще - создавать для каждого инсанса новую папку, а потом объединять, но зачем?
        with download_lock:
            before_download = set(os.listdir(DOWNLOAD_DIR))

        downloaded_file = []  # Да, список. Да, для одного файла.
        # TODO: Изменить список на строку
        counter = f'{index}/{total}' # 2/5
        logger.info(f"Переход к URL {counter}: {url}")

        try:
            if 'pk.ofd.ru/api/' in url:
                browser.ofd_ru_download(url)
                msg.reply_text(f"{counter}. Данные от OFD.ru получены.")
            elif 'org.1-ofd.ru/api/' in url:
                browser.one_ofd_download(url)
                msg.reply_text(f'{counter}. Данные от "Первый ОФД" получены.')
            elif 'sigma' in url:
                browser.atol_sigma_download(url, start_date, end_date, selected_filter)
                msg.reply_text(f"{counter}. Данные по АТОЛ Sigma получены.")
            elif 'kassatka' in url:
                # browser.kassatka_download(url)
                msg.reply_text(f"{counter}. Данные по Кассатке получены.")
            else:
                raise Exception('Unexceptional URL')
        except InvalidSessionIdException:
            logger.critical(traceback.format_exc())
            browser.close()
            msg.reply_text(f"{counter}: внутренняя ошибка. Запустите программу выгрузки заново.")
            return []
        except Exception as e:
            logger.warning(f"{e}: {traceback.format_exc()}")
            if '--headless' not in browser.options.arguments:
                time.sleep(36000)
                return []
            msg.reply_text(f"{counter}: не удалось выгрузить данные из {url}")
            return []

        # Подождём, пока файл не станет доступен (не будет .crdownload)
        try:
            WebDriverWait(browser.driver, 30).until(
                lambda driver: any(
                    file.endswith('.xlsx') and file not in before_download 
                    for file in os.listdir(DOWNLOAD_DIR)
                )
            )
        except TimeoutException:
            logger.error(f"Загрузка из {url} не завершается.")
            return []

        with download_lock:
            after_download = set(os.listdir(DOWNLOAD_DIR))
            new_files = after_download - before_download

        file_counter = 1
        for file_name in new_files:
            if file_name.endswith('.xlsx'):
                src_path = os.path.join(DOWNLOAD_DIR, file_name)
                # Проверка, что файл завершил загрузку и не является .crdownload
                while file_name.endswith('.crdownload') or not os.path.exists(src_path):
                    logger.debug(f"Файл {file_name} ещё не готов, ожидаем...")
                    time.sleep(1)
                    with download_lock:
                        file_name = os.listdir(DOWNLOAD_DIR)[-1]  # Обновляем имя файла, если оно изменилось
                    src_path = os.path.join(DOWNLOAD_DIR, file_name)

                new_file_name = f"{file_counter}.xlsx"  # Меняем имя файла на первое доступное число от единицы
                dest_path = os.path.join(DOWNLOAD_DIR, new_file_name)
                while os.path.exists(dest_path):
                    file_counter += 1
                    new_file_name = f"{file_counter}.xlsx"
                    dest_path = os.path.join(DOWNLOAD_DIR, new_file_name)

                os.rename(src_path, dest_path)
                downloaded_file.append(dest_path)
                logger.info(f"Файл переименован и скачан: {new_file_name}")
                file_counter += 1

        return downloaded_file

    finally:
        # Всегда закрываем драйвер, чтобы избежать утечки и конфликта сессии
        browser.close()


def new_download_files(msg,
                   selected_filter,
                   start_date,
                   end_date,
                   urls: List[str]) -> List[str]:
    """ Загружает все файлы с данными и возвращает их строки расположения """
    if not urls:
        logger.warning("Список URL пуст.")
        return []
    
    downloaded_files = []

    max_workers = min(MAX_WORKERS, len(urls))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        total = len(urls)
        for index, url in enumerate(urls, start=1):
            futures.append(
                executor.submit(
                    download_one_file,
                    url,
                    index,
                    total,
                    selected_filter,
                    start_date,
                    end_date,
                    msg
                )
            )
        # Ждём завершения всех потоков
        for future in futures:
            result = future.result()
            if result:
                downloaded_files.extend(result)
    
    return downloaded_files
