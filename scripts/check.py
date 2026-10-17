#!/usr/bin/env python3
"""Check this setup with opencode's own loader.

opencode/ is linked into a check project, and opencode is asked what it loaded: the agents,
commands, skills and MCP connections. The script also flags what the loader would accept
silently but shouldn't, such as an unpinned MCP package or v1 fields in an agent's frontmatter.

The check project is ~/.cache/opencode-setup/check/<hash of opencode/>. The background service
keeps a folder's definitions from the first time it loads that folder and misses later edits made
through the symlink, so every version of the files gets a folder of its own. The folders are
never deleted: once the service knows a folder, deleting it makes `opencode reload` fail.

It needs opencode v2 on PATH. Each MCP server is connected once, so npx may download
chrome-devtools-mcp on the first run. The servers are disconnected again at the end.
"""
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse

REPO = pathlib.Path(__file__).resolve().parent.parent
CFG = REPO / "opencode"
# The frontmatter keys of a v2 agent. Any other key makes opencode parse the file as a v1 agent.
V2_AGENT_KEYS = {"description", "mode", "model", "variant", "steps", "hidden", "color", "disabled", "permissions", "request"}

problems = []


def check(ok, what):
    print(("ok       " if ok else "PROBLEM  ") + what)
    if not ok:
        problems.append(what)


def oc(project, *args):
    # Output goes to a file: through a pipe, opencode 2.0.25 can exit before a large answer is written.
    with tempfile.TemporaryFile("w+") as out:
        run = subprocess.run(["opencode", *args], cwd=project, stdout=out, stderr=subprocess.PIPE, text=True)
        out.seek(0)
        text = out.read()
    if run.returncode != 0:
        sys.exit(f"opencode {' '.join(args)} failed:\n{run.stderr or text}")
    return json.loads(text) if text.strip() else None


def api(project, *request):
    return oc(project, "api", *request, "-H", f"x-opencode-directory:{project}")


def poll(fetch, ready, timeout=90):
    """Ask again until ready(answer) holds or time runs out. A new folder loads in the background,
    so a first answer can miss agents, commands, skills or MCP connections that arrive a moment later."""
    deadline = time.time() + timeout
    while True:
        answer = fetch()
        if ready(answer) or time.time() > deadline:
            return answer
        time.sleep(2)


def disconnect_all(project):
    """Stop the MCP servers the background service started for the throwaway folder."""
    for server in api(project, "mcp.list")["data"]:
        if server["status"]["status"] == "connected":
            # The generated mcp.disconnect operation fails in the 2.0.25 CLI; the raw route works.
            api(project, "POST", f"/api/experimental/mcp/{urllib.parse.quote(server['name'], safe='')}/disconnect")


def jsonc(text):
    """Parse JSONC: drop // and /* */ comments outside strings, then trailing commas."""
    out, i, in_string = [], 0, False
    while i < len(text):
        c = text[i]
        if in_string:
            out.append(c)
            if c == "\\":
                out.append(text[i + 1])
                i += 1
            elif c == '"':
                in_string = False
        elif c == '"':
            in_string = True
            out.append(c)
        elif text.startswith("//", i):
            i = text.find("\n", i)
            i = len(text) if i < 0 else i
            continue
        elif text.startswith("/*", i):
            i = text.index("*/", i) + 2
            continue
        else:
            out.append(c)
        i += 1
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", "".join(out)))


def frontmatter_keys(path):
    m = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.S)
    return set(re.findall(r"^([A-Za-z_][\w-]*):", m.group(1), re.M)) if m else set()


def effect(rules, action, resource):
    """The effect opencode applies: the last rule whose action and resource both match, else ask."""
    result = "ask"
    for rule in rules:
        pattern = rule["resource"]
        resource_matches = fnmatch.fnmatchcase(resource, pattern) or (
            # A shell pattern ending in " *" also matches the command without arguments.
            action == "shell" and pattern.endswith(" *") and resource == pattern[:-2]
        )
        if fnmatch.fnmatchcase(action, rule["action"]) and resource_matches:
            result = rule["effect"]
    return result


def check_project():
    """The check folder for the current contents of opencode/, created on first use."""
    digest = hashlib.sha256()
    for path in sorted(p for p in CFG.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(CFG)).encode() + b"\0" + path.read_bytes() + b"\0")
    cache = pathlib.Path(os.environ.get("XDG_CACHE_HOME") or pathlib.Path.home() / ".cache")
    project = (cache / "opencode-setup" / "check" / digest.hexdigest()[:16]).resolve()
    project.mkdir(parents=True, exist_ok=True)
    link = project / ".opencode"
    if not (link.is_symlink() and link.resolve() == CFG.resolve()):
        if link.is_symlink():
            link.unlink()  # a clone that moved since this folder was made
        link.symlink_to(CFG)
    return project


