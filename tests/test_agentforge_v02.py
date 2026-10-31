"""Regression and safety tests for AgentForge v0.2."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
import pytest
import forge


@pytest.fixture
def db(tmp_path):
    db=forge.connect(tmp_path/'test.sqlite3');forge.setup(db)
    yield db
    db.close()


def sample(db,approval=False,scheduled=False,tools=None):
    aid=forge.add_agent(db,'Writer','Write a report','Stay factual',tools=tools or [])
    wid=forge.add_workflow(db,'Draft','Produce a useful business briefing',[aid],interval_minutes=60,
                           enabled=scheduled,approval_required=approval)
    return aid,wid


def test_original_schema_is_upgraded(tmp_path):
    db=sqlite3.connect(tmp_path/'legacy.db')
    db.executescript('''CREATE TABLE agents (id TEXT PRIMARY KEY,name TEXT,role TEXT,instructions TEXT,model TEXT,can_research INTEGER,enabled INTEGER,created_at TEXT);
       INSERT INTO agents VALUES ('old','Researcher','Research','Cite','llama3.2:3b',1,1,'2026-01-01');''')
    db.close()
    fresh=forge.connect(tmp_path/'legacy.db');forge.setup(fresh)
    agent=forge.list_agents(fresh)[0]
    assert json.loads(agent['tools'])==['wikipedia_search']
    assert agent['model_planning']==0
    fresh.close()


def test_models_fallback(monkeypatch):
    monkeypatch.setattr(forge.requests,'get',lambda *a,**kw: (_ for _ in ()).throw(forge.requests.ConnectionError('offline')))
    models,err=forge.ollama_models()
    assert models==[] and 'unavailable' in err


def test_models_list(monkeypatch):
    r=Mock();r.json.return_value={'models':[{'name':'qwen:3b'},{'name':'llama:3b'}]}
    monkeypatch.setattr(forge.requests,'get',lambda *a,**kw:r)
    assert forge.ollama_models()[0]==['llama:3b','qwen:3b']


@pytest.mark.parametrize('tools',[['shell'],['wikipedia_search','shell'],['utc_time','utc_time']])
def test_invalid_tools_forbidden(db,tools):
    with pytest.raises(ValueError):
        forge.add_agent(db,'Bad','Agent','Instructions',tools=tools)


def test_agent_custom_tools_edit_and_disable(db):
    aid=forge.add_agent(db,'Research','Check facts','Use citations',tools=['news_search'])
    assert json.loads(forge.list_agents(db)[0]['tools'])==['news_search']
    forge.update_agent(db,aid,'Updated','Researcher','More guidance','llama:3b',tools=['wikipedia_search','utc_time'],model_planning=True)
    a=forge.list_agents(db)[0]
    assert a['model_planning']==1 and json.loads(a['tools'])==['wikipedia_search','utc_time']
    forge.set_agent_enabled(db,aid,False)
    assert forge.list_agents(db)[0]['enabled']==0


def test_planner_unauthorized_tool_fallback(monkeypatch):
    agent={'name':'Research','role':'Analyst','model':'test','tools':'["news_search"]','model_planning':1}
    r=Mock();r.json.return_value={'message':{'content':'{"tools":["send_email"]}'}}
    monkeypatch.setattr(forge.requests,'post',lambda *a,**k:r)
    tools,how=forge.choose_tools(agent,'Business research',[])
    assert tools==['news_search'] and 'fallback' in how


def test_planner_timeout_fallback(monkeypatch):
    agent={'name':'Research','role':'Analyst','model':'test','tools':'["news_search"]','model_planning':1}
    def timeout(*a,**kw):
        raise forge.requests.Timeout('timed out')
    monkeypatch.setattr(forge.requests,'post',timeout)
    assert forge.choose_tools(agent,'Business research',[])[0]==['news_search']


def test_planner_valid_selects_granted_only(monkeypatch):
    agent={'name':'Research','role':'Analyst','model':'test','tools':'["news_search","wikipedia_search"]','model_planning':1}
    r=Mock();r.json.return_value={'message':{'content':'{"tools":["wikipedia_search"]}'}}
    monkeypatch.setattr(forge.requests,'post',lambda *a,**k:r)
    assert forge.choose_tools(agent,'Briefing',[])[0]==['wikipedia_search']


def test_no_permission_no_research_calls(monkeypatch):
    monkeypatch.setattr(forge.requests,'get',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('network used')))
    assert forge.choose_tools({'tools':'[]','model_planning':1},'News',[])[0]==[]


def test_safe_calculator_allowed():
    assert forge.safe_calculate('10 * (2 + 3)')==50
    assert forge.execute_tool('calculator','Calculate 2 + 5')[0]['value']=='7'


@pytest.mark.parametrize('expression',['__import__("os")','2**100','2/0','True','10**10**10'])
def test_safe_calculator_rejects_unsafe(expression):
    with pytest.raises((ValueError,ZeroDivisionError,OverflowError)):
        forge.safe_calculate(expression)


def test_run_without_approval_completes(db,monkeypatch):
    aid,wid=sample(db)
    monkeypatch.setattr(forge,'ask_ollama',lambda *a:'Report written')
    rid=forge.execute_workflow(db,wid)
    run=forge.recent_runs(db)[0]
    assert run['id']==rid and run['status']=='completed'
    assert len(forge.run_steps(db,rid))==1
    assert any('completed' in e['message'] for e in forge.recent_events(db,run_id=rid))


def test_approval_blocks_all_ollama_calls(db,monkeypatch):
    aid,wid=sample(db,approval=True)
    monkeypatch.setattr(forge,'ask_ollama',lambda *a: (_ for _ in ()).throw(AssertionError('agent ran without approval')))
    rid=forge.execute_workflow(db,wid)
    assert db.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()[0]=='pending_approval'
    assert forge.process_due(db) is None
    assert len(forge.pending_approvals(db))==1


def test_approved_run_executes(db,monkeypatch):
    _,wid=sample(db,approval=True)
    monkeypatch.setattr(forge,'ask_ollama',lambda *a:'Approved report')
    rid=forge.execute_workflow(db,wid)
    forge.approve_run(db,rid)
    assert forge.process_due(db)==rid
    assert forge.recent_runs(db)[0]['status']=='completed'


def test_cannot_approve_twice(db):
    _,wid=sample(db,approval=True)
    rid=forge.execute_workflow(db,wid)
    forge.approve_run(db,rid)
    with pytest.raises(ValueError):forge.approve_run(db,rid)


def test_duplicate_pending_run_prevented(db):
    _,wid=sample(db,approval=True)
    assert forge.request_run(db,wid)
    assert forge.request_run(db,wid) is None


def test_cancel_pending_run_and_request_again(db):
    _,wid=sample(db,approval=True)
    rid=forge.execute_workflow(db,wid)
    forge.cancel_run(db,rid)
    assert forge.recent_runs(db)[0]['status']=='cancelled'
    assert forge.request_run(db,wid) is not None


def test_worker_queues_approval_without_running(db,monkeypatch):
    _,wid=sample(db,approval=True,scheduled=True)
    monkeypatch.setattr(forge,'ask_ollama',lambda *a: (_ for _ in ()).throw(AssertionError('Should not run')))
    rid=forge.process_due(db)
    assert db.execute('SELECT source,status FROM runs WHERE id=?',(rid,)).fetchone()[:]==('schedule','pending_approval')
    assert forge.process_due(db) is None


def test_worker_executes_unrestricted_due(db,monkeypatch):
    _,wid=sample(db,scheduled=True)
    monkeypatch.setattr(forge,'ask_ollama',lambda *a:'Report')
    assert forge.process_due(db)
    assert forge.process_due(db) is None


def test_update_workflow_changes_approvals_and_interval(db):
    aid,wid=sample(db)
    forge.update_workflow(db,wid,'New','Do something',[aid],45,True,True)
    w=forge.list_workflows(db)[0]
    assert w['name']=='New' and w['approval_required']==1 and w['interval_minutes']==45 and w['enabled']==1


def test_cancellation_requested_stops_before_next_agent(db,monkeypatch):
    first=forge.add_agent(db,'First','Do first','One')
    second=forge.add_agent(db,'Second','Do second','Two')
    wid=forge.add_workflow(db,'Pipeline','Write report',[first,second])
    count=[]
    def fake(agent,*a):
        count.append(agent['name'])
        if len(count)==1:
            run_id=forge.recent_runs(db)[0]['id']
            forge.cancel_run(db,run_id)
        return 'Output'
    monkeypatch.setattr(forge,'ask_ollama',fake)
    rid=forge.execute_workflow(db,wid)
    assert count==['First']
    assert db.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()[0]=='cancelled'


def test_persists_and_reopens(tmp_path):
    path=tmp_path/'db.sqlite3'
    db=forge.connect(path);forge.setup(db)
    aid=forge.add_agent(db,'A','B','C')
    db.close()
    reopened=forge.connect(path);forge.setup(reopened)
    assert forge.list_agents(reopened)[0]['id']==aid
    reopened.close()


def test_run_failure_preserves_error_and_steps(db,monkeypatch):
    _,wid=sample(db)
    monkeypatch.setattr(forge,'ask_ollama',lambda *a: (_ for _ in ()).throw(RuntimeError('Ollama unavailable')))
    rid=forge.execute_workflow(db,wid)
    r=forge.recent_runs(db)[0]
    assert r['status']=='failed' and 'unavailable' in r['error']
    assert forge.run_steps(db,rid)==[]


def test_worker_heartbeat_changes_state(db):
    assert forge.worker_status(db)['state']=='not observed'
    forge.worker_heartbeat(db)
    assert forge.worker_status(db)['state']=='recent heartbeat'


def test_recover_stale_running(db):
    _,wid=sample(db)
    rid=forge.request_run(db,wid)
    assert forge._claim_queued(db,rid)
    old=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat(timespec='seconds')
    db.execute('UPDATE runs SET started_at=? WHERE id=?',(old,rid));db.commit()
    assert forge.recover_stale_runs(db,older_than_minutes=30)==1
    assert forge.recent_runs(db)[0]['status']=='failed'


def test_news_tool_previews_are_labelled(monkeypatch):
    res=Mock();res.content=b'<rss><channel><item><title>Market update</title><link>https://example.com/article</link><pubDate>Today</pubDate></item></channel></rss>'
    monkeypatch.setattr(forge.requests,'get',lambda *a,**kw:res)
    assert forge.research_news('market')[0]['provenance']=='headline'


def test_events_log_creation(db):
    sample(db)
    assert len(forge.recent_events(db))>=2


def test_disabled_agent_fails_run(db):
    aid,wid=sample(db)
    forge.set_agent_enabled(db,aid,False)
    rid=forge.execute_workflow(db,wid)
    assert db.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()[0]=='failed'


def test_workflow_step_order(db,monkeypatch):
    a=forge.add_agent(db,'A','A','A');b=forge.add_agent(db,'B','B','B')
    w=forge.add_workflow(db,'Team','Goal',[a,b])
    seen=[]
    def fake(agent,goal,previous,sources):
        seen.append((agent['name'],len(previous)))
        return 'ok'
    monkeypatch.setattr(forge,'ask_ollama',fake)
    forge.execute_workflow(db,w)
    assert seen==[('A',0),('B',1)]


def test_default_business_team_is_installed_once(db):
    assert forge.bootstrap_business(db)
    names = [a['name'] for a in forge.list_agents(db)]
    assert len(names) == 10
    assert {x[0] for x in forge.BUSINESS_TEAM} == set(names)
    assert not forge.bootstrap_business(db)
    assert len(forge.list_agents(db)) == 10
    flow = next(w for w in forge.list_workflows(db) if w['name'] == 'Autonomous Online Business Founder')
    assert flow['enabled'] == 1
    assert flow['approval_required'] == 0
    assert len(json.loads(flow['agent_ids'])) == 10


def test_bootstrap_preserves_custom_agent_and_repeated_creations(db):
    custom = forge.add_agent(db, 'Specialist', 'Extra', 'Helpful')
    forge.bootstrap_business(db)
    assert len(forge.list_agents(db)) == 11
    forge.add_agent(db, 'Another specialist', 'Extra role', 'Helpful instructions')
    forge.bootstrap_business(db)
    assert len(forge.list_agents(db)) == 12
    assert any(a['id'] == custom for a in forge.list_agents(db))


def test_owner_emergency_stop_disables_schedules_and_cancels_queue(db):
    forge.bootstrap_business(db)
    wf = forge.list_workflows(db)[0]
    forge.set_workflow_enabled(db,wf['id'],True)
    run = forge.request_run(db,wf['id'])
    forge.emergency_stop(db)
    assert not forge.list_workflows(db)[0]['enabled']
    assert db.execute('SELECT status FROM runs WHERE id=?',(run,)).fetchone()['status']=='cancelled'
