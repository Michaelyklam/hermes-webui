from pathlib import Path
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
PANELS = (ROOT / "static" / "panels.js").read_text(encoding="utf-8")
STYLE = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "i18n.js").read_text(encoding="utf-8")
COMPACT_INDEX = re.sub(r"\s+", "", INDEX)
COMPACT_PANELS = re.sub(r"\s+", "", PANELS)
COMPACT_STYLE = re.sub(r"\s+", "", STYLE)


def test_kanban_has_native_sidebar_rail_and_mobile_tab():
    assert 'data-panel="kanban"' in INDEX
    assert 'data-i18n-title="tab_kanban"' in INDEX
    assert 'onclick="switchPanel(\'kanban\')"' in INDEX
    assert 'data-label="Kanban"' in INDEX
    kanban_section = INDEX[INDEX.find('id="mainKanban"'):INDEX.find('id="mainWorkspaces"')]
    assert "<iframe" not in kanban_section.lower()


def test_kanban_has_sidebar_panel_and_main_board_mounts():
    assert '<div class="panel-view" id="panelKanban">' in INDEX
    assert 'id="kanbanSearch"' in INDEX
    assert 'id="kanbanAssigneeFilter"' in INDEX
    assert 'id="kanbanTenantFilter"' in INDEX
    assert 'id="kanbanIncludeArchived"' in INDEX
    assert 'id="kanbanList"' in INDEX
    assert '<div id="mainKanban" class="main-view">' in INDEX
    assert 'id="kanbanBoard"' in INDEX
    assert 'id="kanbanTaskPreview"' in INDEX


def test_switch_panel_lazy_loads_kanban_and_toggles_main_view():
    assert "'kanban'" in re.search(r"\[[^\]]+\]\.forEach\(p => \{\s*mainEl\.classList", PANELS).group(0)
    assert "if (nextPanel === 'kanban') await loadKanban();" in PANELS
    assert "if (_currentPanel === 'kanban') await loadKanban();" in PANELS


def test_kanban_frontend_uses_relative_api_endpoints():
    assert "'/api/kanban/board" in PANELS
    assert "_kanbanAppendBoardQuery('/api/kanban/tasks/" in PANELS
    assert "api('/api/kanban/config" in PANELS
    assert 'id="kanbanBoardFilter"' in INDEX
    assert "async function switchKanbanBoard" in PANELS
    assert "fetch('/api/kanban" not in PANELS
    assert "kanbanTaskPreview" in PANELS
    assert "classList.add('selected')" in PANELS


def test_kanban_task_detail_renders_read_only_sections():
    assert "function _kanbanRenderTaskDetail" in PANELS
    for payload_key in ("data.comments", "data.events", "data.links", "data.runs"):
        assert payload_key in PANELS
    for section_class in (
        "kanban-detail-section",
        "kanban-detail-comments",
        "kanban-detail-events",
        "kanban-detail-links",
        "kanban-detail-runs",
    ):
        assert section_class in PANELS
    assert "method: 'POST'" not in PANELS[PANELS.find("async function loadKanbanTask"):PANELS.find("function loadTodos")]



def test_kanban_task_detail_renderer_executes_with_realistic_fixture_and_empty_log():
    start = PANELS.index("function _kanbanColumnLabel")
    end = PANELS.index("async function loadKanbanTask")
    fixture = {
        "task": {
            "id": "t_exec",
            "title": "Renderer regression task",
            "body": "Detail body",
            "status": "running",
            "assignee": "webui-test",
            "tenant": "default",
            "priority": 20,
        },
        "comments": [{"author": "reviewer", "body": "Looks good", "created_at": "2026-05-04"}],
        "events": [{"kind": "blocked", "payload": {"reason": "needs QA"}, "created_at": "2026-05-04"}],
        "links": {"parents": ["t_parent"], "children": ["t_child"]},
        "runs": [{"id": 7, "status": "completed", "summary": "verified"}],
        "log": {},
    }
    fixture_json = json.dumps(fixture)
    source_json = json.dumps(PANELS[start:end] + "\nresult = _kanbanRenderTaskDetail(fixture);")
    script = f"""
const vm = require('vm');
const context = {{
  fixture: {fixture_json},
  result: '',
  esc: (value) => String(value ?? '').replace(/[&<>\"]/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}}[ch])),
  t: (key) => ({{
    kanban_comments_count: 'Comments ({{0}})',
    kanban_events_count: 'Events ({{0}})',
    kanban_runs_count: 'Runs ({{0}})',
    kanban_links: 'Links',
    kanban_worker_log: 'Worker log',
    kanban_empty: 'Empty',
    kanban_no_comments: 'No comments',
    kanban_no_events: 'No events',
    kanban_no_runs: 'No runs',
    kanban_block: 'Block',
    kanban_unblock: 'Unblock',
    kanban_no_description: 'No description',
    kanban_parents: 'Parents',
    kanban_children: 'Children',
  }}[key] || key),
  $: () => null,
  api: async () => ({{}}),
  showToast: () => {{}},
}};
vm.runInNewContext({source_json}, context);
for (const expected of ['kanban-detail-comments', 'kanban-detail-events', 'kanban-detail-links', 'kanban-detail-runs', 'kanban-detail-log', 'kanban-comment-form']) {{
  if (!context.result.includes(expected)) throw new Error('missing ' + expected);
}}
if (!context.result.includes('Renderer regression task')) throw new Error('missing task title');
if (!context.result.includes('Empty')) throw new Error('empty log fallback did not render');
"""
    subprocess.run(["node", "-e", script], cwd=ROOT, check=True)



