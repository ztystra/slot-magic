# Contributing

Спасибо за интерес к проекту!

## Быстрый старт

1. Fork репозитория
2. `git clone https://github.com/YOUR_USERNAME/slot-magic.git`
3. `python3 -m venv venv && source venv/bin/activate`
4. `pip install -r requirements.txt`
5. `cp .env.example .env` и настрой токен
6. `python bot.py` для запуска

## Development Workflow

1. Создайте ветку: `git checkout -b feature/amazing-feature`
2. Внесите изменения
3. Протестируйте: `python bot.py`
4. Закоммитьте: `git commit -m "feat: amazing feature"`
5. Запушьте: `git push origin feature/amazing-feature`
6. Откройте Pull Request

## Code Style

- Python 3.11+
- PEP 8 (flake8)
- Type hints
- Docstrings для всех функций

## Testing

- Тестируйте бота в Telegram перед коммитом
- Проверяйте все команды
- Убедитесь что запись работает

## Questions?

Откройте [issue](https://github.com/ztystra/slot-magic/issues) с вопросом.