def main():
    project = check_project()
    try:
        run_checks(project)
    finally:
        disconnect_all(project)

    print()
    if problems:
        sys.exit(f"{len(problems)} problem(s).")
    print("All checks passed.")


def run_checks(project):
    config = jsonc((CFG / "opencode.jsonc").read_text())
    agent_files = sorted((CFG / "agents").glob("*.md"))
    command_files = sorted((CFG / "commands").glob("*.md"))
    skill_dirs = sorted(p for p in (CFG / "skills").iterdir() if p.is_dir())

    found = poll(lambda: oc(project, "debug", "agents"), lambda a: {f.stem for f in agent_files} <= {x["id"] for x in a})
    agents = {a["id"]: a for a in found}
    for f in agent_files:
        extra = sorted(frontmatter_keys(f) - V2_AGENT_KEYS)
        check(not extra, f"agents/{f.name} uses only v2 frontmatter" + (f" (found {extra})" if extra else ""))
        agent = agents.get(f.stem)
        check(agent is not None, f"agent {f.stem} is loaded")
        if agent:
            check(bool(agent.get("system") and agent.get("description")), f"agent {f.stem} has a prompt and a description")

    # Outcomes worked out by hand from agents/qa.md and opencode.jsonc.
    rules = {name: agents.get(name, {}).get("permissions", []) for name in ("qa", "build")}
    for name, action, resource, want in [
        ("qa", "chrome-devtools_take_screenshot", "*", "allow"),
        ("build", "chrome-devtools_take_screenshot", "*", "deny"),
        ("qa", "edit", "src/app.py", "deny"),
        ("qa", "shell", "git status", "allow"),
        ("qa", "shell", "git diff --stat", "allow"),
        ("qa", "shell", "git merge-base HEAD main", "allow"),
        ("qa", "shell", "npm run test:unit", "allow"),
        ("qa", "shell", "git merge feature", "deny"),
        ("qa", "shell", "git push origin main", "deny"),
        ("qa", "shell", "npx eslint --fix .", "deny"),
        ("qa", "shell", "python3 -m unittest discover -s tests", "allow"),
        ("qa", "shell", "head -50", "allow"),
        ("qa", "shell", "cat README.md > copy.md", "deny"),
        ("qa", "shell", "curl http://localhost:3000/orders", "ask"),
        ("qa", "subagent", "explore", "allow"),
        ("qa", "subagent", "general", "deny"),
    ]:
        got = effect(rules[name], action, resource)
        check(got == want, f"{name}: {action} {resource!r} is {want}" + ("" if got == want else f" (got {got})"))

    listed = poll(lambda: api(project, "command.list")["data"], lambda c: {f.stem for f in command_files} <= {x["name"] for x in c})
    commands = {c["name"] for c in listed}
    for f in command_files:
        check(f.stem in commands, f"command /{f.stem} is loaded")
        m = re.search(r"^agent:\s*(\S+)", f.read_text(), re.M)
        if m:
            check(m.group(1) in agents, f"command /{f.stem} runs an agent that exists ({m.group(1)})")

    listed = poll(lambda: api(project, "skill.list")["data"], lambda s: {d.name for d in skill_dirs} <= {x["id"] for x in s})
    skills = {s["id"]: s for s in listed}
    for d in skill_dirs:
        skill = skills.get(d.name)
        loaded_here = bool(skill) and pathlib.Path(skill.get("path", "")).resolve() == (d / "SKILL.md").resolve()
        check(loaded_here, f"skill {d.name} is loaded from this repo")
        check(bool(skill and skill.get("description")), f"skill {d.name} has a description, so the model is offered it")

    servers = config["mcp"]["servers"]
    for name, server in servers.items():
        command = server.get("command") or []
        if command[:1] == ["npx"]:
            package = next((a for a in command[1:] if not a.startswith("-")), "")
            pinned = re.fullmatch(r"(@[^/]+/)?[^@]+@\d[\w.-]*", package) is not None
            check(pinned, f"mcp {name}: npx package is pinned to a version ({package})")
    listed = lambda: {s["name"]: s["status"] for s in api(project, "mcp.list")["data"]}
    settled = lambda s: set(servers) <= set(s) and all(v["status"] not in ("pending", "connecting") for v in s.values())
    status = poll(listed, settled, timeout=120)
    # A check folder reused from an earlier run still has the servers that run disconnected.
    reconnect = [n for n, server in servers.items() if not server.get("disabled") and status.get(n, {}).get("status") == "disabled"]
    for name in reconnect:
        api(project, "POST", f"/api/experimental/mcp/{urllib.parse.quote(name, safe='')}/connect")
    if reconnect:
        status = poll(listed, settled, timeout=120)
    for name, server in servers.items():
        state = status.get(name, {"status": "missing"})
        want = "disabled" if server.get("disabled") else "connected"
        check(state.get("status") == want, f"mcp {name} is {want}" + ("" if state.get("status") == want else f" (got {json.dumps(state)})"))


if __name__ == "__main__":
    main()
