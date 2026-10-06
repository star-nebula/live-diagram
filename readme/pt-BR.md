# live-diagram · Diagramas de arquitetura vivos

[English](../README.md) | [简体中文](zh-CN.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | **Português** | [Русский](ru.md)

> Transforma **um único arquivo JSON** em um diagrama de arquitetura animado, de layout fixo e sempre em execução: pacotes fluindo pelos fios, logs rolando, contadores girando, barras mudando de estado e alarmes acendendo dash por dash. Saída em **mp4 H.264** (X / Xiaohongshu / TikTok / Bilibili) ou em uma **página web ao vivo** que abre em qualquer navegador. Também é um [skill para agentes de IA](../SKILL.md).

![preview](../docs/media/memory-vault-panel.webp)

*Em loop: painel do AI Memory Vault renderizado com este skill (tema escuro do GitHub; números ilustrativos).*

## Ideias centrais

Reescrito a partir do *método* do [ythx-101/live-panel-skill](https://github.com/ythx-101/live-panel-skill); todo o código é uma implementação independente:

- **O layout nunca se move; o que se move é o estado do sistema.** Qualquer quadro é um diagrama completo e legível.
- **Renderização determinística.** A página expõe `window.seek(t)`; toda mudança visível é uma função pura de `t` (sem relógio, sem `Math.random`, sem animação CSS) → quadros reproduzíveis e verificáveis.
- **Uma única verdade em todo lugar.** Os logs são gerados pelas mesmas máquinas de estado que animam os painéis: o número do log é o da barra, por construção.
- **Sem dados reais? Marque como "ilustrativo".**

## Temas (`theme.preset`)

`github-dark` / `github-light` (paleta oficial do GitHub) · `blueprint` (prancheta técnica) · `terminal-dark` (terminal) · `light-pastel` (infográfico pastel). Telas: `4:5` / `3:4` / `1:1` / `9:16` / `16:9`.

## Uso

Requisitos: Python 3.8+ (somente biblioteca padrão), Chrome/Chromium/Edge, ffmpeg.

```bash
python scripts/livediagram.py render --config my.json --out my.mp4 --html-out my.html --crf 10 --preset slow
python scripts/livediagram.py check  --config my.json --out-dir frames --repeat
python scripts/livediagram.py build  --config my.json --out page.html
```

Como skill de IA: coloque esta pasta no diretório de skills do seu agente (`~/.zcode/skills/`, etc.).

## Documentação

[SKILL.md](../SKILL.md) · [motion-grammar.md](../references/motion-grammar.md) · [config-schema.md](../references/config-schema.md) · [exemplo completo](../examples/rag-pipeline/). Mais detalhes no [README em inglês](../README.md) e no [README em chinês](zh-CN.md).

## Licença

[MIT](../LICENSE) · Gramática de movimento aprendida do clipe de [@thedelost](https://x.com/thedelost) (implementação independente, sem o código original).
