import json
from forge import (connect, setup, add_agent, add_workflow, list_agents,
                   execute_workflow, process_due, run_steps, set_workflow_enabled, recent_runs, set_agent_enabled)
import pytest


@pytest.fixture
def db(tmp_path):
    connection = connect(tmp_path / 'db.sqlite')
    setup(connection)
    yield connection
    connection.close()


def test_agent_create_and_config(db):
    aid = add_agent(db, 'Researcher', 'Research', 'Cite sources', can_research=True)
    assert list_agents(db)[0]['can_research'] == 1
    assert list_agents(db)[0]['id'] == aid


def test_cannot_create_without_agents(db):
    with pytest.raises(ValueError):
        add_workflow(db, 'Bad', 'Do research', ['not-here'])


def test_manual_workflow_calls_each_agent_and_persists_output(db, monkeypatch):
    a = add_agent(db, 'Research', 'Find information', 'Use evidence')
    b = add_agent(db, 'Editor', 'Prepare report', 'Summarise clearly')
    workflow = add_workflow(db, 'Market', 'Analyse UK widgets', [a, b])
    seen = []
    def fake_call(agent, goal, previous, sources):
        seen.append((agent['name'], len(previous)))
        return f'Output from {agent["name"]}'
    monkeypatch.setattr('forge.ask_ollama', fake_call)
    rid = execute_workflow(db, workflow)
    assert seen == [('Research', 0), ('Editor', 1)]
    assert len(run_steps(db, rid)) == 2
    assert recent_runs(db)[0]['status'] == 'completed'


def test_failed_ollama_is_reported_not_hidden(db, monkeypatch):
    a = add_agent(db, 'Writer', 'Write', 'Clear output')
    wid = add_workflow(db, 'Report', 'Write report', [a])
    def fail(*_):
        raise RuntimeError('Ollama connection refused')
    monkeypatch.setattr('forge.ask_ollama', fail)
    rid = execute_workflow(db, wid)
    row = db.execute('SELECT status, error FROM runs WHERE id=?', (rid,)).fetchone()
    assert row['status'] == 'failed'
    assert 'connection refused' in row['error']


def test_scheduled_due_and_disabled(db, monkeypatch):
    agent = add_agent(db, 'Writer', 'Writing', 'Create a draft')
    wid = add_workflow(db, 'Daily', 'Make a draft', [agent], interval_minutes=60, enabled=True)
    monkeypatch.setattr('forge.ask_ollama', lambda *args: 'Done')
    assert process_due(db) is not None
    assert process_due(db) is None  # not yet due again
    set_workflow_enabled(db, wid, False)
    assert process_due(db) is None


def test_disabled_agent_blocks_run(db):
    agent = add_agent(db, 'Writer', 'Writing', 'Create a draft')
    wid = add_workflow(db, 'Daily', 'Make a draft', [agent])
    set_agent_enabled(db, agent, False)
    rid = execute_workflow(db, wid)
    assert db.execute('SELECT status FROM runs WHERE id=?', (rid,)).fetchone()[0] == 'failed'
