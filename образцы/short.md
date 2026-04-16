---
id: short
name: Краткий протокол (планёрка)
description: Сжатая форма для оперативных совещаний. Только повестка, решения, поручения.
language: ru
sections:
  - header
  - agenda
  - decisions
  - action_items
---

# {{org}}

## ПРОТОКОЛ № {{number}} оперативного совещания

{{city}}, {{date}}, {{time_start}}–{{time_end}}

**Председатель:** {{chair}}
**Секретарь:** {{secretary}}
**Присутствовали:** {{present}}

---

### Повестка:
{{agenda}}

---

### Решения:

{{#items}}
**{{no}}. {{title}}**
Решение: {{resolved}}

{{/items}}

---

### Поручения:

| Поручение | Исполнитель | Срок |
|---|---|---|
{{#action_items}}
| {{task}} | {{assignee}} | {{deadline}} |
{{/action_items}}

---

Председатель: _____________ {{chair}}
Секретарь:    _____________ {{secretary}}
