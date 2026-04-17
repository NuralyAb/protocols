---
id: casual
name: Свободный разговор / Заметки встречи
description: Неформальная встреча без жёсткой структуры. Темы, упоминания, договорённости, следующие шаги.
language: ru
sections:
  - summary
  - topics
  - mentions
  - agreements
  - next_steps
---

# Заметки встречи

**Дата:** {{date}}
**Участники:** {{participants}}
**Длительность:** {{duration}}

---

## Краткое содержание

{{summary}}

---

## О чём говорили

{{#topics}}
- **{{topic}}** — {{notes}}
{{/topics}}

---

## Упоминания (люди, компании, цифры, даты)

{{#mentions}}
- {{item}}
{{/mentions}}

---

## Договорённости (явные или подразумеваемые)

{{#agreements}}
- {{text}}{{#by}} — *{{by}}*{{/by}}
{{/agreements}}

---

## Следующие шаги

{{#next_steps}}
- {{action}}{{#owner}} — *{{owner}}*{{/owner}}{{#deadline}} · до {{deadline}}{{/deadline}}
{{/next_steps}}

---

_Заметки сгенерированы на основе стенограммы. Неформальная встреча — возможны неявные выводы из контекста._
