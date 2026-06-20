import re
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

API = "https://api.github.com"
TIMEOUT = httpx.Timeout(20.0, connect=10.0)
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "ARDA-Research-Bot/0.1",
}

REPO_URL_RE = re.compile(r"github\.com/([^/\s]+)/([^/\s#?]+)")


@dataclass
class RepoSummary:
    owner: str
    name: str
    description: str | None
    language: str | None
    stars: int
    forks: int
    open_issues: int
    default_branch: str
    topics: list[str]
    readme_md: str | None


def parse_repo_url(url: str) -> tuple[str, str]:
    m = REPO_URL_RE.search(url)
    if not m:
        raise ValueError(f"Not a GitHub repo URL: {url}")
    owner, name = m.group(1), m.group(2)
    return owner, name.removesuffix(".git")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _get(client: httpx.Client, path: str) -> httpx.Response:
    r = client.get(f"{API}{path}")
    if r.status_code == 404:
        return r
    r.raise_for_status()
    return r


def fetch_repo(owner: str, name: str) -> RepoSummary:
    with httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
        repo_resp = _get(client, f"/repos/{owner}/{name}")
        if repo_resp.status_code == 404:
            raise ValueError(f"Repo not found: {owner}/{name}")
        repo = repo_resp.json()

        readme_md: str | None = None
        readme_resp = _get(client, f"/repos/{owner}/{name}/readme")
        if readme_resp.status_code == 200:
            readme_data = readme_resp.json()
            download_url = readme_data.get("download_url")
            if download_url:
                rm = client.get(download_url)
                if rm.status_code == 200:
                    readme_md = rm.text

    return RepoSummary(
        owner=owner,
        name=name,
        description=repo.get("description"),
        language=repo.get("language"),
        stars=repo.get("stargazers_count", 0),
        forks=repo.get("forks_count", 0),
        open_issues=repo.get("open_issues_count", 0),
        default_branch=repo.get("default_branch", "main"),
        topics=repo.get("topics", []) or [],
        readme_md=readme_md,
    )
