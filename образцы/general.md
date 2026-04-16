---
id: general
name: Общий протокол заседания
description: Универсальная форма по типовой структуре делопроизводства РК.
language: ru
sections:
  - header
  - participants
  - agenda
  - items
  - action_items
  - signatures
---

# {{org}}

## ПРОТОКОЛ № {{number}}

**{{body}}**

{{city}}                                                          {{date}}

Время начала: {{time_start}}
Время окончания: {{time_end}}
Место проведения: {{place}}

---

**Председатель:** {{chair}}
**Секретарь:** {{secretary}}

**Присутствовали ({{present|count}} чел.):**
{{present}}

**Отсутствовали:**
{{absent}}

**Приглашённые:**
{{invited}}

{{quorum}}

---

## ПОВЕСТКА ДНЯ:

{{agenda}}

---

{{#items}}
### {{no}}. {{title}}

**СЛУШАЛИ:** {{heard}}

**ВЫСТУПИЛИ:**
{{#spoke}}
- {{speaker}}: {{text}}
{{/spoke}}

**ГОЛОСОВАЛИ:** «за» — {{vote.for}}, «против» — {{vote.against}}, «воздержались» — {{vote.abstain}}.

**ПОСТАНОВИЛИ:** {{resolved}}

{{/items}}

---

## ПОРУЧЕНИЯ:

{{#action_items}}
- {{task}} — отв. {{assignee}}, срок: {{deadline}}
{{/action_items}}

---

Председатель                _________________ {{chair}}

Секретарь                   _________________ {{secretary}}
