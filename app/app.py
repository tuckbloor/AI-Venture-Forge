"""AI Venture Forge on AI App Server: independent local app and database.

All actions are triggered by authenticated local UI interactions. This application
is not designed for unauthenticated internet publication.
"""
from pathlib import Path
import json
from contextlib import closing
import ai_app_server as ui
from ai_app_server.ui import add as forge_component
from forge import (TOOLS, add_agent, add_workflow, answer_owner_request,
    approve_run, bootstrap_business, cancel_run, connect, emergency_stop,
    list_agents, list_assignments, list_workflows, ollama_models, owner_requests,
    pending_approvals, recent_events, recent_runs, request_run, run_steps,
    set_agent_enabled, set_workflow_enabled, setup, update_agent, worker_status)

state = ui.session_state()
sections = ['Overview', 'Live team', 'Agents', 'Workflows', 'Approvals', 'History', 'Worker']
with ui.sidebar():
    ui.section('Venture Forge')
    section = ui.selectbox('Workspace', sections, key='vf_section')
    ui.caption('YOUR BUSINESS CONTROL CENTRE')
    ui.guide('Private AI research. Your agents, decisions and schedules belong to this installation.')

with closing(connect()) as db:
    setup(db)
    bootstrap_business(db)
    agents = list_agents(db)
    flows = list_workflows(db)
    runs = recent_runs(db, 50)
    founder = next((x for x in flows if x['name'] == 'Autonomous Online Business Founder'), None)
    questions = owner_requests(db)
    worker = worker_status(db)
    if section == 'Overview':
        forge_component('hero', eyebrow='YOUR BUSINESS COMMAND CENTRE',
               title='Turn ideas into a business plan.',
               description='Coordinate your AI research team, review progress and decide what happens next. Everything runs on your own server.',
               tagline='Private workspace  •  Human-controlled decisions')

        summary = ui.columns(4)
        with summary[0]: ui.metric('Specialist agents', len(agents))
        with summary[1]: ui.metric('Workflows', len(flows))
        with summary[2]: ui.metric('Completed runs', sum(r['status'] == 'completed' for r in runs))
        with summary[3]: ui.metric('Decisions needed', len(questions))

        forge_component('section_heading', title='Business operations',
               description='Your workflow and worker at a glance')
        panels = ui.columns(2)
        with panels[0]:
            if founder:
                active = db.execute("""SELECT status, started_at FROM runs
                  WHERE workflow_id=? AND status IN ('queued', 'running', 'pending_approval')
                  ORDER BY started_at DESC, rowid DESC LIMIT 1""", (founder['id'],)).fetchone()
                active_status = active['status'] if active else None
                workflow_state = ('Research in progress' if active_status == 'running' else
                                  'Queued for the AI worker' if active_status == 'queued' else
                                  'Awaiting approval' if active_status == 'pending_approval' else
                                  'Ready to research')
                forge_component('info_card', icon='briefcase', eyebrow='FOUNDING WORKFLOW',
                       title='Online Business Founder',
                       description='A coordinated team researches a business idea, validates assumptions and drafts a practical launch plan.',
                       status=workflow_state,
                       tone='info' if active_status else 'success')
                if active_status:
                    ui.caption('Research has already been requested. See Live team for assignments and results.')
                elif ui.button('Start business research', key='vf_start_founder'):
                    rid = request_run(db, founder['id'])
                    if rid:
                        ui.success('Research queued. Open Live team to follow its progress.')
                    else:
                        ui.warning('A run was just queued by the worker. Check Live team.')
                if ui.button('Pause automatic schedule' if founder['enabled'] else 'Resume automatic schedule', key='vf_schedule_founder'):
                    set_workflow_enabled(db, founder['id'], not bool(founder['enabled']))
                    ui.success('Schedule changed. The dashboard will refresh.')
                ui.caption('Schedule: ' + ('Enabled · every 24 hours' if founder['enabled'] else 'Paused'))
            else:
                forge_component('info_card', eyebrow='WORKFLOW', title='Create your first workflow',
                       description='Open Workflows and choose agents to build your research plan.',
                       icon='briefcase', tone='info')
        with panels[1]:
            healthy = worker['state'] == 'recent heartbeat'
            forge_component('info_card', icon='activity', eyebrow='PROCESSING ENGINE',
                   title='Background AI worker',
                   description='The worker handles scheduled research, agent assignments and local model responses.',
                   status=('Heartbeat received' if healthy else 'No recent heartbeat detected'),
                   tone=('success' if healthy else 'warning'))
            ui.caption('Last check-in: ' + str(worker.get('heartbeat') or 'Not received yet'))
            if not healthy:
                ui.warning('If research stays queued, check Worker status and the Forge worker log.')
            else:
                ui.caption('Your server and worker use a separate database and port from other applications.')

        forge_component('section_heading', title='Your next decisions',
               description='Questions that need your approval or information')
        if not questions:
            forge_component('empty_state', title='Nothing needs your attention',
                   description='Your team will list any questions or decisions here as it works.')
        for q in questions[:8]:
            forge_component('info_card', icon='message', eyebrow=q['kind'].upper(),
                   title=q['question'], description='Answer this question for the next workflow run.',
                   tone='info')
            reply = ui.text_area('Your response', key='answer_'+q['id'])
            if ui.button('Save answer', key='save_answer_'+q['id']):
                try:
                    answer_owner_request(db, q['id'], reply)
                    ui.success('Your response has been saved.')
                except ValueError as exc: ui.error(str(exc))

        forge_component('section_heading', title='Recent activity',
               description='The latest research requests and results')
        if not runs:
            forge_component('empty_state', title='No research history yet',
                   description='The first research run will appear here when your team starts.')
        for run in runs[:5]:
            forge_component('activity_item', title=run['workflow_name'], status=run['status'].replace('_',' ').title(),
                   detail=run['started_at'].replace('T',' ')[:19] + ' UTC',
                   tone=('success' if run['status']=='completed' else
                         'warning' if run['status']=='failed' else 'info'))
    elif section == 'Live team':
        ui.section('Live team activity')
        ui.caption('Use Refresh to read the latest real worker state. Agent steps execute sequentially.')
        if ui.button('Refresh team progress', key='vf_refresh_team'): ui.success('Latest records loaded.')
        recent = runs[0] if runs else None
        if not recent: ui.warning('No runs yet. Start the business workflow on Overview.')
        else:
            ui.text(f"Run {recent['id'][:12]} • {recent['workflow_name']} • {recent['status']}")
            assignments = [x for x in list_assignments(db,1000) if x['run_id']==recent['id']]
            team_stats = ui.columns(3)
            with team_stats[0]: ui.metric('Working now', sum(x['status']=='working' for x in assignments))
            with team_stats[1]: ui.metric('Waiting', sum(x['status']=='queued' for x in assignments))
            with team_stats[2]: ui.metric('Finished', sum(x['status']=='completed' for x in assignments))
            for x in assignments:
                forge_component('info_card', icon='briefcase', eyebrow=x['status'].upper(),
                                title=x['agent_name'], description='Assignment: ' + x['task'],
                                status=x['status'].replace('_',' ').title(),
                                tone='success' if x['status']=='completed' else 'info')
                ui.caption('Due (estimated): '+str(x['due_at'] or 'Unscheduled'))
                if x['result']: ui.output(x['result'][:16000])
            ui.section('Worker events')
            for e in recent_events(db,20,run_id=recent['id']):
                ui.caption(f"{e['created_at']} • {e['level']}: {e['message']}")
    elif section == 'Agents':
        ui.section('Create a specialist agent')
        available, ollama_error = ollama_models()
        if ollama_error: ui.warning(ollama_error)
        model = ui.selectbox('Ollama model',available or ['llama3.2:3b'],key='vf_new_model')
        name = ui.input('New agent name',key='vf_new_name')
        role = ui.input('Specialist role',key='vf_new_role')
        instructions = ui.text_area('Instructions',key='vf_new_instructions',height=150)
        selected_tools = [t for t in TOOLS if ui.checkbox('Allow '+t,value=False,key='vf_tool_'+t)]
        planning = ui.checkbox('Allow model to choose among permitted tools',key='vf_model_planning')
        if ui.button('Create agent',key='vf_create_agent'):
            try:
                add_agent(db,name,role,instructions,model,tools=selected_tools,model_planning=planning)
                ui.success('Agent saved. Refresh to see it in the list.')
            except ValueError as exc: ui.error(str(exc))
        ui.divider()
        ui.section('Manage existing agents')
        if agents:
            labels={f"{a['name']} — {a['id'][:7]}": a for a in agents}
            chosen = ui.selectbox('Select an agent to edit',list(labels),key='vf_choose_agent')
            a = labels[chosen]
            new_name = ui.input('Name',a['name'],key='vf_edit_name_'+a['id'])
            new_role = ui.input('Role',a['role'],key='vf_edit_role_'+a['id'])
            new_instructions = ui.text_area('Instructions',a['instructions'],key='vf_edit_instructions_'+a['id'])
            new_model = ui.selectbox('Model',list(dict.fromkeys([a['model'],*available])),key='vf_edit_model_'+a['id'])
            current_tools = json.loads(a['tools'])
            granted=[t for t in TOOLS if ui.checkbox('Allow '+t,value=t in current_tools,key='vf_edit_tool_'+a['id']+t)]
            planner=ui.checkbox('Model-selected tools',value=bool(a['model_planning']),key='vf_edit_planner_'+a['id'])
            if ui.button('Save agent changes',key='vf_save_agent'):
                try:
                    update_agent(db,a['id'],new_name,new_role,new_instructions,new_model,tools=granted,model_planning=planner)
                    ui.success('Agent updated.')
                except ValueError as exc: ui.error(str(exc))
            if ui.button('Disable agent' if a['enabled'] else 'Enable agent',key='vf_toggle_agent'):
                set_agent_enabled(db,a['id'],not a['enabled']); ui.success('Agent status changed.')
    elif section == 'Workflows':
        ui.section('Create a workflow')
        ui.caption('Agents run in their selected order. Choose up to six using the position controls.')
        flow_name = ui.input('Workflow name',key='vf_flow_name')
        goal = ui.text_area('Goal and expected report',key='vf_flow_goal',height=160)
        active = [a for a in agents if a['enabled']]
        options=['(none)']+[f"{a['name']} — {a['id'][:7]}" for a in active]
        order=[]
        for pos in range(1,7):
            pick=ui.selectbox('Step '+str(pos),options,key='vf_step_'+str(pos))
            if pick!='(none)':order.append(active[options.index(pick)-1]['id'])
        interval=int(ui.number_input('Repeat every N minutes',1440,key='vf_interval'))
        scheduled=ui.checkbox('Enable scheduled runs',key='vf_enabled')
        approvals=ui.checkbox('Require owner approval',key='vf_approval_required')
        if ui.button('Create workflow',key='vf_create_flow'):
            try:
                add_workflow(db,flow_name,goal,order,interval,scheduled,approvals)
                ui.success('Workflow created. Refresh to see it below.')
            except ValueError as exc: ui.error(str(exc))
        ui.section('Existing workflows')
        for w in flows:
            active_workflow = db.execute("SELECT status FROM runs WHERE workflow_id=? AND status IN ('running','queued','pending_approval') LIMIT 1",(w['id'],)).fetchone()
            forge_component('info_card', icon='briefcase', eyebrow='ENABLED' if w['enabled'] else 'PAUSED',
                            title=w['name'], description=w['goal'][:320],
                            status=(active_workflow['status'].replace('_',' ').title() if active_workflow else 'Ready to run'),
                            tone='info' if active_workflow else 'success')
            ui.caption(f"Repeat every {w['interval_minutes']} minutes • {'Scheduled' if w['enabled'] else 'Manual'}")
            if active_workflow:
                ui.caption('This workflow already has an active run. Follow it in Live team.')
            elif ui.button('Run '+w['name'],key='vf_run_'+w['id']):
                rid=request_run(db,w['id']);ui.success('Run requested.' if rid else 'A run was just queued.')
            if ui.button('Pause' if w['enabled'] else 'Enable',key='vf_tog_flow_'+w['id']):
                set_workflow_enabled(db,w['id'],not w['enabled']);ui.success('Schedule updated.')
    elif section == 'Approvals':
        ui.section('Owner approvals')
        pending=pending_approvals(db)
        if not pending: ui.caption('No runs awaiting approval.')
        for r in pending:
            ui.text(f"{r['workflow_name']} • {r['started_at']} • {r['id'][:12]}")
            if ui.button('Approve run',key='vf_approve_'+r['id']):
                approve_run(db,r['id']);ui.success('Approved. The worker can now run it.')
            if ui.button('Reject run',key='vf_reject_'+r['id']):
                cancel_run(db,r['id']);ui.success('Run cancelled.')
    elif section == 'History':
        ui.section('Run history and audit')
        if not runs: ui.caption('No runs recorded yet.')
        for r in runs[:25]:
            ui.text(f"{r['workflow_name']} — {r['status']} — {r['started_at']}")
        if runs:
            runmap={f"{r['workflow_name']} {r['started_at']} {r['id'][:6]}":r for r in runs}
            selected=ui.selectbox('Inspect run',list(runmap),key='vf_inspect_run')
            record=runmap[selected]
            if record['error']:ui.error(record['error'])
            if record['result']:ui.output(record['result'][:50000])
            for step in run_steps(db,record['id']):
                ui.section(step['agent_name'])
                ui.output(step['output'][:16000])
        ui.section('Recent events')
        for e in recent_events(db,30):ui.caption(f"{e['created_at']}: {e['message']}")
    elif section == 'Worker':
        ui.section('Background worker')
        status=worker_status(db)
        ui.text('Heartbeat state: '+status['state'])
        ui.text('Last heartbeat: '+str(status.get('heartbeat') or 'No heartbeat yet'))
        ui.caption('The independent Forge worker runs beside the AI App Server process. It executes queued tasks and schedules.')
        if ui.button('Request emergency stop',key='vf_emergency_stop'):
            emergency_stop(db)
            ui.warning('Cancellation requested. Running Ollama inference may take time to return.')
        ui.guide('View data/logs/forge-worker.log if no heartbeat appears. START.bat --stop stops the worker and dashboard.')
