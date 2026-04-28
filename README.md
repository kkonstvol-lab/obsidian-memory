# obsidian-memory

Скил для Claude Code и Codex-style агентов — система постоянной памяти для AI-агентов на базе Obsidian. Объединяет LLM Wiki, Robby Palace, Self-Improvement Loop, optional Codex hooks и Graphify knowledge graph в единый контур.

**Claude — программист. Obsidian — IDE. Wiki — кодовая база.**

---

## Что делает

Четыре взаимосвязанные системы внутри одного vault:

**LLM Wiki** (`wiki/`) — накапливаемая база знаний:
- Ingest любого источника (PDF, статья, книга, разговор) → структурированная страница-конспект
- Извлечение сущностей и концептов → связанные страницы через wikilinks
- Организация по доменам → тематические Maps of Content
- Еженедельный LINT → битые ссылки, сироты, устаревший контент

**Robby Palace** (`wiki/wings/` + `wiki/drawers/`) — постоянная память о людях и проектах:
- Wing для любого человека или проекта → 5 залов: Facts, Events, Discoveries, Preferences, Advice/Decisions
- Каждая сессия создаёт неизменяемый Drawer (лог сессии) → COMPILE обновляет Wings автоматически
- Провенанс: каждый факт в Wing ссылается на исходный Drawer

**Self-Improvement Loop** (`{private}/memory_corrections.md` + 3 файла) — агент учится на ошибках:
- Логировать каждую логическую/процессную ошибку → обнаруживать паттерны
- Трекать идеи улучшений → внедрять в скилы
- Ежедневный HEARTBEAT cron в 10:00 → читает corrections, поверхностно выявляет паттерны, остаётся калиброванным

**Codex Hooks** (`assets/codex/hooks/`) — optional lifecycle-интеграция Codex с Obsidian:
- `SessionStart` загружает bounded operational context из vault
- `PostToolUse` после `git push` напоминает обновить `memory_in_progress.md`
- Источник правды — Obsidian memory, не GitHub Issues

**Graphify Knowledge Graph** (`memory/graph/`) — семантический слой поверх Wiki:
- Автоматически извлекает связи между страницами через wikilinks → граф (NetworkX)
- Leiden-кластеризация → тематические communities → кандидаты на новые MOC
- Beads-style очередь ревью `GRAPH_READY.md`: готовые действия, блокеры, решения человека
- Устойчивые IDs для узлов, связей и предложений; `review-state.jsonl` для accepted/skipped/obsolete
- MCP-сервер graphify → агенты делают `query_graph` перед grep
- Скрипты не редактируют `wiki/` и `raw-sources/`, только генерируют отчёты

---

## Мультиагентный сетап (Claude Code + Codex)

Скил поддерживает работу нескольких агентов из одного vault без смешивания контекстов:

```
vault/
├── 12-shared/    ← мировые факты (decisions, projects, clients, tools) — оба агента
├── 12-claude/    ← приватная оперативка Claude Code
├── 12-codex/     ← приватная оперативка Codex
└── wiki/         ← база знаний — общая, оба агента
```

Каждый агент читает свой entry-point (`CLAUDE.md` или `AGENTS.md`), узнаёт `agent_id` и пути к своему `{private}` и общему `{shared}`. Self-Improvement Loop работает независимо для каждого — ошибки Codex не попадают в heartbeat Claude и наоборот.

Codex может дополнительно использовать lifecycle hooks из `assets/codex/hooks/`, чтобы подтягивать свой `{private}/memory_in_progress.md` на старте новой сессии и получать напоминание обновить Obsidian memory после `git push`.

Для одного агента: используй `memory/` как единый корень, мультиагентное разделение опционально.

---

## Установка

```bash
git clone https://github.com/kkonstvol-lab/obsidian-memory ~/.claude/skills/obsidian-memory
```

Перезапустить Claude Code. Скил доступен как `/obsidian-memory`.

### Optional: Codex hooks

Codex-интеграция устанавливается отдельно, потому что Codex hooks являются experimental:

```bash
mkdir -p ~/.codex/hooks
cp assets/codex/hooks/codex-session-start.js ~/.codex/hooks/
cp assets/codex/hooks/codex-post-tool-use.js ~/.codex/hooks/
cp assets/codex/hooks/hooks.json.template ~/.codex/hooks.json
cp assets/codex/memory_in_progress.md /path/to/obsidian-vault/12-codex/memory_in_progress.md
```

