import datetime
import inspect
import logging
import pickle
import sys
import traceback
from functools import wraps

import requests
from selenium.common import InvalidSessionIdException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement

import time
import os

from selenium.webdriver.support.wait import WebDriverWait

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
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


def load_auth_cookiess():
    try:
        session = requests.Session()
        with open("cookies.pkl", "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
        return session
    except (EOFError, FileNotFoundError):
        return


class WebdriverProfile:
    def __init__(self):
        self.download_directory = DOWNLOAD_DIR
        self.options = ChromeOptions()
        self.options.add_argument('--allow-profiles-outside-user-dir')
        self.options.add_argument('--enable-profile-shortcut-manager')
        self.options.add_argument(rf"user-data-dir={os.path.join(os.getcwd(), 'browser_profile')}")  # Убедитесь, что путь правильный
        # self.options.add_argument("--headless")  # Выполнение в фоновом режиме без открытия браузера
        self.options.add_argument("--window-size=1600,900")
        self.options.add_argument("--no-sandbox")
        self.options.add_experimental_option("prefs", {
            "download.default_directory": self.download_directory,
            "download.prompt_for_download": False,  # Всплывающее окно загрузки
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })
        self.driver = Chrome(options=self.options)
        self.driver.implicitly_wait(15)

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
    def ofd_login(self):
        find = self.find
        click = self.click
        driver = self.driver

        driver.get(LOGIN_URL)
        time.sleep(2)

        submit_button_xpath = "/html/body/pk-app-shell/app-main-page/section/div[1]/div/app-main-login/div/form/div[3]/button/span[1]"
        submit_button = find(submit_button_xpath)
        click(submit_button)
        time.sleep(10)

        return True

    def get_auth_cookies(self):
        driver = self.driver
        # Сохранение cookies
        cookies = driver.get_cookies()
        with open("cookies.pkl", "wb") as file:
            pickle.dump(cookies, file)
        self.close()

    @log_print
    def ofd_direct_download(self, url):
        try:  # Если при загрузке найден элемент со страницы авторизации, выполняет скрипт авторизации
            # Загрузка cookies в сессию requests
            try:
                session = load_auth_cookiess()
            except (EOFError, FileNotFoundError) as e:
                logging.info(e)
                self.get_auth_cookies()
            self.driver.get(url)
            return 'True'

        except InvalidSessionIdException:
            logging.critical(f'{traceback.format_exc()}')
            sys.exit(1)

        except Exception:
            logging.warning(f'{traceback.format_exc()}')
            if '--headless' in self.options.arguments:
                return False
            time.sleep(36000)
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
        before_download = set(os.listdir(DOWNLOAD_DIR))
        file_path = os.path.join(DOWNLOAD_DIR, f'\ККТ партнёра-{datetime.datetime.now().strftime("%Y-%m-%d_%I-%M")}.xlsx')
        browser.ofd_direct_download(url)
        # Проверка, что файл полностью загружен
        try:
            WebDriverWait(browser.driver, 20).until(
                lambda driver: any(file.endswith('.xlsx') or file.endswith('.xls') for file in os.listdir(DOWNLOAD_DIR))
            )
        except TimeoutException:
            logger.error(f"Загрузка из {url} не завершилась вовремя.")
            continue  # Пропустить текущий URL и перейти к следующему

        after_download = set(os.listdir(DOWNLOAD_DIR))
        new_files = after_download - before_download
        for file_name in new_files:
            if file_name.endswith('.xlsx') or file_name.endswith('.xls'):
                file_path = os.path.join(DOWNLOAD_DIR, file_name)
                downloaded_files.append(file_path)
                logger.info(f"Файл скачан: {file_name}")

    browser.close()
    return downloaded_files


if __name__ == '__main__':
    browser = WebdriverProfile()
    time.sleep(10000)
    browser.close()
