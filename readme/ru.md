# live-diagram · Живые архитектурные диаграммы

[English](../README.md) | [简体中文](zh-CN.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Português](pt-BR.md) | **Русский**

> Превращает **один JSON-конфиг** в анимированную архитектурную диаграмму с фиксированной компоновкой, которая всегда «работает»: пакеты бегут по проводам, логи прокручиваются, счётчики тикают, шкалы меняют состояние, тревоги загораются по очереди. Вывод — **mp4 (H.264)** (X / Xiaohongshu / TikTok / Bilibili) или **живая веб-страница**, открывающаяся в любом браузере. Также это [skill для ИИ-агентов](../SKILL.md).

![preview](../docs/media/memory-vault-panel.webp)

*Циклическое воспроизведение: живая панель AI Memory Vault, отрисованная этим skill'ом (тёмная тема GitHub; цифры условные).*

## Ключевые идеи

Переписано на основе *метода* [ythx-101/live-panel-skill](https://github.com/ythx-101/live-panel-skill); весь код — самостоятельная реализация:

- **Компоновка не двигается — двигается состояние системы.** Любой отдельно взятый кадр — законченная, читаемая диаграмма.
- **Детерминированный рендеринг.** Страница предоставляет `window.seek(t)`; каждое видимое изменение — чистая функция от `t` (без часов, без `Math.random`, без CSS-анимаций) → кадры воспроизводимы и проверяемы.
- **Всюду одна правда.** Логи порождаются теми же автоматами состояний, что двигают панели: число в логе равно числу на шкале — по построению.
- **Нет реальных данных — помечай как «условные».**

## Темы (`theme.preset`)

`github-dark` / `github-light` (официальная палитра GitHub) · `blueprint` (чертёжный стиль) · `terminal-dark` (терминал) · `light-pastel` (пастельная инфографика). Холсты: `4:5` / `3:4` / `1:1` / `9:16` / `16:9`.

## Использование

Требования: Python 3.8+ (только стандартная библиотека), Chrome/Chromium/Edge, ffmpeg.

```bash
python scripts/livediagram.py render --config my.json --out my.mp4 --html-out my.html --crf 10 --preset slow
python scripts/livediagram.py check  --config my.json --out-dir frames --repeat
python scripts/livediagram.py build  --config my.json --out page.html
```

Как skill для ИИ: положите эту папку в каталог skills вашего агента (`~/.zcode/skills/` и т.п.).

## Документация

[SKILL.md](../SKILL.md) · [motion-grammar.md](../references/motion-grammar.md) · [config-schema.md](../references/config-schema.md) · [полный пример](../examples/rag-pipeline/). Подробнее — в [англоязычном README](../README.md) и [китайском README](zh-CN.md).

## Лицензия

[MIT](../LICENSE) · Грамматика движения изучена по клипу [@thedelost](https://x.com/thedelost) (самостоятельная реализация, без оригинального кода).
