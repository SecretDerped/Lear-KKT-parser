from time import time
from functools import wraps
import inspect
import logging
from selenium.webdriver.remote.webelement import WebElement

def log_print(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        all_args = {arg: value for arg, value in bound.arguments.items() if
                    arg != 'self'}  # Создаём словарь аргументов, исключая 'self'
        logging.info(f'CALL {func.__name__}{all_args}...')
        start_time = time()

        result = func(*args, **kwargs)

        exec_time = time() - start_time
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

        start_time = time()
        result = func(*args, **kwargs)
        exec_time = time() - start_time
        logging.info(f"RESULT {func.__name__} is completed for {exec_time:.3f} sec.")
        return result

    return _wrapper