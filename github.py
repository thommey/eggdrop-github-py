### Settings
# IP to listen on, 0.0.0.0 is all available IPs
GITHUB_IP = '0.0.0.0'
# Port to listen on
GITHUB_PORT = '21111'
# Secret for the webhook
GITHUB_SECRET = 'a7uBvf8jqpa8'
# Channel to announce events on (todo: do this via channel settings)
ANNOUNCE_CHANNEL = '#eggheads'

# It is recommended to set up a reverse proxy in front of this API and make it listen on 127.0.0.1
# see https://flask.palletsprojects.com/en/3.0.x/deploying/ for details, but it works without that

### Code starts here
# Real Python functions exported from Eggdrop
from eggdrop import bind
# Fallback solution, use Tcl functions
from eggdrop.tcl import setudef, putmsg, channel, putlog

import ipaddress, requests, threading, hmac
from pydantic import BaseModel, ValidationError
from flask import Flask, request, Response
from typing import List, Optional
from datetime import datetime, timezone
import re
from textwrap import wrap

if not 'github_app' in globals():
    github_app = Flask('github')

class UserInfo(BaseModel):
    email: Optional[str] = None
    name: str
    username: Optional[str] = None

class GithubUser(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    login: str
    type: str

class Commit(BaseModel):
    id: str
    author: UserInfo
    committer: UserInfo
    message: str
    timestamp: datetime
    url: str

class Repository(BaseModel):
    full_name: str

class PullRequest(BaseModel):
    number: int
    html_url: str
    title: str
    user: GithubUser

class PullRequestReview(BaseModel):
    state: str
    html_url: str

class Issue(BaseModel):
    number: int
    html_url: str
    title: str

class IssueComment(BaseModel):
    html_url: str
    body: str

class PushEvent(BaseModel):
    pusher: UserInfo
    sender: GithubUser
    ref: str
    compare: str
    commits: List[Commit]
    forced: bool
    repository: Repository

class PullRequestEvent(BaseModel):
    action: str
    number: int
    pull_request: PullRequest
    sender: GithubUser

class ReleaseInfo(BaseModel):
    html_url: str
    name: str
    prerelease: bool
    draft: bool

class ReleaseEvent(BaseModel):
    action: str
    sender: GithubUser
    release: ReleaseInfo

class IssueCommentEvent(BaseModel):
    action: str
    comment: IssueComment
    issue: Issue
    sender: GithubUser

class IssueEvent(BaseModel):
    action: str
    issue: Issue
    sender: GithubUser

class PullRequestReviewEvent(BaseModel):
    action: str
    pull_request: PullRequest
    sender: GithubUser
    review: PullRequestReview

def msgsummary(msg):
    summary = msg.split("\n", 1)[0]
    return summary

def msgsplit(msg):
    return wrap(msg, width=160, initial_indent="> ", subsequent_indent="> ", max_lines=5)

def process_hook(evtype, data):
    lines = []
    if evtype == 'push':
        data : PushEvent = PushEvent.model_validate(data)
        branch = data.ref.split("/", 2)[2]

        if len(data.commits) == 1 and branch == 'develop':
            c = data.commits[0]
            lines.append(f'{data.sender.login} -> {branch}: {c.timestamp.astimezone(timezone.utc).isoformat(" ")} {c.id[0:8]} {c.author.username}: {msgsummary(c.message)}')
        else:
            if branch == "develop":
                lines.append(f'{data.sender.login} pushed {len(data.commits)} commits to {branch}, see {data.compare} for details')
                lines.extend(map(lambda c: f'- {c.timestamp.astimezone(timezone.utc).isoformat(" ")} {c.id[0:8]} {c.author.username}: {msgsummary(c.message)}', data.commits))
    elif evtype == 'pull_request':
        data : PullRequestEvent = PullRequestEvent.model_validate(data)
        if data.action != 'synchronize':
            lines.append(f'{data.sender.login} {data.action} pull request #{data.number} ({data.pull_request.title}), see {data.pull_request.html_url} for details')
    elif evtype == 'release':
        data : ReleaseEvent = ReleaseEvent.model_validate(data)
        lines.append(f'{data.sender.login} {data.action} release "{data.release.name}", see {data.release.html_url} for details')
    elif evtype == 'issue_comment':
        rawdata = data
        data : IssueCommentEvent = IssueCommentEvent.model_validate(data)
        if data.action == 'created':
            if 'pull_request' in rawdata:
                strtype = 'pull request'
            else:
                strtype = 'issue'
            lines.append(f'{data.sender.login} added comment on {strtype} #{data.issue.number} ({data.issue.title}), see {data.comment.html_url} for details')
            #lines.extend(msgsplit(data.comment.body))
    elif evtype == 'pull_request_review':
        data : PullRequestReviewEvent = PullRequestReviewEvent.model_validate(data)
        if data.action == 'submitted':
            lines.append(f'{data.sender.login} submitted a review on pull request #{data.pull_request.number} => {data.review.state} ({data.pull_request.title}), see {data.review.html_url} for details')
    elif evtype == 'issues' and '/pull/' not in data.issue.html_url:
        data : IssueEvent = IssueEvent.model_validate(data)
        lines.append(f'{data.sender.login} {data.action} issue #{data.issue.number} ({data.issue.title}), see {data.issue.html_url} for details')

    if len(lines):
        for line in lines:
            #putlog('GITHUB: ' + line)
            putmsg(ANNOUNCE_CHANNEL, line)

@github_app.post('/github')
def github_hook():
    # IP Check
    ip_allowed = False
    for cidr in GITHUB_IPS:
        if ipaddress.ip_address(request.remote_addr) in ipaddress.ip_network(cidr):
            ip_allowed = True
    if not ip_allowed:
        putlog(f'Github.py: Rejected IP {request.remote_addr}')
        return Response('', status=403)
    # Signature check
    if 'X-Hub-Signature-256' not in request.headers:
        putlog(f'Github.py: Rejected request from {request.remote_addr}, no signature found')
        return Response('', status=403)
    if not request.headers['X-Hub-Signature-256'].startswith('sha256='):
        putlog(f'Github.py: Rejected request from {request.remote_addr}, invalid signature format')
        return Response('', status=403)
    request_signature = request.headers['X-Hub-Signature-256'][7:]
    calculated_signature = hmac.new(GITHUB_SECRET.encode('utf-8'), request.data, 'sha256').hexdigest()
    if not hmac.compare_digest(request_signature, calculated_signature):
        putlog(f'Github.py: Rejected request from {request.remote_addr}, invalid signature')
        return Response('', status=403)
    data = request.get_json()
    eventtype = request.headers['X-GitHub-Event']
    putlog(f'Github.py: Got webhook type {eventtype}')
    try:
        process_hook(eventtype, data)
    except Exception as e:
        putlog(f'GitHub exception:')
        putlog(str(e))
    return ''

def github_refresh_ips(*args):
    global GITHUB_IPS
    r = requests.get('https://api.github.com/meta')
    if r.status_code != 200:
        raise ValueError(f'Github.py: Github /meta API HTTP status is not 200 OK: {r.status_code}')
    if not 'content-type' in r.headers or not r.headers['content-type'].startswith('application/json'):
        raise ValueError(f'Github.py: Github /meta API HTTP content-type is not application/json: {r.headers.content_type}')
    data = r.json()
    if not 'hooks' in data:
        raise ValueError(f'Github.py: Github /meta API endpoint does not contain hooks key')
    if GITHUB_IPS is None or GITHUB_IPS != data['hooks']:
        GITHUB_IPS = data['hooks']
        putlog(f'Github.py: Github hook IPs whitelist: {", ".join(GITHUB_IPS)}')

def github_start():
    github_app.run(host=GITHUB_IP, port=GITHUB_PORT, debug=False, use_reloader=False)

def github_init():
    global GITHUB_IPS
    GITHUB_IPS = None
    setudef('str', 'github-events')
    bind('cron', '*', '3 12 * * *', github_refresh_ips)
    github_refresh_ips()
    threading.Thread(target=github_start).start()

if not 'GITHUB_INIT' in globals():
    global GITHUB_INIT
    GITHUB_INIT = True
    putlog('LOADING')
    github_init()
