<div align="center">
  <img src="assets/bongo_icon.png" width="160" alt="Bongo Cat Auto Clicker Icon">
  <h1>Bongo Cat Auto Clicker 🐾</h1>
  <p><b>Быстрый, плавный и умный автокликер для BongoCat (Steam) без лагов и спама кнопками</b></p>

  <p>
    <a href="https://github.com/lokalizator-repo/BongoCat-Autoclicker/releases/latest"><img src="https://img.shields.io/github/v/release/lokalizator-repo/BongoCat-Autoclicker?color=brightgreen&label=Download%20EXE" alt="Download EXE"></a>
    <img src="https://img.shields.io/badge/Platform-Windows_10_|_11-0078D6?logo=windows" alt="Platform">
    <img src="https://img.shields.io/badge/Dependencies-Zero-success" alt="Zero Dependencies">
    <img src="https://img.shields.io/badge/License-MIT-blue" alt="License">
  </p>
</div>

---

### 🐾 В чем фишка?

Обычные автокликеры и макросы (Razer, Logitech, стандартные кликеры) спамят виртуальными кликами мыши или клавиатуры. Из-за этого:
- Сбивается 2x-перемотка на YouTube при зажатии пробела или ЛКМ.
- При нажатии `Win` залипают меню или открывается проектор `Win + P`.
- Клики теряются, потому что игра не успевает их обрабатывать.

**Bongo Cat Auto Clicker работает иначе:** он отправляет клики напрямую во внутренний канал игры (`Named Pipe IPC`).
- ⚡ **Ноль конфликтов в Windows** — мышь и клавиатура полностью свободны. Можно спокойно печатать, играть или смотреть видео.
- 🚀 **Любая скорость** — от умеренных 1,000 кликов до максимума игры (2.14 млрд).
- 🎨 **Красивый интерфейс** — современный шрифт Bahnschrift, скругленные карточки, плавная логарифмическая шкала и темная тема кнопок.

---

### 🚀 Быстрый старт

#### Вариант 1: Готовый `.exe` (Без установки Python)
1. Скачай **[BongoCatAutoClicker.exe](https://github.com/lokalizator-repo/BongoCat-Autoclicker/releases/latest)** из раздела [Releases](https://github.com/lokalizator-repo/BongoCat-Autoclicker/releases).
2. Запусти игру **BongoCat** в Steam.
3. Запусти скачанный файл и нажми **F8** для старта / паузы.

#### Вариант 2: Запуск из исходников
Если на компьютере установлен Python 3.8+:
```bash
git clone https://github.com/lokalizator-repo/BongoCat-Autoclicker.git
cd BongoCat-Autoclicker
run.bat
```

---

### ⌨️ Горячие клавиши

| Клавиша | Действие |
| :---: | :--- |
| **`F8`** | **Старт / Пауза** (работает глобально в фоне, даже если окно свернуто) |
| **`F10`** | **Быстрый выход** из программы |

---

### ⚡ Пресеты скорости

В выпадающей панели **Speed Settings** можно выбрать готовый режим или ввести любое число вручную (поддерживаются суффиксы `k`, `m`, `b`, `max`):

| Пресет | Кликов за такт | Скорость в секунду | Описание |
| :---: | :---: | :---: | :--- |
| **1,000** | 1,000 | ~11,000 CPS | Аккуратный ровный фарм |
| **100,000** | 100,000 | ~1.1M CPS | Быстрый набор очков |
| **1,000,000** | 1,000,000 | ~11.1M CPS | Десятки миллионов за секунды |
| **100,000,000** | 100,000,000 | ~1.11B CPS | Миллиард очков в секунду |
| **MAX** | 2,147,483,646 | 2.14B / такт | Максимальный лимит игры за один клик |

> 💡 **Почему счетчик останавливается на ~2.14 млрд?**  
> В самой игре BongoCat счетчик очков написан на 32-битном числе (`int32`), предел которого равен `2,147,483,646`. Выше игра физически не может прибавить очки. Потратьте накопленные очки в игровом магазине (на шапки и скины), и фарм снова продолжится!

---

### 📄 Лицензия

Проект распространяется под свободной лицензией [MIT](LICENSE).
