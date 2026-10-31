"""Optional: populate a three-agent example workflow for safe demo use."""
from forge import connect, setup, list_agents, list_workflows, add_agent, add_workflow


def seed(db):
    if any(w['name'] == 'Demo — UK market briefing' for w in list_workflows(db)):
        return False
    researcher = add_agent(db, 'Demo Researcher', 'Collect background context',
                           'Use public sources, identify uncertainty, and cite references.', can_research=True)
    analyst = add_agent(db, 'Demo Analyst', 'Analyse the evidence',
                        'Separate verified observations from assumptions. Look for weaknesses in the evidence.')
    editor = add_agent(db, 'Demo Editor', 'Prepare a concise final briefing',
                       'Write a clear summary with evidence, uncertainties, and next research steps.')
    add_workflow(db, 'Demo — UK market briefing',
                 'Prepare a cautious introductory briefing on the UK garden equipment market.',
                 [researcher, analyst, editor], interval_minutes=1440, enabled=False)
    return True


if __name__ == '__main__':
    connection = connect()
    setup(connection)
    try:
        if seed(connection):
            print('Added 3 demo agents and 1 manual workflow. Open AgentForge to run it.')
        else:
            print('Demo workflow already exists; no duplicate added.')
    finally:
        connection.close()
