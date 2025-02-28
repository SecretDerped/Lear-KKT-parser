from logging import INFO, basicConfig, DEBUG
import logging
from telegram.ext import Updater
from Tg_bot_xlsx_parser_OFD import get_handler
from config import TOKEN

# Включаем логирование
basicConfig(format='%(asctime)s: %(filename)s - %(levelname)s - %(message)s', level=DEBUG)
logger = logging.getLogger(__name__)

def main():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(get_handler())
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
