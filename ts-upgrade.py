#!/usr/bin/env python3

import datetime
import re
import sys
import tarfile
from distutils import dir_util
from functools import lru_cache

import requests
from bs4 import BeautifulSoup as bs

TEAMSPEAK_RELEASE_PAGE = "https://teamspeak.com/en/downloads/"
TEAMSPEAK_INSTALLATION_PATH = "/opt/teamspeak3"


@lru_cache(maxsize=1)
def get_release_page():
    return requests.get(TEAMSPEAK_RELEASE_PAGE).text


@lru_cache(maxsize=1)
def get_latest_release():
    html = get_release_page()
    soup = bs(html, "html.parser")
    div_field = soup.select_one("#server > div.platform.mb-5.linux")
    for title in div_field.findAll("h3"):
        title_content = title.text
        if not "64-bit" in title_content:
            continue

        release_informations = re.sub(r"[\n\t]*", "", title_content).split()
        release_version = release_informations[-1]

        return release_version
    sys.exit(1)


def get_download_link(version=None):
    if version is None:
        version = get_latest_release()
    return f"https://files.teamspeak-services.com/releases/server/{version}/teamspeak3-server_linux_amd64-{version}.tar.bz2"


def get_current_version():
    with open(f"{TEAMSPEAK_INSTALLATION_PATH}/version.txt", "r") as ts_version:
        return ts_version.read().strip()


def upgrade(version, dry_run=False):
    download = requests.get(get_download_link(version), allow_redirects=True)
    download_file_path = f"/tmp/ts3-{version}.tar.bz2"
    with open(download_file_path, "wb") as download_file:
        download_file.write(download.content)

    with tarfile.open(download_file_path, "r:bz2") as release:
        
        import os
        
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(release, "/tmp/")

    timestamp = datetime.datetime.now().timestamp()
    dir_util.copy_tree(
        TEAMSPEAK_INSTALLATION_PATH,
        f"{TEAMSPEAK_INSTALLATION_PATH}.{timestamp}",
        dry_run=int(dry_run),
    )

    dir_util.copy_tree(
        "/tmp/teamspeak3-server_linux_amd64/",
        TEAMSPEAK_INSTALLATION_PATH,
        dry_run=int(dry_run),
    )

    with open(f"{TEAMSPEAK_INSTALLATION_PATH}/version.txt", "w") as ts_version:
        ts_version.write(version)


def main():
    latest_release = get_latest_release()
    current_version = get_current_version()

    print(f"Current: '{current_version}'")
    print(f"Latest: '{latest_release}'")
    if latest_release != current_version:
        print(
            f"Need upgrade. Current version is {current_version}. {latest_release} is available."
        )
        upgrade(latest_release)
    else:
        print("Everything is up to date")


if __name__ == "__main__":
    main()
