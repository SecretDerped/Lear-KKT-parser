from logging import basicConfig, getLogger, INFO
from telegram.ext import Updater
from Tg_bot_xlsx_parser_OFD import get_handler
from config import TOKEN

# Включаем логирование
basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
            level=INFO)

def main():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(get_handler())
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
