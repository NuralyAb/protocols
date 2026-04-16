---
id: pedagogical-council
name: Заседание педагогического совета
description: Педсовет школы / колледжа / вуза.
language: ru
sections:
  - header
  - participants
  - agenda
  - items
  - signatures
---

# {{org}}

## ПРОТОКОЛ № {{number}}
## заседания педагогического совета

{{city}}                                                          {{date}}

Время: {{time_start}}–{{time_end}}
Место: {{place}}

---

**Председатель:** {{chair}}
**Секретарь:** {{secretary}}

**Присутствовали ({{present|count}} чел.):**
{{present}}

**Отсутствовали (с указанием причины):**
{{absent}}

**Приглашённые:** {{invited}}

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

**РЕШИЛИ:** {{resolved}}

{{/items}}

---

## ПОРУЧЕНИЯ:

{{#action_items}}
- {{task}} — отв. {{assignee}}, срок: {{deadline}}
{{/action_items}}

---

Председатель педсовета       _________________ {{chair}}

Секретарь                    _________________ {{secretary}}
