#!/usr/bin/env python3
import re
import os
import sys
import json
import zipfile
import requests
import tempfile
import platform
import subprocess
from os import path
from git import Repo
from bs4 import BeautifulSoup
from urllib.parse import urljoin

__folder__ = path.abspath(path.dirname(__file__))

os_name = platform.system().lower()
github_url = "https://github.com/"
repos = {
    "codeql-repo": urljoin(github_url, "/github/codeql.git"),
    "codeql-go": urljoin(github_url, "/github/codeql-go.git"),
}
queries_repo_url = urljoin(github_url, "/github/vscode-codeql-starter.git")
cli = urljoin(github_url, "/github/codeql-cli-binaries/releases/latest")
cli_path = path.join(__folder__, "codeql")
cli_zip = "codeql-linux64.zip"
cli_exe = "codeql"
if os_name == "darwin":
    cli_zip = "codeql-osx64.zip"
elif os_name == "windows":
    cli_zip = "codeql-win64.zip"
    cli_exe = "codeql.exe"


def install_repos():
    for repo, url in repos.items():
        repo_path = path.join(__folder__, repo)
        if not path.exists(repo_path):
            print(f"Cloning repo {path.basename(url)}", file=sys.stderr)
            Repo.clone_from(url, repo_path)
            continue
        print(f"Pulling repo {path.basename(url)}", file=sys.stderr)
        Repo(repo_path).remotes[0].pull()


def install_cli():
    res = requests.get(cli)
    html = BeautifulSoup(res.text, features="html.parser")

    urls = html.find_all("a", attrs={
        "rel": "nofollow",
        "class": "flex-items-center",
    })
    url_map = {}
    for url in urls:
        url_map[url.text.strip()] = urljoin(github_url, url.get("href"))

    data_hydro_click = json.loads(html.select_one("a[data-hydro-click]").get("data-hydro-click"))
    version_regex = re.compile(r"(\d+\.\d+\.\d+)")
    codeql_latest_version = version_regex.search(path.basename(data_hydro_click["payload"]["originating_url"])).group(1)
    codeql_installed_version = ""
    if path.exists(cli_path):
        codeql_installed_version = version_regex.search(subprocess.check_output([
            path.join(cli_path, cli_exe), "--version"
        ]).splitlines()[0].decode()).group(1)

    if codeql_installed_version != codeql_latest_version:
        print(f"Downloading {cli_zip} successfully", file=sys.stderr)
        with requests.get(url_map[cli_zip], stream=True) as res:
            res.raise_for_status()
            with tempfile.TemporaryFile(suffix=".zip") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)
                f.seek(0)
                print(f"Downloaded {cli_zip} successfully", file=sys.stderr)
                with zipfile.ZipFile(file=f) as zf:
                    print(f"Extracting {cli_zip}", file=sys.stderr)
                    zf.extractall(__folder__)
                print(f"Extracted {cli_zip} successfully", file=sys.stderr)


def create_env():
    # Create Databases Folder
    print(f"Creating folder databases", file=sys.stderr)
    os.makedirs(path.join(__folder__, "databases"), exist_ok=True)

    # Create Queries Folder
    queries_repo_path = path.join(__folder__, "queries")
    dir_map = {
        "ql": "codeql-repo",
        "codeql-go": "codeql-go"
    }
    if not path.exists(queries_repo_path):
        print(f"Cloning repo {path.basename(queries_repo_url)}", file=sys.stderr)
        Repo.clone_from(queries_repo_url, queries_repo_path)

    for dir_in_queries, dir_in_codeql_home in dir_map.items():
        dir_path = path.join(queries_repo_path, dir_in_queries)
        if path.exists(dir_path) and len(os.listdir(dir_path)):
            continue

        print(f"Creating symlink for {dir_in_queries}", file=sys.stderr)
        os.rmdir(path.join(queries_repo_path, dir_in_queries))
        try:
            os.symlink(
                src=path.join(__folder__, dir_in_codeql_home),
                dst=dir_path
            )
        except OSError:
            print(
                f"Error: {dir_in_queries} symlink creation failed. Try to run script as "
                f"{'administrator' if os_name == 'windows' else 'root'}"
            )


if __name__ == '__main__':
    install_repos()
    install_cli()
    create_env()
