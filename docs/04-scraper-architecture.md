# Архитектура скраппера

## Обзор

Скраппер собирает данные о компаниях с Яндекс.Карт и 2ГИС через headless-браузер (Playwright). Результаты дедуплицируются, обогащаются ИНН через DaData, и кешируются.

## Компоненты

### 1. QueryParser (`query_parser.py`)

Разбирает текстовый запрос на структуру:
```
"рестораны Сочи" → ParsedQuery(category="рестораны", location="Сочи", is_valid=True)
```

### 2. TwoGisScrapper (`twogis.py`)

Парсит 2ГИС через Playwright:
- URL: `https://2gis.ru/search/{query}`
- Скроллит страницу для загрузки всех результатов
- Извлекает данные из DOM через JavaScript (ссылки `/firm/ID`)
- Данные: название, адрес, категория, рейтинг, кол-во отзывов

### 3. YandexMapsScrapper (`yandex_maps.py`)

Парсит Яндекс.Карты через Playwright:
- URL: `https://yandex.ru/maps/search/{query}`
- Аналогичный подход: скролл + JS-извлечение (ссылки `/org/ID`)
- Настраиваемые задержки для антибана

### 4. Deduplicator (`deduplicator.py`)

Удаляет дубликаты по `(name.lower(), address.lower())`.

### 5. InnFinder (`inn_finder.py`)

Ищет ИНН компаний через DaData API:
- API: `https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party`
- Бесплатно: 10,000 запросов/день
- Также получает: ФИО директора, юр. форму, полное юр. название

### 6. Cache (`cache.py`)

Кеширует результаты в JSON-файлы:
- Путь: `data/cache/{category}_{location}.json`
- TTL: 24 часа (`scrapper_cache_ttl_hours`)

### 7. LLM Parser (`llm_parser.py`)

Fallback для сложных запросов, которые не удалось разобрать через QueryParser. Использует LLM (OpenAI/GigaChat/YandexGPT).

## Оркестратор (`orchestrator.py`)

Координирует весь процесс:

```
1. QueryParser.parse(query)
2. Проверка кеша
3. TwoGisScrapper.scrape(parsed) + YandexMapsScrapper.scrape(parsed)
   (последовательно или параллельно через scrape_parallel())
4. Deduplicator.deduplicate(all_companies)
5. InnFinder.enrich_companies(unique)
6. Сохранение в кеш
```

## Текущие данные в кеше

| Запрос | Компаний | Источник |
|--------|----------|----------|
| автосервисы Москва | 200 | 2ГИС + Яндекс |
| рестораны Москва | 173 | 2ГИС + Яндекс |
| рестораны Сочи | 10 | 2ГИС + Яндекс |
| стоматологии Москва | 93 | 2ГИС + Яндекс |
| фитнес Москва | 307 | 2ГИС + Яндекс |

## Интеграция с ботом

FSM скраппера (`handlers/scrapper.py`):
1. Пользователь выбирает "Поиск компаний"
2. Вводит запрос или выбирает из популярных
3. Скраппер работает с progress callback
4. Результат можно скачать как Excel
5. Результат можно передать в outreach для рассылки
