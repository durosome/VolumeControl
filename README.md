# Volume Control Tray App

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Десктопное приложение для управления громкостью через системный трей. Регулируйте звук с помощью горячих клавиш, даже когда окно свёрнуто!

![Скриншот интерфейса](assets/screenshots/tray-menu.png)

## 🌟 Особенности
- Регулировка громкости через `Ctrl+Shift+Up/Down`
- Иконка в системном трее с контекстным меню
- Автосохранение настроек в JSON
- Минималистичный GUI на PyQt6
- Работа в фоновом режиме

## 📦 Установка

### Требования
- Python 3.10+
- Windows 10/11

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/volume-control-tray.git
cd volume-control-tray
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Запустите приложение:
```bash
# На Windows (с правами администратора):
python main.py
```

## 🛠 Настройка
Создайте файл `config.json`:
```json
{
  "hotkeys": {
    "volume_up": "Ctrl+Shift+Up",
    "volume_down": "Ctrl+Shift+Down"
  }
}
```

## 🖥 Сборка в EXE
1. Установите PyInstaller:
```bash
pip install pyinstaller
```

2. Соберите приложение:
```bash
pyinstaller --onefile --windowed --icon=assets/icons/icon.ico main.py
```

## 📂 Структура проекта
```
volume-control-tray/
├── app/
│   ├── core/            # Логика управления звуком
│   ├── ui/              # Окно настроек и трей
│   └── utils/           # Логирование и конфиги
├── assets/
│   └── icons/           # Иконки приложения
└── tests/
```

## 🤝 Участие в разработке
1. Создайте форк репозитория
2. Добавьте изменения в новую ветку:
```bash
git checkout -b feature/awesome-feature
```
3. Запушьте изменения:
```bash
git push origin feature/awesome-feature
```
4. Создайте Pull Request

## 📜 Лицензия
[MIT License](LICENSE)

---

> **Важно**  
> Для глобальных горячих клавиш может потребоваться запуск от администратора.
