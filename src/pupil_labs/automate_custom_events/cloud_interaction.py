import requests
import json
import logging
import glob
import shutil
from pathlib import Path
import os

API_URL = "https://api.cloud.pupil-labs.com/v2"


def download_url(path: str, save_path: str, API_KEY, chunk_size=128) -> None:
    url = f"{API_URL}/{path}"
    r = requests.get(url, stream=True, headers={"api-key": API_KEY})
    r.raise_for_status()
    save_path = Path(save_path)
    with open(save_path, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fd.write(chunk)

    return r.status_code


def download_recording(recording_id: str, workspace_id: str, download_path: str, API_KEY) -> None:
    download_path = Path(download_path)  # Ensure download_path is a Path object
    download_path.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist

    save_path = download_path / f"{recording_id}.zip"
    status = download_url(f"workspaces/{workspace_id}/recordings:raw-data-export?ids={recording_id}", save_path, API_KEY, chunk_size=128)
    shutil.unpack_archive(save_path, download_path / recording_id)
    os.remove(save_path)
    for file_source in glob.glob(str(download_path / f"{recording_id}/*/*")):
        file_source = Path(file_source)
        file_destination = file_source.parents[1] / file_source.name
        shutil.move(file_source, file_destination)

    return status


def send_event_to_cloud(workspace_id, recording_id, keyword, timestamp_sec, API_KEY):
    url = f"{API_URL}/workspaces/{workspace_id}/recordings/{recording_id}/events"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "api-key": API_KEY,
    }
    data = {"name": keyword, "offset_s": timestamp_sec}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        logging.info(f"Event sent successfully: {data}")
    else:
        logging.error(f"Failed to send event: {response.status_code}, {response.text}")


def download_raw_recording(recording_id: str, workspace_id: str, download_path: str, API_KEY) -> None:
    os.makedirs(download_path, exist_ok=True)
    download_url(f"/workspaces/{workspace_id}/recordings/{recording_id}.zip", download_path / f"{recording_id}.zip", API_KEY, chunk_size=128)
    shutil.unpack_archive(download_path / f"{recording_id}.zip", download_path / f"{recording_id}")
    os.remove(download_path / f"{recording_id}.zip")
    for file_source in glob.glob(str(download_path / f"{recording_id}/*/*")):
        file_source = Path(file_source)
        file_destination = file_source.parents[1] / file_source.name
        shutil.move(file_source, file_destination)