Задать vault path:

```bash
export OBSIDIAN_VAULT_PATH="/path/to/obsidian-vault"
export OBSIDIAN_AGENT_ID="codex"
```

Подробнее: `references/codex-hooks.md`.

---

## Быстрый старт

1. **Настроить vault** — следовать `references/setup.md`
2. **Добавить схему** — скопировать `assets/vault-CLAUDE.md` → `wiki/CLAUDE.md` в vault
3. **Скопировать шаблоны** — `assets/templates/` → `templates/` в vault
4. **Настроить identity** — скопировать `assets/identity.md` → `identity.md` в корень vault, заполнить имя и роль
5. **Первый ingest** — "ingest [название источника] в мой wiki"
6. **Первый session-summary** — в конце сессии `/session-summary` → создаёт Drawer → `/compile` → обновляет Wings

---

## Структура файлов скила

```
obsidian-memory/
├── SKILL.md                     # Главный файл скила — триггеры + все операции
├── references/
│   ├── wiki-schema.md           # Полная схема wiki: типы страниц, frontmatter, теги, workflows
│   ├── memory-schema.md         # Memory layer: типы файлов, порядок загрузки, routing
│   ├── graphify.md              # Graphify + Beads-style review queue
│   ├── codex-hooks.md           # Optional Codex hooks для Obsidian memory
│   └── setup.md                 # Пошаговая инструкция установки
└── assets/
    ├── graph/
    │   ├── extract_vault.py
    │   ├── suggest_wikilinks.py
    │   ├── review-state.jsonl
    │   └── tests/
    ├── codex/
    │   ├── hooks/
    │   │   ├── codex-session-start.js
    │   │   ├── codex-post-tool-use.js
    │   │   └── hooks.json.template
    │   ├── memory_in_progress.md
    │   └── env.example
    ├── vault-CLAUDE.md          # Drop-in схема для wiki/CLAUDE.md
    ├── vault-index.md           # Шаблон wiki/index.md (с секциями Wings + Drawers)
    ├── vault-log.md             # Шаблон wiki/log.md
    ├── identity.md              # Шаблон identity.md (L0 контекст)
    └── templates/
        ├── wiki-summary.md      # Конспект источника
        ├── wiki-entity.md       # Человек/компания/инструмент
        ├── wiki-concept.md      # Методология/фреймворк
        ├── wiki-synthesis.md    # Кросс-источниковый анализ
        ├── wiki-domain.md       # Map of Content
        ├── wing-person.md       # Wing человека — 5 залов
        ├── wing-project.md      # Wing проекта — 5 залов
        └── drawer.md            # Неизменяемый лог сессии
```

---

## Операции

| Операция | Когда использовать |
|----------|-------------------|
| SETUP | Первичная инициализация vault |
| INGEST | Добавить источник в wiki |
| QUERY | Поиск и синтез знаний (сначала graph query, потом grep) |
| LINT | Еженедельная проверка (wiki + Palace) |
| GRAPH | Регенерация knowledge graph после bulk ingest |
| MEMORY | Загрузка контекста агента в начале сессии |
| CODEX-HOOKS | Optional Codex lifecycle hooks для Obsidian memory |
| COMPILE | После сессии — обработать Drawers в Wings |
| WING | Создать Wing человека или проекта |

---

## Структура vault после настройки

```
vault/
├── identity.md             ← L0 контекст, каждая сессия (~100 токенов)
├── AGENTS.md               ← entry point для второго агента (опционально)
├── wiki/
│   ├── CLAUDE.md           ← схема (из assets/vault-CLAUDE.md)
│   ├── index.md            ← каталог всех страниц
│   ├── log.md              ← лог операций
│   ├── summaries/          ← один файл на источник
│   ├── entities/           ← люди, компании, инструменты (что это ЕСТЬ)
│   ├── concepts/           ← фреймворки, методологии
│   ├── synthesis/          ← кросс-источниковый анализ
│   ├── domains/            ← тематические хабы (Maps of Content)
│   ├── wings/              ← Robby Palace: профили людей и проектов
│   │   ├── person-{slug}.md
│   │   └── project-{slug}.md
│   └── drawers/            ← неизменяемые логи сессий
├── output/
│   ├── dashboards/
│   └── reports/
├── memory/                 ← одиночный агент
│   ├── memory_active.md
│   ├── memory_in_progress.md
│   ├── memory_decisions.md
│   ├── memory_corrections.md
│   ├── memory_improvements_backlog.md
│   ├── memory_metrics.md
│   ├── memory_heartbeat.md
│   └── graph/              ← graphify knowledge graph
│       ├── extract_vault.py
│       ├── suggest_wikilinks.py
│       ├── review-state.jsonl
│       ├── tests/
│       └── graphify-out/
│           ├── graph.json        (git-ignored)
│           ├── GRAPH_REPORT.md
│           ├── GRAPH_READY.md
│           └── missing-links.md
└── raw-sources/
    ├── pdfs/
    ├── articles/
    └── converted/
```

