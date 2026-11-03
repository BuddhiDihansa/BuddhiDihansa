
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

README_FILE = ROOT / "README.md"
CONFIG_FILE = ROOT / "profile_config.json"

START_MARKER = "<!-- AUTO-PROJECTS:START -->"
END_MARKER = "<!-- AUTO-PROJECTS:END -->"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_public_repositories(username):
    url = (
        f"https://api.github.com/users/{username}/repos"
        "?type=owner&sort=updated&direction=desc&per_page=100"
    )

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Buddhi-GitHub-Profile-Updater",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    token = os.getenv("GH_TOKEN")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        url,
        headers=headers
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def should_include(repo, config):
    full_name = repo["full_name"].lower()

    excluded = {
        name.lower()
        for name in config.get("exclude_repositories", [])
    }

    featured = {
        name.lower()
        for name in config.get("featured_repositories", [])
    }

    if repo.get("private"):
        return False

    if full_name in excluded:
        return False

    if full_name in featured:
        return False

    if config.get("exclude_forks", True) and repo.get("fork"):
        return False

    if config.get("exclude_archived", True) and repo.get("archived"):
        return False

    if (
        config.get("exclude_empty_repositories", True)
        and repo.get("size", 0) == 0
    ):
        return False

    return True


def generate_project_table(repositories, config):
    selected = [
        repo
        for repo in repositories
        if should_include(repo, config)
    ]

    selected.sort(
        key=lambda repo: repo.get("updated_at", ""),
        reverse=True
    )

    maximum = config.get("max_projects", 6)
    selected = selected[:maximum]

    if not selected:
        return "_New public projects will appear here as I publish them._"

    lines = [
        "| Project | Description | Language | Last Updated |",
        "|---|---|---|---|"
    ]

    for repo in selected:
        name = repo.get("name", "Project")
        url = repo.get("html_url", "")
        description = repo.get("description") or "Project details coming soon."
        language = repo.get("language") or "Not specified"
        updated = repo.get("updated_at", "")[:10]

        # Keep Markdown table formatting safe.
        name = name.replace("|", "\\|")
        description = " ".join(description.split())
        description = description.replace("|", "\\|")

        if len(description) > 100:
            description = description[:97] + "..."

        lines.append(
            f"| [{name}]({url}) "
            f"| {description} "
            f"| {language} "
            f"| {updated} |"
        )

    return "\n".join(lines)


def update_readme(project_section):
    content = README_FILE.read_text(encoding="utf-8")

    if START_MARKER not in content:
        raise ValueError("START marker missing from README.md")

    if END_MARKER not in content:
        raise ValueError("END marker missing from README.md")

    before, remaining = content.split(START_MARKER, 1)
    _, after = remaining.split(END_MARKER, 1)

    new_content = (
        before
        + START_MARKER
        + "\n"
        + project_section
        + "\n"
        + END_MARKER
        + after
    )

    if new_content != content:
        README_FILE.write_text(
            new_content,
            encoding="utf-8"
        )
        print("GitHub profile README updated successfully.")

    else:
        print("No changes detected. README is already up to date.")


def main():
    config = load_config()

    username = config["username"]

    print(f"Fetching public repositories for {username}...")

    repositories = get_public_repositories(username)

    print(f"Found {len(repositories)} repositories.")

    project_section = generate_project_table(
        repositories,
        config
    )

    update_readme(project_section)


if __name__ == "__main__":
    main()
