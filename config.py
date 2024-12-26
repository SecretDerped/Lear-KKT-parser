import os

# Токен доступа к боту телеграм
TOKEN = '7849560687:AAEl9BEAKenqidtyFd3gSUT1T24Rk3dkjEA'

# Cсылки на xlsx файл
DOWNLOAD_URLS = [
    'https://pk.ofd.ru/api/partner/v3/b3e111d3-f35e-4e8c-90ea-caa21c353b05/kkt/xlsx?filter={"version":3,"b2bAgreementId":"b3e111d3-f35e-4e8c-90ea-caa21c353b05","page":0,"pageSize":10,"groupPage":0,"groupPageSize":10}',
    'https://pk.ofd.ru/api/partner/v3/c3efe88c-ce2a-4d12-8cfe-0beba2254c48/kkt/xlsx?filter={"version":3,"b2bAgreementId":"c3efe88c-ce2a-4d12-8cfe-0beba2254c48","page":0,"pageSize":10,"groupPage":0,"groupPageSize":10}'
]

# Параметры авторизации
LOGIN_URL = "https://pk.ofd.ru/login"
USERNAME = "api@le-ar.ru"
PASSWORD = "cX6u97CakGmYR5Wd3jt6"

# Путь для загрузки файлов
DOWNLOAD_DIR = "/root/Downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

