import inspect
import logging
import shutil
import sys
import tempfile
import traceback
from functools import wraps
import time
import os

import requests

from selenium.common import InvalidSessionIdException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from config import DOWNLOAD_DIR, OFD_RU_LOGIN_URL, OFD_RU_USERNAME, OFD_RU_PASSWORD, ONE_OFD_PASSWORD, ONE_OFD_USERNAME

logger = logging.getLogger(__name__)


def log_print(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        all_args = {arg: value for arg, value in bound.arguments.items() if
                    arg != 'self'}  # Создаём словарь аргументов, исключая 'self'
        logging.info(f'CALL {func.__name__}{all_args}...')
        start_time = time.time()

        result = func(*args, **kwargs)

        exec_time = time.time() - start_time
        logging.info(f'RESULT {func.__name__}{all_args} ({exec_time:.3f} sec.):\n{result} ')
        return result

    return _wrapper


def log_webdriver_action(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        # Предполагаем, что первый аргумент после self - это либо экземпляр WebDriver, либо WebElement
        element_or_driver = args[1]
        description = "WebDriver" if not isinstance(element_or_driver, WebElement) else "WebElement"
        # Дополнительно логгируем тип элемента и его атрибуты, если это WebElement
        if description != "WebElement":
            logging.info(f"CALL {func.__name__} on {description}...")
        else:
            try:
                text = element_or_driver.text
                element_description = f"{element_or_driver.tag_name} element"
                if text:
                    element_description += f" with text:\n'{text}'"
            except:
                element_description = "unknown element"
            logging.info(f"CALL {func.__name__} on {element_description}...")

        start_time = time.time()
        result = func(*args, **kwargs)
        exec_time = time.time() - start_time
        logging.info(f"RESULT {func.__name__} is completed for {exec_time:.3f} sec.")
        return result

    return _wrapper


class WebdriverProfile:
    def __init__(self):
        self.options = ChromeOptions()
        self.options.add_argument("--user-data-dir=/root/browser_profile")
        self.options.add_argument('--profile-directory=Profile 1')
        self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--window-size=1280,720")
        self.options.add_argument("--disable-extensions")
        self.options.add_argument("--disable-infobars")
        self.options.add_argument("--disable-browser-side-navigation")
        self.options.add_argument("--disable-features=VizDisplayCompositor")
        self.options.binary_location = "/usr/bin/google-chrome"
        self.options.add_experimental_option("prefs", {
            "download.default_directory": DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "safebrowsing.enabled": True,
        })
        self.service = Service('/usr/local/bin/chromedriver')
        self.driver = Chrome(service=self.service, options=self.options)
        self.driver.implicitly_wait(20)

    @log_print
    def close(self):
        try:
            self.driver.quit()
            return True
        except Exception:
            return False

    @log_webdriver_action
    def click(self, element):
        """Imitate moving cursor and clicking the web element"""
        ActionChains(self.driver).move_to_element(element).click().perform()
        return True

    def find(self, xpath: str):
        """Search for one web element by Xpath"""
        result = self.driver.find_element(By.XPATH, xpath)
        return result

    def find_all(self, xpath: str):
        """Searching for all web elements by Xpath"""
        result = self.driver.find_elements(By.XPATH, xpath)
        return result

    @log_print
    def ofd_ru_login(self):
        find = self.find
        click = self.click
        driver = self.driver

        driver.get(OFD_RU_LOGIN_URL)

        login_input_xpath = '/html/body/pk-app-shell/app-main-page/section/div[1]/div/app-main-login/div/form/ui-text-control[1]/div/input'
        login_field = find(login_input_xpath)
        login_field.send_keys(OFD_RU_USERNAME)

        password_input_xpath = '/html/body/pk-app-shell/app-main-page/section/div[1]/div/app-main-login/div/form/ui-text-control[2]/div/input'
        password_field = find(password_input_xpath)
        password_field.send_keys(OFD_RU_PASSWORD)

        submit_button_xpath = "/html/body/pk-app-shell/app-main-page/section/div[1]/div/app-main-login/div/form/div[3]/button"
        submit_button = find(submit_button_xpath)
        click(submit_button)

        return True

    @log_print
    def ofd_ru_download(self, url):
        try:
            self.driver.get(url)
            # Если при загрузке найден элемент ошибки, выполняет скрипт авторизации
            if 'Errors' in self.driver.page_source:
                self.ofd_ru_login()
                self.driver.get(url)
            return 'True'

        except InvalidSessionIdException:
            logging.critical(f'{traceback.format_exc()}')
            sys.exit(1)

        except Exception as e:
            logging.warning(f'{e}: {traceback.format_exc()}')
            if '--headless' in self.options.arguments:
                time.sleep(36000)
                return False
            return None

    @log_print
    def one_ofd_login(self):
        find = self.find
        click = self.click
        driver = self.driver

        driver.get(OFD_RU_LOGIN_URL)

        login_input_xpath = '/html/body/app-root/div/div/div/registration-login-mail/div/div/div/div/app-taxpayer-input/div/div/input'
        login_field = find(login_input_xpath)
        login_field.send_keys(ONE_OFD_USERNAME)

        contune_button_xpath = "/html/body/app-root/div/div/div/registration-login-mail/div/div/div/div/div/app-button"
        contune_button = find(contune_button_xpath)
        click(contune_button)

        password_input_xpath = '/html/body/app-root/div/div/div/registration-login-password/div/div/div/app-taxpayer-input/div/div/input'
        password_field = find(password_input_xpath)
        password_field.send_keys(ONE_OFD_PASSWORD)

        contune_button_xpath = '/html/body/app-root/div/div/div/registration-login-password/div/div/div/div[2]/app-button'
        contune_button = find(contune_button_xpath)
        click(contune_button)

        return True

    @log_print
    def one_ofd_download(self, url):
        try:
            self.driver.get(url)
            # Если при загрузке найден элемент ошибки, выполняет скрипт авторизации
            if 'invalid' in self.driver.page_source:
                self.one_ofd_login()
                self.driver.get(url)
            return 'True'

        except InvalidSessionIdException:
            logging.critical(f'{traceback.format_exc()}')
            sys.exit(1)

        except Exception as e:
            logging.warning(f'{e}: {traceback.format_exc()}')
            if '--headless' in self.options.arguments:
                time.sleep(36000)
                return False
            return None
        

def selenium_download_all(urls):
    browser = WebdriverProfile()
    logger.info("Chrome запущен.")
    downloaded_files = []

    if not urls:
        logger.warning("Список URL пуст.")
        return downloaded_files


    for index, url in enumerate(urls, start=1):
        logger.info(f"Переход к URL {index}/{len(urls)}: {url}")

        if 'https://pk.ofd.ru/api/' in url:
            browser.ofd_ru_download(url)
            
        if 'https://org.1-ofd.ru/api/' in url:
            browser.one_ofd_download(url)

        before_download = set(os.listdir(DOWNLOAD_DIR))  # Сохраняем текущие файлы
        logger.debug(f"{before_download = }")

        # Ожидаем появления нового файла и проверки его статуса
        try:
            WebDriverWait(browser.driver, 20).until(
                lambda driver: any(file.endswith('.xlsx') and file not in before_download for file in os.listdir(DOWNLOAD_DIR))
            )
        except TimeoutException:
            logger.error(f"Загрузка из {url} не завершилась вовремя.")
            return None

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

    browser.close()
    return downloaded_files



if __name__ == '__main__':
    browser = WebdriverProfile()
    time.sleep(10000)
    browser.close()