def test_kanban_write_mvp_has_native_controls_and_api_calls():
    assert 'id="kanbanNewTaskBtn"' in INDEX
    assert "async function createKanbanTask" in PANELS
    assert "async function updateKanbanTask" in PANELS
    assert "async function addKanbanComment" in PANELS
    assert "_kanbanAppendBoardQuery('/api/kanban/tasks')" in PANELS
    assert "method: 'POST'" in PANELS
    assert "method: 'PATCH'" in PANELS
    assert "_kanbanAppendBoardQuery('/api/kanban/tasks/' + encodeURIComponent(taskId))" in PANELS
    assert "'/api/kanban/tasks/' + encodeURIComponent(taskId) + '/comments'" in PANELS
    assert "kanban-status-actions" in PANELS
    assert "kanban-comment-form" in PANELS


def test_kanban_board_has_native_css_classes():
    for selector in (
        ".kanban-board",
        ".kanban-column",
        ".kanban-card",
        ".kanban-card-title",
        ".kanban-meta",
        ".kanban-readonly",
    ):
        assert selector in STYLE
    assert "overflow-x:auto" in COMPACT_STYLE


def test_kanban_mobile_layout_stacks_columns_without_horizontal_clipping():
    media_idx = STYLE.find("/* Kanban mobile parity:")
    assert media_idx >= 0
    media_block = STYLE[media_idx:STYLE.find("}\n", STYLE.find(".kanban-comment-form", media_idx)) + 2]
    compact = re.sub(r"\s+", "", media_block)
    assert ".kanban-board{gap:10px;flex-direction:column;overflow-x:visible;}" in compact
    assert ".kanban-board-wrap{padding:10px;overflow-x:hidden;" in compact
    assert ".kanban-column{flex:00auto;min-width:0;max-width:none;width:100%;" in compact



def test_kanban_i18n_keys_exist_in_every_locale_block():
    locale_blocks = re.findall(r"\n\s*([a-z]{2}(?:-[A-Z]{2})?): \{(.*?)\n\s*\},", I18N, flags=re.S)
    assert len(locale_blocks) >= 8
    required_keys = [
        "tab_kanban",
        "kanban_board",
        "kanban_search_tasks",
        "kanban_all_assignees",
        "kanban_all_tenants",
        "kanban_default_board",
        "kanban_switch_board",
        "kanban_include_archived",
        "kanban_visible_tasks",
        "kanban_no_matching_tasks",
        "kanban_unavailable",
        "kanban_read_only",
        "kanban_empty",
        "kanban_comments_count",
        "kanban_events_count",
        "kanban_links",
        "kanban_runs_count",
        "kanban_no_comments",
        "kanban_no_events",
        "kanban_no_runs",
        "kanban_new_task",
        "kanban_add_comment",
    ]
    missing = [
        f"{locale}:{key}"
        for locale, body in locale_blocks
        for key in required_keys
        if re.search(rf"\b{re.escape(key)}\s*:", body) is None
    ]
    assert missing == []



def test_kanban_dashboard_parity_core_controls_are_native():
    assert 'id="kanbanOnlyMine"' in INDEX
    assert 'id="kanbanBulkBar"' in INDEX
    assert 'id="kanbanStats"' in INDEX
    assert "async function nudgeKanbanDispatcher" in PANELS
    assert "async function bulkUpdateKanban" in PANELS
    assert "async function refreshKanbanEvents" in PANELS
    for endpoint in (
        "'/api/kanban/stats'",
        "'/api/kanban/assignees'",
        "'/api/kanban/events?'",
        "'/api/kanban/dispatch?'",
        "'/api/kanban/tasks/bulk'",
        "'/api/kanban/tasks/' + encodeURIComponent(taskId) + '/log?tail=65536'",
        "'/api/kanban/tasks/' + encodeURIComponent(taskId) + '/block'",
        "'/api/kanban/tasks/' + encodeURIComponent(taskId) + '/unblock'",
        "'/api/kanban/boards'",
        "'/api/kanban/boards/' + encodeURIComponent(board) + '/switch'",
    ):
        assert endpoint in PANELS
    assert "setInterval(refreshKanbanEvents" in PANELS
    assert "prompt(" not in PANELS
    assert "confirm(" not in PANELS


def test_kanban_dashboard_parity_i18n_keys_exist():
    locale_blocks = re.findall(r"\n\s*([a-z]{2}(?:-[A-Z]{2})?): \{(.*?)\n\s*\},", I18N, flags=re.S)
    required_keys = [
        "kanban_only_mine",
        "kanban_bulk_action",
        "kanban_nudge_dispatcher",
        "kanban_stats",
        "kanban_worker_log",
        "kanban_block",
        "kanban_unblock",
    ]
    missing = [
        f"{locale}:{key}"
        for locale, body in locale_blocks
        for key in required_keys
        if re.search(rf"\b{re.escape(key)}\s*:", body) is None
    ]
    assert missing == []