**Мультиагентный вариант** — вместо единого `memory/` используется:
```
12-shared/    ← memory_decisions, memory_projects, memory_tools, graph/
12-claude/    ← memory_active, memory_in_progress, memory_corrections, memory_heartbeat, ...
12-codex/     ← то же, отдельно
```

---

## Ключевые принципы

1. **Writes required** — каждая сессия, которая читает, должна что-то записать
2. **Separation** — wiki = знания, memory = оперативный контекст, никогда не дублировать
3. **Quality > quantity** — 5 связанных страниц лучше 20 изолированных
4. **Compound context** — каждая сессия делает следующую быстрее
5. **Corrections > rules** — конкретные логи ошибок сильнее абстрактных инструкций
6. **Drawers immutable** — логи сессий не редактируются после создания
7. **Entity vs Wing** — entity = что это ЕСТЬ; wing = ваши отношения с этим
8. **Graph before grep** — при QUERY сначала `query_graph`, потом файловый поиск
9. **Private isolation** — в мультиагентном сетапе ошибки и heartbeat каждого агента хранятся отдельно

---

## Self-Improvement Loop

Четыре файла, которые работают вместе:

| Файл | Назначение | Кто пишет |
|------|-----------|-----------|
| `memory_corrections.md` | Логические/процессные ошибки (не стиль) | Правки пользователя + session-summary |
| `memory_improvements_backlog.md` | Идеи улучшений (Active/Done) | HEARTBEAT + session-summary |
| `memory_metrics.md` | Еженедельный снапшот | HEARTBEAT каждое воскресенье |
| `memory_heartbeat.md` | Ежедневный self-check лог | HEARTBEAT cron в 10:00 |

**Уровни эскалации:** `memory_corrections.md` (открытая ошибка) → при `repeat_count >= 2` → `memory_decisions.md` (дурное правило) → при следующем agent-introspection → `CLAUDE.md` (часть identity агента).

**HEARTBEAT cron:** создаётся через `mcp__scheduled-tasks__create_scheduled_task` с `cronExpression: "0 10 * * *"`. Читает corrections, выявляет повторяющиеся паттерны (2+ одинаковых root cause), флагирует застойные backlog items.

---

## Graphify Knowledge Graph

Опциональный слой, который добавляет semantic search поверх wiki:

```bash
# Установка
pip install graphifyy

# Скопировать bundled graph layer
cp -R assets/graph/* /path/to/vault/memory/graph/

# Регенерация графа
cd /path/to/vault/memory/graph
python extract_vault.py
python suggest_wikilinks.py

# Проверка
python tests/test_graphify_beads.py

# Добавить MCP-сервер в ~/.claude.json
{
  "mcpServers": {
    "graphify": {
      "command": "python",
      "args": ["-m", "graphify.serve", "memory/graph/graphify-out/graph.json"],
      "type": "stdio"
    }
  }
}
```

После этого агент может использовать `mcp__graphify__query_graph` для семантических запросов к графу перед тем как делать grep по файлам.

`GRAPH_READY.md` — это очередь человеческого ревью. Принятые/отклонённые решения фиксируются в `review-state.jsonl`, а не ручной правкой generated reports. Подробнее: `references/graphify.md`.

---

## Требования

- Claude Code со поддержкой скилов
- Для Codex hooks: Codex runtime с включённой experimental hooks support; по официальной документации Windows support сейчас временно отключён
- Obsidian с плагинами Dataview + Templater
- Опционально: obsidian-git (синхронизация между устройствами), mcpvault (MCP доступ к vault), graphify (knowledge graph)

---

Создан из production-использования. Вдохновлён LLM Wiki pattern (Tobi Lutke / Karpathy), MemPalace (Milla Jovovich) и ALIVE memory system (witcheer).
