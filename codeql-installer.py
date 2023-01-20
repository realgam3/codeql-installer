#!/usr/bin/env python3
import re
import os
import logging
import zipfile
import requests
import tempfile
import platform
import subprocess
from os import path
from git import Repo
from urllib.parse import urljoin

__folder__ = path.abspath(path.dirname(__file__))

os_name = platform.system().lower()
logger = logging.getLogger(__name__)
github_url = "https://github.com/"
github_api_url = "https://api.github.com/"
repos = {
    "codeql-repo": urljoin(github_url, "/github/codeql.git"),
    "codeql-go": urljoin(github_url, "/github/codeql-go.git"),
}
queries_repo_url = urljoin(github_url, "/github/vscode-codeql-starter.git")
cli = urljoin(github_api_url, "/repos/github/codeql-cli-binaries/releases/latest")
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
            logger.info(f"Cloning repo {path.basename(url)}")
            Repo.clone_from(url, repo_path)
            continue
        logger.info(f"Pulling repo {path.basename(url)}")
        Repo(repo_path).remotes[0].pull()


def install_cli():
    res = requests.get(cli)
    res.raise_for_status()
    res_json = res.json()

    version = res_json["tag_name"]
    url_map = {}
    for asset in res_json["assets"]:
        url = asset["browser_download_url"]
        file_name = path.basename(url)
        url_map[file_name] = url

    version_regex = re.compile(r"(\d+\.\d+\.\d+)")
    codeql_latest_version = version_regex.search(version).group(1)
    codeql_installed_version = ""
    if path.exists(cli_path):
        codeql_installed_version = version_regex.search(subprocess.check_output([
            path.join(cli_path, cli_exe), "--version"
        ]).splitlines()[0].decode()).group(1)

    if codeql_installed_version != codeql_latest_version:
        logger.info(f"Downloading {cli_zip}")
        with requests.get(url_map[cli_zip], stream=True) as res:
            res.raise_for_status()
            with tempfile.TemporaryFile(suffix=".zip") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)
                f.seek(0)
                logger.info(f"Downloaded {cli_zip} successfully")
                with zipfile.ZipFile(file=f) as zf:
                    logger.info(f"Extracting {cli_zip}")
                    zf.extractall(__folder__)
                logger.info(f"Extracted {cli_zip} successfully")


def create_env():
    # Create Databases Folder
    os.makedirs(path.join(__folder__, "databases"), exist_ok=True)

    # Create Queries Folder
    queries_repo_path = path.join(__folder__, "queries")
    dir_map = {
        "ql": "codeql-repo",
        "codeql-go": "codeql-go"
    }
    if not path.exists(queries_repo_path):
        logger.info(f"Cloning repo {path.basename(queries_repo_url)}")
        Repo.clone_from(queries_repo_url, queries_repo_path)

    for dir_in_queries, dir_in_codeql_home in dir_map.items():
        dir_path = path.join(queries_repo_path, dir_in_queries)
        if path.islink(dir_path) and not path.exists(dir_path):
            os.unlink(dir_path)
        elif path.isdir(dir_path) and path.exists(dir_path):
            if len(os.listdir(dir_path)):
                continue

            os.rmdir(dir_path)

        logger.info(f"Creating symlink for {dir_in_queries}")
        try:
            os.symlink(
                src=path.join(__folder__, dir_in_codeql_home),
                dst=dir_path
            )
        except OSError:
            logger.error(
                f"Symlink {dir_in_queries} creation failed. Try to run script as "
                f"{'administrator' if os_name == 'windows' else 'root'}"
            )


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='[%(levelname)s] %(message)s',
                        datefmt='%d-%m-%y %H:%M:%S')
    install_repos()
    install_cli()
    create_env()
