import os
from toggl.TogglPy import Endpoints, Toggl

toggl = Toggl()

token = os.getenv("TOGGL_API_TOKEN")
toggl.setAPIKey(token)

workspaces = []
for e in toggl.getWorkspaces():
    workspaces.append((e['id'], e['name']))

clients = []
for e in toggl.getClients():
    clients.append((e['id'], e['name']))

print(workspaces)
print(clients)

projects = []
clients = [(None, "")]

#        return self.request(Endpoints.CLIENTS + '/{0}/projects'.format(id))

for wid, wname in workspaces:
    print(wname)
    for e in toggl.request(Endpoints.WORKSPACES + f'/{wid}/projects'):
        projects.append((e['id'], e['name']))

print(projects)

ptasks = []
for pid, pname in projects:
    print(pname)
    for e in toggl.getProjectTasks(pid):
        ptasks.append((pid, pname, e['id'], e['name']))
        print(ptasks[-1])
