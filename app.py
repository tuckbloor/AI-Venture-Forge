"""Local AgentForge Studio UI. Run on localhost; not an authenticated public service."""
from __future__ import annotations

import json
import streamlit as st
from forge import (
    connect,setup,TOOLS,ollama_models,add_agent,update_agent,set_agent_enabled,list_agents,
    add_workflow,update_workflow,set_workflow_enabled,list_workflows,execute_workflow,
    execute_run,request_run,approve_run,cancel_run,pending_approvals,recent_runs,run_steps,
    recent_events,worker_status,bootstrap_business,emergency_stop,owner_requests,answer_owner_request,
    list_assignments,prepare_assignments,
)

st.set_page_config(page_title='AgentForge AI — Agent Studio',page_icon='⚙️',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
:root{--teal:#0f766e;--navy:#102d39}
[data-testid="stAppViewContainer"]{background:#f5f9f9}
[data-testid="stSidebar"]{background:#e8f4f3;border-right:1px solid #cfdfdc}
.block-container{max-width:1280px;padding-top:1.6rem}
.hero{padding:2rem 2.2rem;border-radius:22px;background:linear-gradient(115deg,#102f3e,#0f766e);
  color:#fff;margin-bottom:1.6rem;box-shadow:0 10px 35px #102f3e18}
.hero h1{color:white;margin:0;font-size:2.5rem}.hero p{color:#e4f6f4;margin:0.6rem 0 0}
.eyebrow{letter-spacing:2px;font-size:.75rem;font-weight:700;color:#84f1e3;margin-bottom:.6rem}
[data-testid="stForm"]{background:#fff;border:1px solid #d3e5e4;border-radius:18px;padding:1.35rem}
[data-testid="stMetric"]{background:#fff;border:1px solid #d3e5e4;border-radius:14px;padding:12px 18px}
.stButton>button[kind="primary"],button[data-testid="stBaseButton-primary"]{background:#08796f!important;color:white!important;border-color:#08796f!important;font-weight:700!important}
.stButton>button[kind="primary"]:hover{background:#07564e!important;border-color:#07564e!important}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea{background:white!important;color:#162f3a!important}
[data-testid="stExpander"]{background:#fff;border:1px solid #d7e6e5;border-radius:12px}
footer{visibility:hidden}
</style>''',unsafe_allow_html=True)

@st.cache_resource
def get_db():
    db=connect();setup(db);bootstrap_business(db);return db

db=get_db()
models,model_error=ollama_models()
all_agents=list_agents(db)
flows=list_workflows(db)
runs=recent_runs(db)

st.sidebar.header('⚙️ AgentForge settings')
st.sidebar.caption('Autonomous planning — no financial or publishing integrations')
if models:
    st.sidebar.success(f'Ollama connected · {len(models)} model(s)')
    default_model=st.sidebar.selectbox('Default model for new agents',models,
       index=next((i for i,m in enumerate(models) if '3b' in m),0))
else:
    st.sidebar.warning(model_error or 'No models found; start Ollama')
    default_model=st.sidebar.text_input('Default model',value='llama3.2:3b')
st.sidebar.divider()
st.sidebar.markdown('**Permitted agent tools**')
for key,label in TOOLS.items():
    st.sidebar.caption(f'• `{key}` — {label}')
st.sidebar.divider()
st.sidebar.info('All data stays in local SQLite. Ollama calls your locally installed model. Public research tools contact external websites. No payments, emails, shell commands or file edits.')

st.markdown('''<div class="hero"><div class="eyebrow">PROJECT 04 · LOCAL MULTI-AGENT AUTOMATION</div>
<h1>⚙️ AgentForge AI</h1><p>AI founder team: choose a business, design the website and assign the owner build tasks.</p></div>''',unsafe_allow_html=True)
c1,c2,c3,c4=st.columns(4)
c1.metric('Agents',len(all_agents));c2.metric('Workflows',len(flows))
c3.metric('Questions for you',len(owner_requests(db)));c4.metric('Completed runs',sum(r['status']=='completed' for r in runs))

st.markdown('### 👑 Owner control')
a,b,c=st.columns([1,1,2])
with a:
    if st.button('🛑 EMERGENCY STOP',type='primary',use_container_width=True):
        emergency_stop(db);st.warning('Schedules stopped; queued jobs cancelled; running jobs asked to stop at next checkpoint.');st.rerun()
with b:
    if st.button('♻ Restore missing default agents',use_container_width=True):
        bootstrap_business(db);st.rerun()
with c:
    st.caption('Use this dashboard to control business research and planning. The worker launches automatically from START-BUSINESS.bat; stop or resume the founder schedule here.')

tabs=st.tabs(['🏢 Business Dashboard','📊 Team & Deadlines','👥 Agent Builder','🔀 Workflows','▶ Run & Approvals','📋 History','⏰ Worker & Schedules'])
with tabs[0]:
    st.subheader('Business command centre')
    st.write('**Owner:** You · **AI CEO:** Autonomous founding coordinator · **Mode:** Website and business planning')
    st.info('The 10-agent Online Business Founder workflow runs automatically each day when the worker is on. Its project manager will ask you to build the website. The platform has no tools to publish websites, send marketing messages or spend money.')
    founder_control = next((w for w in list_workflows(db) if w['name'] == 'Autonomous Online Business Founder'), None)
    if founder_control:
        cauto, crun = st.columns(2)
        with cauto:
            if st.button('▶ Resume automatic business operation' if not founder_control['enabled'] else '⏸ Pause automatic business operation', use_container_width=True):
                set_workflow_enabled(db, founder_control['id'], not founder_control['enabled'])
                st.rerun()
        with crun:
            if st.button('🚀 Start new business research now', use_container_width=True):
                try:
                    from forge import request_run
                    rid = request_run(db, founder_control['id'])
                    st.success('Job queued for the background worker.' if rid else 'No job created.')
                    st.rerun()
                except Exception as exc:
                    st.error(f'Could not queue run: {exc}')
        st.caption('Agents execute in sequence because later roles rely on earlier findings. Queued means awaiting the previous agent, not that the team has been disabled. Runs can take several minutes per local model.')
    st.markdown('**Questions from the business team**')
    questions=owner_requests(db)
    if not questions:
        st.caption('No questions yet. Run the founding workflow once to generate its first plan.')
    for q in questions:
        with st.form('owner_question_'+q['id']):
            st.write(('💷 ' if q['kind']=='funding' else '🛠️ ' if q['kind']=='build' else '❓ ') + q['question'])
            reply=st.text_area('Your answer / decision',key='reply_'+q['id'])
            if st.form_submit_button('Send answer to the team'):
                try:
                    answer_owner_request(db,q['id'],reply)
                    st.success('Answer saved for the next founder run.')
                    st.rerun()
                except ValueError as exc: st.error(str(exc))
    st.markdown('**Your current decisions and work queue**')
    for entry in pending_approvals(db):
        st.write('⏳ '+entry['workflow_name']+' — awaiting your approval')
    st.write('**Worker heartbeat:**',worker_status(db))
    st.caption('24/7 operation requires the separate worker or a supervised server process. Closing the desktop or worker stops new runs.')


@st.fragment(run_every="3s")
def live_team_dashboard():
    # A fresh read connection avoids reusing the UI's connection during worker writes.
    live_db=connect()
    try:
        current_flows=list_workflows(live_db)
        founder=next((f for f in current_flows if f['name']=='Autonomous Online Business Founder'),None)
        st.subheader('Live AI team activity')
        st.caption('Automatically updates every 3 seconds. Statuses come directly from the background worker, not simulated progress. Agents currently execute one at a time.')
        heartbeat=worker_status(live_db)
        st.write('**Worker heartbeat:**', heartbeat)
        if not founder:
            st.warning('Business founder workflow not installed.')
            return
        founder_runs=[r for r in recent_runs(live_db, 100) if r['workflow_id']==founder['id']]
        if not founder_runs:
            st.info('No founder run recorded yet. Start the business from Business Dashboard.')
            return
        latest=founder_runs[0]
        run_id=latest['id']
        # Read-only: worker owns task creation. Never mutate assignments from a UI refresh.
        assignments=[x for x in list_assignments(live_db,1000) if x['run_id']==run_id]
        active=[x for x in assignments if x['status']=='working']
        completed=[x for x in assignments if x['status']=='completed']
        pending=[x for x in assignments if x['status']=='queued']
        blocked=[x for x in assignments if x['status']=='blocked']
        status=latest['status']
        st.write(f'**Current run:** `{run_id[:12]}` · **{status.upper()}** · Started {latest["started_at"]} UTC')
        if latest.get('error'):
            st.error(f'Workflow problem: {latest["error"]}')
        c1,c2,c3,c4=st.columns(4)
        c1.metric('Working',len(active)); c2.metric('Waiting',len(pending))
        c3.metric('Finished',len(completed)); c4.metric('Blocked',len(blocked))
        if assignments:
            st.progress(len(completed)/len(assignments),text=f'{len(completed)} / {len(assignments)} agent assignments completed')
        if active:
            st.info('Currently working: '+', '.join(x['agent_name'] for x in active))
        elif status=='queued':
            st.warning('Run is queued. Check worker heartbeat and worker.log if it does not start.')
        elif status=='running':
            st.info('Worker preparing the next step or waiting on an external model/tool response.')
        elif status=='completed':
            st.success('Latest team run finished. Results appear below.')
        st.markdown('#### Agents and their latest work')
        for task in sorted(assignments,key=lambda x:(x['status']!='working',x['status']!='completed',x['agent_name'])):
            sym={'working':'🟢','queued':'⏳','completed':'✅','blocked':'🔴'}.get(task['status'],'⚪')
            with st.expander(f'{sym} {task["agent_name"]} — {task["status"].title()}',expanded=task['status']=='working'):
                st.write('**Role:**',task['role'])
                st.write('**Assignment:**',task['task'])
                st.write('**Deadline (estimate):**',task['due_at'] or 'Unscheduled')
                st.write('**Started:**',task['started_at'] or 'Not yet')
                st.write('**Finished:**',task['finished_at'] or 'Not yet')
                if task['result']:
                    st.markdown('**Actual agent result**')
                    st.text_area('Output',task['result'],height=260,key='live_result_'+task['id'])
                elif task['status']=='working':
                    st.caption('Agent is running a model request or research tool. The full response is saved when the step finishes.')
        st.markdown('#### Live worker activity')
        events=recent_events(live_db,limit=18,run_id=run_id)
        if not events:
            st.caption('No step events recorded yet.')
        for e in events:
            st.caption(f'{e["created_at"]} UTC · {e["level"].upper()} · {e["message"]}')
        st.caption('Live updates show completed steps and worker events; Ollama does not stream partial reasoning or response tokens into this dashboard.')
    finally:
        live_db.close()

with tabs[1]:
    live_team_dashboard()

with tabs[2]:
    st.subheader('Create an AI agent')
    st.caption('You choose the number of agents, what each knows, which model they use and which tools they may call.')
    with st.form('agent_create_'+str(st.session_state.get('agent_form_revision',0)),clear_on_submit=False):
        a,b=st.columns(2)
        with a:
            name=st.text_input('Agent name *',key='create_name_'+str(st.session_state.get('agent_form_revision',0)),placeholder='e.g. Market Researcher')
            role=st.text_input('Role *',key='create_role_'+str(st.session_state.get('agent_form_revision',0)),placeholder='e.g. Research market opportunities')
        with b:
            model=st.selectbox('Ollama model',models or [default_model],key='create_model')
            grant=st.multiselect('Allowed tools — read-only',list(TOOLS),format_func=lambda k:TOOLS[k])
        instructions=st.text_area('System instructions *',placeholder='Use evidence; flag assumptions; avoid invented facts.',height=130)
        planning=st.checkbox('Let Ollama choose from the allowed tools (short timeout, safe fallback)')
        if st.form_submit_button('＋ Create agent',type='primary',use_container_width=True):
            try:
                add_agent(db,name,role,instructions,model,tools=grant,model_planning=planning)
                st.session_state['agent_form_revision']=st.session_state.get('agent_form_revision',0)+1
                st.success('Agent saved');st.rerun()
            except ValueError as exc: st.error(str(exc))
    st.divider()
    st.subheader(f'Your agents ({len(all_agents)})')
    if not all_agents: st.info('Create a Researcher first, then an Analyst and Editor. You can design your own roles.')
    for agent in all_agents:
        with st.expander(('🟢 ' if agent['enabled'] else '⚪ ') + agent['name']+'  ·  '+agent['role']):
            with st.form('edit_agent_'+agent['id']):
                ca,cb=st.columns(2)
                newname=ca.text_input('Name',agent['name'])
                newrole=cb.text_input('Role',agent['role'])
                ai=st.text_area('Instructions',agent['instructions'])
                moptions=sorted(set(models+[agent['model']]))
                amodel=st.selectbox('Model',moptions,index=moptions.index(agent['model']))
                selected=st.multiselect('Tools',list(TOOLS),default=json.loads(agent['tools']),format_func=lambda k:TOOLS[k])
                planner=st.checkbox('Model-selected tools',value=bool(agent['model_planning']))
                if st.form_submit_button('Save agent changes'):
                    try:
                        update_agent(db,agent['id'],newname,newrole,ai,amodel,tools=selected,model_planning=planner)
                        st.success('Agent updated');st.rerun()
                    except ValueError as exc: st.error(str(exc))
            if st.button('Disable agent' if agent['enabled'] else 'Enable agent',key='toggle_'+agent['id']):
                set_agent_enabled(db,agent['id'],not agent['enabled']);st.rerun()

with tabs[3]:
    st.subheader('Design a workflow')
    st.caption('Agents run in the order shown. Each agent receives the previous agents’ outputs as untrusted context.')
    enabled_agents=[a for a in list_agents(db) if a['enabled']]
    labels={f'{a["name"]} · {a["id"][:7]}':a['id'] for a in enabled_agents}
    with st.form('workflow_create',clear_on_submit=True):
        flowname=st.text_input('Workflow name',placeholder='Weekly industry briefing')
        goal=st.text_area('Overall goal',placeholder='Research relevant developments, analyse findings, write an evidence-aware report.',height=110)
        selections=st.multiselect('Agents — selected order',list(labels))
        left,right=st.columns(2)
        interval=left.number_input('Repeat every N minutes',min_value=1,max_value=43200,value=1440)
        scheduled=right.checkbox('Enable scheduled worker execution',value=False)
        approval=st.checkbox('Require human approval before EACH run',value=True)
        if st.form_submit_button('＋ Create workflow',type='primary',use_container_width=True):
            try:
                add_workflow(db,flowname,goal,[labels[s] for s in selections],int(interval),scheduled,approval)
                st.success('Workflow created');st.rerun()
            except ValueError as exc: st.error(str(exc))
    st.divider()
    for flow in list_workflows(db):
        with st.expander(('🟢 ' if flow['enabled'] else '⚪ ')+flow['name']+' · '+flow['last_status']):
            st.write(flow['goal']);st.caption(f'Next run: {flow["next_run"] or "manual only"} · Approval: {"required" if flow["approval_required"] else "not required"}')
            with st.form('flowedit_'+flow['id']):
                fname=st.text_input('Workflow name',flow['name'])
                fgoal=st.text_area('Goal',flow['goal'])
                aids=json.loads(flow['agent_ids'])
                la={f'{a["name"]} · {a["id"][:7]}':a['id'] for a in list_agents(db)}
                reverse={v:k for k,v in la.items()}
                agents_order=st.multiselect('Agents — selection order',list(la),default=[reverse[x] for x in aids if x in reverse])
                fi=st.number_input('Interval (minutes)',1,43200,int(flow['interval_minutes']))
                fe=st.checkbox('Schedule enabled',value=bool(flow['enabled']))
                fa=st.checkbox('Approval required',value=bool(flow['approval_required']))
                if st.form_submit_button('Save workflow'):
                    try:
                        update_workflow(db,flow['id'],fname,fgoal,[la[x] for x in agents_order],fi,fe,fa)
                        st.success('Workflow saved');st.rerun()
                    except ValueError as exc: st.error(str(exc))
            if st.button('Pause schedule' if flow['enabled'] else 'Resume schedule',key='switch_'+flow['id']):
                set_workflow_enabled(db,flow['id'],not flow['enabled']);st.rerun()

with tabs[4]:
    st.subheader('Run a workflow')
    flows=list_workflows(db)
    if flows:
        options={f['name']+' · '+f['id'][:7]:f['id'] for f in flows}
        selection=st.selectbox('Workflow',list(options))
        chosen=next(f for f in flows if f['id']==options[selection])
        st.caption('Approval required' if chosen['approval_required'] else 'This workflow can execute when you press Run.')
        if st.button('▶ Request / run workflow',type='primary'):
            with st.status('Preparing run...',expanded=True) as status:
                try:
                    messages=[]
                    rid=execute_workflow(db,chosen['id'],on_step=lambda line:(messages.append(line),status.write(line)))
                    if rid is None: status.update(label='Run already active',state='error')
                    else:
                        state=db.execute('SELECT status,error FROM runs WHERE id=?',(rid,)).fetchone()
                        if state['status']=='pending_approval':
                            status.update(label='Waiting for approval',state='complete')
                        else:
                            status.update(label='Run '+state['status'],state='complete' if state['status']=='completed' else 'error')
                            if state['error']: st.error(state['error'])
                except Exception as err: status.update(label='Run error',state='error');st.error(str(err))
    else:
        st.info('Create an agent and a workflow first.')
    st.divider()
    st.subheader('Approval queue')
    approvals=pending_approvals(db)
    if not approvals: st.success('No pending approvals')
    for run in approvals:
        ca,cb,cc=st.columns([4,1,1])
        ca.write(f'**{run["workflow_name"]}** · {run["source"]} · {run["started_at"]}')
        if cb.button('Approve',key='approve_'+run['id'],type='primary'):
            approve_run(db,run['id']);st.success('Approved and queued. The worker can execute it.');st.rerun()
        if cc.button('Reject',key='reject_'+run['id']):
            cancel_run(db,run['id']);st.rerun()
    queued=[r for r in recent_runs(db) if r['status']=='queued']
    if queued:
        st.subheader('Approved runs awaiting worker')
        for r in queued:
            ca,cb=st.columns([4,1]);ca.write(f'{r["workflow_name"]} · {r["started_at"]}')
            if cb.button('Run now',key='execute_'+r['id']):
                with st.status('Executing...',expanded=True) as s:
                    execute_run(db,r['id'],on_step=lambda msg:s.write(msg))
                    s.update(label='Run finished',state='complete')
                st.rerun()

with tabs[5]:
    st.subheader('Run history and audit trail')
    for run in recent_runs(db,40):
        with st.expander(f'{run["workflow_name"]} · {run["status"].upper()} · {run["started_at"]}'):
            st.caption(f'Run ID: {run["id"]} · Source: {run["source"]}')
            if run['error']: st.error(run['error'])
            for step in run_steps(db,run['id']):
                st.markdown(f'**Step {step["step_number"]} · {step["agent_name"]}**')
                st.write(step['output'])
                st.caption('Tool evidence for this step (previews may be unverified)')
                st.json(json.loads(step['sources']))
            if run['result']:
                st.download_button('Download final report',run['result'],file_name=run['id']+'.md',key='dl_'+run['id'])
            if run['status'] in ('queued','pending_approval','running'):
                if st.button('Cancel this run',key='cancel_'+run['id']):cancel_run(db,run['id']);st.rerun()
            st.caption('Run activity')
            for ev in recent_events(db,100,run_id=run['id']):
                st.caption(f'{ev["created_at"]} · {ev["level"].upper()} · {ev["message"]}')
    st.subheader('Latest system activity')
    for ev in recent_events(db,25):
        st.caption(f'{ev["created_at"]} · {ev["message"]}')

with tabs[6]:
    st.subheader('Background worker')
    st.caption('START-BUSINESS.bat launches the worker in the background. No console menu is needed. The dashboard controls business workflows.')
    health=worker_status(db)
    st.write('**Status:** '+health['state']);st.caption('Last heartbeat: '+str(health.get('heartbeat') or 'Not yet seen'))
    st.caption('Worker diagnostics: E:\\04-agentforge\\data\\worker.log (local Windows installation)')
    st.warning('Scheduled tasks only run while the worker and Ollama are active. For true 24/7 operation use an always-on server, process supervision and access controls. No email, financial transactions or other external write actions are enabled.')
    st.markdown('**Safe schedule control**')
    for w in list_workflows(db):
        st.write(f'{"🟢" if w["enabled"] else "⚪"} {w["name"]} — every {w["interval_minutes"]} min — next: {w["next_run"] or "paused"}')
