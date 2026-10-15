"""Is every sibling still running? Its scheduled workflows, their last run and the signals.json it publishes.

Only public data is read (the GitHub API of public repositories and each sibling's web), so the
workflow's own token is enough. Problems open one issue in estado-iba and update it when they
change; when they are gone it is closed. Whoever watches the repository gets the alert, not just
whoever wrote the bots.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime

import requests

from . import config, contract

ISSUE_TITLE = "Salud de los proyectos hermanos"
INACTIVE_WARN_DAYS = 45  # GitHub turns off the cron of a public repository after 60 days without activity
FAILED = {"failure", "timed_out", "startup_failure"}
_CRON = re.compile(r"^\s*-\s*cron:", re.MULTILINE)  # a commented-out cron does not count
_KEYS = re.compile(r"<!-- claves: (\[.*?\]) -->")


@dataclass(frozen=True)
class Finding:
    repo: str
    level: str  # "error", "aviso" or "info"; only the first two open the issue
    key: str  # stable from one day to the next, so the issue only speaks when the set changes
    text: str


def scheduled(workflow_text: str) -> bool:
    return bool(_CRON.search(workflow_text))


def workflow_findings(repo: str, pushed: date, workflows: list[dict], today: date) -> list[Finding]:
    """Findings on the scheduled workflows of one repository.

    Each workflow is {"path", "state", "last": {"conclusion", "date", "url"} | None}, where last is
    its latest scheduled run that finished.
    """
    out = []
    for w in workflows:
        file = w["path"].rsplit("/", 1)[-1]
        if w["state"] == "disabled_inactivity":
            out.append(Finding(repo, "error", f"{repo}:{file}:inactivo",
                               f"GitHub ha apagado el cron de `{file}` por inactividad. Para reactivarlo: "
                               f"`gh workflow enable {file} -R {config.OWNER}/{repo}`"))
        elif w["state"] != "active":
            out.append(Finding(repo, "info", f"{repo}:{file}:{w['state']}", f"`{file}` está desactivado a mano."))
        elif (last := w.get("last")) and last["conclusion"] in FAILED:
            out.append(Finding(repo, "error", f"{repo}:{file}:fallo",
                               f"La última ejecución programada de `{file}` ({last['date']}) acabó en "
                               f"«{last['conclusion']}»: [ver ejecución]({last['url']})"))
    idle = (today - pushed).days
    if idle >= INACTIVE_WARN_DAYS and any(w["state"] == "active" for w in workflows):
        out.append(Finding(repo, "aviso", f"{repo}:inactividad",
                           f"Sin actividad desde hace {idle} días: GitHub apaga los cron a los 60. "
                           "Basta un commit para reiniciar la cuenta."))
    return out


def signals_findings(repo: str, doc: dict | None, today: date, max_age: int | None, expected: bool) -> list[Finding]:
    """Findings on the signals.json of one repository; doc is None when it publishes none."""
    if doc is None:
        return [Finding(repo, "info", f"{repo}:sin-signals",
                        "Aún no publica `signals.json`; el panel lo lee con su adaptador.")] if expected else []
    out = []
    rep = contract.validate(doc, repo)
    for kind, n in rep.unknown_kinds.most_common():
        out.append(Finding(repo, "error", f"{repo}:tipo:{kind}",
                           f"{n} señales de tipo «{kind}», que el contrato no recoge: el panel las descarta."))
    if rep.errors:
        out.append(Finding(repo, "error", f"{repo}:esquema",
                           f"`signals.json` no cumple el contrato ({len(rep.errors)} errores): "
                           + "; ".join(rep.errors[:3])))
    for w in rep.warnings:
        out.append(Finding(repo, "aviso", f"{repo}:aviso:{w.split(' ', 1)[1][:40]}", w))
    try:
        age = (today - date.fromisoformat(str(doc.get("generated", ""))[:10])).days
    except ValueError:
        return out  # the schema already says what is wrong with the date
    if max_age is not None and age > max_age:
        out.append(Finding(repo, "error", f"{repo}:viejo",
                           f"`signals.json` se generó hace {age} días; se espera al menos cada {max_age}."))
    return out


def issue_plan(old: list[str] | None, new: list[str]) -> str:
    """What to do with the issue: old is the set of keys of the open issue, or None if there is none.

    "create", "comment" (the set changed: say it, so it notifies), "refresh" (same set: only
    the report is updated, silently), "close" or "nothing".
    """
    if not new:
        return "close" if old is not None else "nothing"
    if old is None:
        return "create"
    return "refresh" if sorted(old) == sorted(new) else "comment"


def report(findings: list[Finding], repos: list[str], today: date) -> str:
    by = {lvl: [f for f in findings if f.level == lvl] for lvl in ("error", "aviso", "info")}
    lines = [f"Revisión del {today.isoformat()} (UTC): {len(by['error'])} problemas, {len(by['aviso'])} avisos.", ""]
    for lvl, title in (("error", "Problemas"), ("aviso", "Avisos")):
        if by[lvl]:
            lines += [f"## {title}", ""] + [f"- **{f.repo}**: {f.text}" for f in by[lvl]] + [""]
    touched = {f.repo for f in findings if f.level != "info"}
    lines += ["## Sin novedad", "", " · ".join(r for r in repos if r not in touched) or "—", ""]
    if by["info"]:
        lines += ["<details><summary>Notas</summary>", ""] + [f"- **{f.repo}**: {f.text}" for f in by["info"]]
        lines += ["", "</details>", ""]
    lines.append("Lo genera `python -m estado.cli health` cada día (workflow `salud.yml`).")
    return "\n".join(lines)


# --- reading GitHub and the siblings' webs ---------------------------------------------------

def _session(token: str | None) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "estado-iba (+https://github.com/Asensio94/estado-iba)",
                      "Accept": "application/vnd.github+json"})
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


def _day(stamp: str) -> date:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).date()


def _workflows(s: requests.Session, repo: str, branch: str) -> list[dict]:
    api = f"{config.API}/repos/{config.OWNER}/{repo}/actions"
    out = []
    for w in s.get(f"{api}/workflows", timeout=60).json().get("workflows", []):
        text = s.get(f"{config.RAW}/{repo}/{branch}/{w['path']}", timeout=60)
        if text.status_code != 200 or not scheduled(text.text):
            continue
        runs = s.get(f"{api}/workflows/{w['id']}/runs", params={"event": "schedule", "status": "completed",
                                                                 "per_page": 1}, timeout=60).json()
        run = (runs.get("workflow_runs") or [None])[0]
        out.append({"path": w["path"], "state": w["state"],
                    "last": run and {"conclusion": run["conclusion"], "date": run["created_at"][:10],
                                     "url": run["html_url"]}})
    return out


def _signals(s: requests.Session, repo: str) -> dict | None:
    r = s.get(f"{config.PAGES}/{repo}/signals.json", timeout=120, headers={"Accept": "application/json"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def check(today: date, token: str | None, expected: set[str]) -> list[Finding]:
    """Every sibling in config.SIBLINGS; one that cannot be read is itself a finding, not a crash."""
    s = _session(token)
    out = []
    for repo, max_age in config.SIBLINGS.items():
        try:
            info = s.get(f"{config.API}/repos/{config.OWNER}/{repo}", timeout=60)
            info.raise_for_status()
            info = info.json()
            out += workflow_findings(repo, _day(info["pushed_at"]), _workflows(s, repo, info["default_branch"]), today)
        except (requests.RequestException, KeyError, ValueError) as e:
            out.append(Finding(repo, "error", f"{repo}:github", f"No se pudo leer de GitHub: {e}"))
        try:
            out += signals_findings(repo, _signals(s, repo), today, max_age, repo in expected)
        except (requests.RequestException, ValueError) as e:
            out.append(Finding(repo, "error", f"{repo}:signals", f"No se pudo leer `signals.json`: {e}"))
    return out


def sync_issue(findings: list[Finding], body: str, repository: str, token: str) -> str:
    """Open, update or close the health issue of `repository` (owner/name). Returns what it did."""
    s = _session(token)
    api = f"{config.API}/repos/{repository}/issues"
    issue = next((i for i in s.get(api, params={"state": "open", "per_page": 100}, timeout=60).json()
                  if i["title"] == ISSUE_TITLE and "pull_request" not in i), None)
    old = None
    if issue is not None:
        m = _KEYS.search(issue.get("body") or "")
        old = json.loads(m.group(1)) if m else []
    new = sorted({f.key for f in findings if f.level != "info"})
    plan = issue_plan(old, new)
    full = f"{body}\n\n<!-- claves: {json.dumps(new, ensure_ascii=False)} -->"
    if plan == "create":
        s.post(api, json={"title": ISSUE_TITLE, "body": full}, timeout=60).raise_for_status()
    elif plan in ("comment", "refresh"):
        s.patch(f"{api}/{issue['number']}", json={"body": full}, timeout=60).raise_for_status()
        if plan == "comment":
            gone, came = sorted(set(old) - set(new)), sorted(set(new) - set(old))
            text = "\n".join([f"Nuevo: `{k}`" for k in came] + [f"Resuelto: `{k}`" for k in gone])
            s.post(f"{api}/{issue['number']}/comments", json={"body": text + "\n\nEl informe está arriba."},
                   timeout=60).raise_for_status()
    elif plan == "close":
        s.post(f"{api}/{issue['number']}/comments", json={"body": "Todo en orden."}, timeout=60).raise_for_status()
        s.patch(f"{api}/{issue['number']}", json={"state": "closed"}, timeout=60).raise_for_status()
    return plan
