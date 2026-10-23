#!/usr/bin/env python3
"""Check this setup with opencode's own loader.

opencode/ is linked into a check project, and opencode is asked what it loaded: the agents,
commands, skills and MCP connections. The script also flags what the loader would accept
silently but shouldn't, such as an unpinned MCP package or v1 fields in an agent's frontmatter.

When there is a private/ layer, it is checked too: it must never be tracked by git, its config
must load, its workspace links must point at it, and its agents must use only v2 fields.

Each check project is ~/.cache/halfling-harness/check/<layer>-<hash of its files>. The background service
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
PRIVATE = REPO / "private"
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


def check_project(layer, links):
    """The check folder for the current contents of one layer, created on first use.
    links maps a name in the folder (".opencode", "AGENTS.md") to the file or folder it links to."""
    digest = hashlib.sha256()
    for source in links.values():
        files = sorted(p for p in source.rglob("*") if p.is_file()) if source.is_dir() else [source]
        for path in files:
            digest.update(str(path.relative_to(REPO)).encode() + b"\0" + path.read_bytes() + b"\0")
    cache = pathlib.Path(os.environ.get("XDG_CACHE_HOME") or pathlib.Path.home() / ".cache")
    project = (cache / "halfling-harness" / "check" / f"{layer}-{digest.hexdigest()[:16]}").resolve()
    project.mkdir(parents=True, exist_ok=True)
    for name, source in links.items():
        link = project / name
        if not (link.is_symlink() and link.resolve() == source.resolve()):
            if link.is_symlink():
                link.unlink()  # a clone that moved since this folder was made
            link.symlink_to(source)
    return project


def main():
    project = check_project("global", {".opencode": CFG})
    try:
        run_checks(project)
    finally:
        disconnect_all(project)

    run_skill_script_tests()
    if PRIVATE.is_dir():
        run_private_checks()

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

    # Outcomes worked out by hand from the agent files and opencode.jsonc.
    rules = {name: agent.get("permissions", []) for name, agent in agents.items()}
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
        ("dev", "edit", "src/app.py", "allow"),
        ("dev", "question", "*", "allow"),
        ("dev", "shell", "git commit -m 'orders: cap limit at 100'", "allow"),
        ("dev", "shell", "git switch -c orders/limit", "allow"),
        ("dev", "shell", "npm run test:unit", "allow"),
        ("dev", "shell", "npm run deploy", "ask"),
        ("dev", "shell", "npm install left-pad", "ask"),
        ("dev", "shell", "git push -u origin orders/limit", "ask"),
        ("dev", "shell", "git push origin main", "deny"),
        ("dev", "shell", "git push --force-with-lease origin orders/limit", "deny"),
        ("dev", "shell", "git reset --hard HEAD~1", "deny"),
        ("dev", "shell", "gh pr merge 7", "deny"),
        ("dev", "subagent", "qa", "allow"),
        ("dev", "subagent", "dev", "deny"),
        ("dev", "chrome-devtools_take_screenshot", "*", "deny"),
        ("eval", "edit", "docs/evaluations/2026-10-22.md", "allow"),
        ("eval", "edit", "src/app.py", "deny"),
        ("eval", "edit", "docs/README.md", "deny"),
        ("eval", "question", "*", "allow"),
        ("eval", "subagent", "explore", "allow"),
        ("eval", "subagent", "general", "deny"),
        ("eval", "shell", "git log --oneline v1.4.0..HEAD", "allow"),
        ("eval", "shell", "gh pr list --state merged --limit 50", "allow"),
        ("eval", "shell", "git commit -m 'docs: evaluation'", "deny"),
        ("eval", "shell", "git tag -a sprint-12", "deny"),
        ("eval", "shell", "npm install left-pad", "ask"),
        ("deps", "edit", "package.json", "deny"),
        ("deps", "shell", "npm outdated --json", "allow"),
        ("deps", "shell", "npm audit --json", "allow"),
        ("deps", "shell", "npm view express time --json", "allow"),
        ("deps", "shell", "pip3 index versions requests", "allow"),
        ("deps", "shell", "npm audit fix", "deny"),
        ("deps", "shell", "npm install express@5", "deny"),
        ("deps", "shell", "npm i express@5", "deny"),
        ("deps", "shell", "pip3 install -U requests", "deny"),
        ("deps", "shell", "go get -u ./...", "deny"),
        ("deps", "shell", "brew install osv-scanner", "deny"),
        ("deps", "shell", "curl -s https://registry.npmjs.org/express", "ask"),
        ("deps", "webfetch", "https://github.com/expressjs/express/releases", "allow"),
        ("deps", "question", "*", "deny"),
        ("design", "edit", "docs/specs/orders-limit-SPEC-12.md", "allow"),
        ("design", "edit", "docs/adr/0007-refunds.md", "allow"),
        ("design", "edit", "api/openapi.yaml", "allow"),
        ("design", "edit", "api/orders.py", "deny"),
        ("design", "edit", "tests/test_api.py", "deny"),
        ("design", "question", "*", "allow"),
        ("design", "subagent", "explore", "allow"),
        ("design", "subagent", "dev", "deny"),
        ("design", "shell", "python3 /h/opencode/skills/specs/scripts/spec_trace.py .", "allow"),
        ("design", "shell", "git commit -m 'docs: SPEC-12'", "deny"),
        ("dev", "shell", "python3 /h/opencode/skills/specs/scripts/spec_trace.py . --strict", "allow"),
        ("qa", "shell", "python3 /h/opencode/skills/specs/scripts/spec_trace.py .", "allow"),
        ("eval", "shell", "python3 /h/opencode/skills/specs/scripts/spec_trace.py . --json", "allow"),
        ("lead", "edit", "api/orders.py", "deny"),
        ("lead", "question", "*", "allow"),
        ("lead", "subagent", "dev", "allow"),
        ("lead", "subagent", "eval", "allow"),
        ("lead", "subagent", "general", "deny"),
        ("lead", "shell", "git worktree add /w/shop.worktrees/refunds -b orders/refunds", "allow"),
        ("lead", "shell", "python3 /h/opencode/skills/swarm/scripts/swarm_limits.py .", "allow"),
        ("lead", "shell", "git push -u origin orders/refunds", "ask"),
        ("lead", "shell", "gh pr create --fill", "ask"),
        ("lead", "shell", "git push --force origin orders/refunds", "deny"),
        ("lead", "shell", "git branch -D orders/refunds", "deny"),
        ("lead", "shell", "gh pr merge 9", "deny"),
        ("lead", "external_directory", "/w/shop.worktrees/refunds/*", "allow"),
        ("dev", "external_directory", "/w/shop.worktrees/refunds/*", "allow"),
        ("qa", "external_directory", "/w/shop.worktrees/refunds/*", "allow"),
    ]:
        got = effect(rules.get(name, []), action, resource)
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


def run_skill_script_tests():
    """Scripts that ship inside a skill carry their own tests; run each test file."""
    for test in sorted(CFG.glob("skills/*/scripts/test_*.py")):
        run = subprocess.run([sys.executable, str(test)], capture_output=True, text=True)
        summary = (run.stderr.strip().splitlines() or ["no output"])[-1]
        check(run.returncode == 0, f"{test.relative_to(REPO)} passes ({summary})")


def run_private_checks():
    tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "private"], capture_output=True, text=True).stdout.split()
    check(not tracked, "private/ has no files tracked by git" + (f" (tracked: {tracked})" if tracked else ""))
    ignored = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", "private/AGENTS.md"]).returncode == 0
    check(ignored, "git ignores private/")

    workspace_file = PRIVATE / ".workspace"
    if workspace_file.exists():
        workspace = pathlib.Path(workspace_file.read_text().strip())
        for name, source in ((".opencode", PRIVATE / "opencode"), ("AGENTS.md", PRIVATE / "AGENTS.md")):
            if source.exists():
                link = workspace / name
                check(link.is_symlink() and link.resolve() == source.resolve(), f"private: {link} links to {source.relative_to(REPO)}")

    if not (PRIVATE / "opencode").is_dir():
        return
    links = {".opencode": PRIVATE / "opencode"}
    if (PRIVATE / "AGENTS.md").exists():
        links["AGENTS.md"] = PRIVATE / "AGENTS.md"
    project = check_project("private", links)
    try:
        config_files = [p for p in (PRIVATE / "opencode").glob("opencode.json*") if p.is_file()]
        rules = [r for f in config_files for r in jsonc(f.read_text()).get("permissions", [])]
        agent_files = sorted((PRIVATE / "opencode" / "agents").glob("*.md"))
        expected_agents = {f.stem for f in agent_files} | {"build"}
        found = poll(lambda: oc(project, "debug", "agents"), lambda a: expected_agents <= {x["id"] for x in a})
        agents = {a["id"]: a for a in found}
        build = agents.get("build", {}).get("permissions", [])
        missing = [r for r in rules if r not in build]
        check(not missing, f"private: all {len(rules)} permission rules reach the agents" + (f" (missing {missing[:3]})" if missing else ""))
        for f in agent_files:
            extra = sorted(frontmatter_keys(f) - V2_AGENT_KEYS)
            check(not extra, f"private: agents/{f.name} uses only v2 frontmatter" + (f" (found {extra})" if extra else ""))
            check(f.stem in agents, f"private: agent {f.stem} is loaded")
    finally:
        disconnect_all(project)


if __name__ == "__main__":
    main()
