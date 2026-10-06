# live-diagram · Diagramas de arquitectura vivos

[English](../README.md) | [简体中文](zh-CN.md) | [日本語](ja.md) | [한국어](ko.md) | **Español** | [Português](pt-BR.md) | [Русский](ru.md)

> Convierte **un solo archivo de configuración JSON** en un diagrama de arquitectura animado de maquetación fija y siempre en ejecución: paquetes fluyendo por los cables, registros que se desplazan, contadores ticking, barras que cambian de estado y alarmas que se encienden dash por dash. Salida en **mp4 H.264** (X / Xiaohongshu / TikTok / Bilibili) o en una **página web en vivo** abrible en cualquier navegador. También es un [skill para agentes de IA](../SKILL.md).

![preview](../docs/media/memory-vault-panel.webp)

*En bucle: panel de AI Memory Vault renderizado con este skill (tema oscuro de GitHub; cifras ilustrativas).*

## Ideas centrales

Reescrito a partir del *método* de [ythx-101/live-panel-skill](https://github.com/ythx-101/live-panel-skill); todo el código es una implementación independiente:

- **La maquetación nunca se mueve; lo que se mueve es el estado del sistema.** Cualquier fotograma es un diagrama completo y legible.
- **Renderizado determinista.** La página expone `window.seek(t)`; todo cambio visible es una función pura de `t` (sin reloj, sin `Math.random`, sin animación CSS) → fotogramas reproducibles y verificables.
- **Una sola verdad en todas partes.** Los registros los generan las mismas máquinas de estado que animan los paneles: el número del log es el de la barra, por construcción.
- **¿Sin datos reales? Indica "ilustrativo".**

## Temas (`theme.preset`)

`github-dark` / `github-light` (paleta oficial de GitHub) · `blueprint` (plano técnico) · `terminal-dark` (terminal) · `light-pastel` (infografía pastel). Lienzos: `4:5` / `3:4` / `1:1` / `9:16` / `16:9`.

## Uso

Requisitos: Python 3.8+ (solo librería estándar), Chrome/Chromium/Edge, ffmpeg.

```bash
python scripts/livediagram.py render --config my.json --out my.mp4 --html-out my.html --crf 10 --preset slow
python scripts/livediagram.py check  --config my.json --out-dir frames --repeat
python scripts/livediagram.py build  --config my.json --out page.html
```

Como skill de IA: coloca esta carpeta en el directorio de skills de tu agente (`~/.zcode/skills/`, etc.).

## Documentación

[SKILL.md](../SKILL.md) · [motion-grammar.md](../references/motion-grammar.md) · [config-schema.md](../references/config-schema.md) · [ejemplo completo](../examples/rag-pipeline/). Más detalle en el [README en inglés](../README.md) y el [README en chino](zh-CN.md).

## Licencia

[MIT](../LICENSE) · Gramática de movimiento aprendida del clip de [@thedelost](https://x.com/thedelost) (implementación independiente, sin su código).
