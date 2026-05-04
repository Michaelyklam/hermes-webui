"""Behavioral Kanban UI tests that execute real static/panels.js renderers."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PANELS_JS = REPO_ROOT / "static" / "panels.js"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not on PATH")

_DRIVER_SRC = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels = {
  kanban_task: 'Task', kanban_no_description: 'No description', kanban_comments_count: 'Comments ({0})',
  kanban_events_count: 'Events ({0})', kanban_links: 'Links', kanban_runs_count: 'Runs ({0})',
  kanban_worker_log: 'Worker log', kanban_no_comments: 'No comments', kanban_no_events: 'No events',
  kanban_no_runs: 'No runs', kanban_empty: 'Empty', kanban_parents: 'Parents', kanban_children: 'Children',
  kanban_add_comment: 'Add comment', kanban_block: 'Block', kanban_unblock: 'Unblock',
  kanban_status_triage: 'Triage', kanban_status_todo: 'Todo', kanban_status_ready: 'Ready',
  kanban_status_running: 'Running', kanban_status_blocked: 'Blocked', kanban_status_done: 'Done',
  kanban_status_archived: 'Archived'
};
const t = key => labels[key] || key;
function extractFunc(name) {
  const re = new RegExp('function\\s+' + name + '\\s*\\(');
  const start = src.search(re);
  if (start < 0) throw new Error(name + ' not found');
  let i = src.indexOf('{', start);
  let depth = 1; i++;
  while (depth > 0 && i < src.length) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') depth--;
    i++;
  }
  return src.slice(start, i);
}
[
  '_kanbanColumnLabel', '_kanbanTaskTitle', '_kanbanTaskBody', '_kanbanTaskMeta',
  '_kanbanFormatDetailValue', '_kanbanDetailSection', '_kanbanCommentHtml', '_kanbanEventHtml',
  '_kanbanRunHtml', '_kanbanLinksHtml', '_kanbanRenderTaskDetail'
].forEach(name => { globalThis[name] = eval('(' + extractFunc(name) + ')'); });
const fixture = {
  task: {id:'t_fixture', title:'Fixture task', body:'A realistic task body', assignee:'worker-a', tenant:'webui', priority:3, comment_count:1, link_counts:{children:1}},
  comments: [{author:'reviewer', body:'Looks good', created_at:1777931496}],
  events: [{kind:'created', payload:{assignee:'worker-a'}, created_at:1777931496}],
  links: {parents:['t_parent'], children:['t_child']},
  runs: [{id:17, status:'completed', summary:'finished', started_at:1777931496, completed_at:1777931596}],
  log: {}
};
process.stdout.write(_kanbanRenderTaskDetail(fixture));
"""


def test_kanban_task_detail_renderer_executes_with_log_fixture(tmp_path):
    driver = tmp_path / "kanban_detail_driver.js"
    driver.write_text(_DRIVER_SRC, encoding="utf-8")
    result = subprocess.run([NODE, str(driver), str(PANELS_JS)], text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    html = result.stdout
    for expected in (
        "Fixture task",
        "kanban-detail-comments",
        "kanban-detail-events",
        "kanban-detail-links",
        "kanban-detail-runs",
        "kanban-detail-log",
        "t_parent",
        "t_child",
        "Looks good",
    ):
        assert expected in html
