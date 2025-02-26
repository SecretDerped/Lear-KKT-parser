# Собираем новый образ с новым тегом, НЕ убиваем старый контейнер
docker build -t ofd_parser_bot:new .

# Останавливаем старый, удаляем старый образ
docker stop ofd_parser_bot_container
docker rm ofd_parser_bot_container
docker rmi ofd_parser_bot:latest

# Переименовываем "new" -> "latest"
docker tag ofd_parser_bot:new ofd_parser_bot:latest
docker rmi ofd_parser_bot:new

# Запуск навого контейнера с сохранением кеша браузера с предыдущей сборки
docker run -itd -v /host/browser_profile:/root/browser_profile --name ofd_parser_bot_container --restart=always ofd_parser_bot:latest

# Очистка мусора
docker system prune -f 

# Вывод логов в терминал
docker logs -f ofd_parser_bot_container
