import base64
import requests
import av
import base64
import io
import logging
import cv2
from openai import OpenAI
import numpy as np
from rich.progress import Progress
import pandas as pd
import re
from pathlib import Path
import os
import json
import glob
from pupil_labs.automate_custom_events.cloud_interaction import download_recording, send_event_to_cloud

def isMonotonicInc(arr):
    return np.all(np.diff(arr) >= 0)

class ActivityRecognition:
    def __init__(self):
        self.base64Frames = []
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.object = "book"
        self.base_prompt = """Act as an experienced video-annotator. You are assigned a task to identify frames with pre-defined descriptions and tag them by adding labels. 
        Find which frame number in the length of the entire base64Frames this frame corresponds to. Ignore grey frames. Return the number of frame where an activity is found and print it. 
        The response format should be: 'Frame X: Description, Activity, Timestamp'.
        The 'Frame' is followed by the frame number
        The 'Description' can be a sentence of up to 10 words. 
        The 'Activity' has to be a summary of the description in 2 words separated by underscores. 
        The 'Timestamp' is the video_df['timestamp [s]'] that corresponds to this frame number. Find the frames where one of the following activities happen, 
        only the first occurrence of this activity should be returned.
        You will be penalized if you return more frames of each activity:"""


        self.picking_up = f"""Activity 1: Identify the frame where "Someone picks up a {self.object} that is placed on a desk". 
        This frame should depict the exact moment the person makes contact with the {self.object} and begins to pick it up. 
        Code this frame as 'picking_up'. 
        """
        self.opening = """
        Activity 2: Identify the frame where "Someone opens a book for the first time". 
        This frame should depict the exact moment the book starts to open. 
        Code this frame as 'opens_book'.
        """
        self.closing = """
        Activity 3: Identify the frame where "Someone closes an open book they hold in their hands". 
        This frame should depict the exact moment the person begins to close the book. 
        Code this frame as 'closes_book'.
        """
        self.putting_down = f"""
        Activity 4: Identify the frame where "Someone puts down the {self.object} on the desk". 
        This frame should depict the exact moment the {self.object} makes contact with the desk surface. 
        Code this frame as 'putting_down'.
        """
        self.format = 'The format should be always the same except for the variables that change (<number>, <description>, <activity_variable>, <timestamp_float_number>). Do not add any extra dots, letters, or characters. Here is the format: "Frame <frame_number>: Description - <description in a few words>, Activity - <activity_variable>, Timestamp - <timestamp_float_number>". Consider this example: "Frame 120: Description - The user picks up the book, Activity - picks_up_book, Timestamp - 4.798511111"'
    
    def read_video_ts(self, video_path, audio=False, auto_thread_type=True):
        """
        A function to read a video, extract frames, and store them as base64 encoded strings.
        :param video_path: the path to the video
        """
        # Read the video
        with av.open(video_path) as video_container, Progress() as progress:
            if audio:
                stream = video_container.streams.audio[0]
            else:
                stream = video_container.streams.video[0]
            if auto_thread_type:
                stream.thread_type = "AUTO"
            fps = stream.average_rate  # alt base_rate or guessed_rate
            nframes = stream.frames
            logging.info("Extracting pts...")
            pts, dts, ts = (list() for i in range(3))
            decode_task = progress.add_task("👓 Decoding...", total=nframes)
            for packet in video_container.demux(stream):
                for frame in packet.decode():
                    if frame is not None and frame.pts is not None:
                        pts.append(frame.pts)
                        dts.append(frame.dts) if frame.dts is not None else logging.info(
                            f"Decoding timestamp is missing at frame {len(pts)}"
                        )
                        ts.append(
                            (
                                frame.pts * frame.time_base
                                - stream.start_time * frame.time_base
                            )
                            * 1e9
                        )

                        # Convert the frame to an image and encode it in base64
                        img = frame.to_ndarray(format='bgr24')
                        _, buffer = cv2.imencode(".jpg", img)
                        self.base64Frames.append(base64.b64encode(buffer).decode("utf-8"))

                progress.advance(decode_task)
                progress.refresh()
            pts, dts, ts = (
                np.array(pts, dtype=np.uint64),
                np.array(dts, dtype=np.uint64),
                np.array(ts, dtype=np.uint64),
            )
            if not isMonotonicInc(pts):
                logging.warning("Pts are not monotonic increasing!.")
            if np.array_equal(pts, dts):
                logging.info("Pts and dts are equal, using pts")

            idc = pts.argsort()
            pts = pts[idc]
            ts = ts[idc]

            if nframes != len(pts):
                nframes = len(pts)
            else:
                logging.info(f"Video has {nframes} frames")

        timestamps_s = ts / 1e9
        self.video_df = pd.DataFrame(
        {
            "frames": np.arange(nframes),
            "pts": [int(pt) for pt in pts],
            "timestamp [ns]": ts,
            "timestamp [s]": timestamps_s
        }
        )   
        return self.video_df #, fps, nframes, pts, ts

    def query_frame(self, index):
         
        base64_frames_content = [{"image": self.base64Frames[index], "resize": 768}]
        video_df_content = [self.video_df.iloc[index].to_dict()]

        PROMPT_MESSAGES = [
            {
                "role": "system",
                "content": (self.base_prompt + self.format),
            },
            {
                "role": "user",
                "content":  f"Here are the activities:  {self.picking_up} , {self.opening} {self.closing}, {self.putting_down})",
            },
            {
                "role": "user",
                "content": f"The frames are extracted from this video and the timestamps and frame numbers are stored in video_df: {json.dumps(video_df_content)}",
            },
            {
                "role": "user", 
                "content": base64_frames_content},
        ]

        params = {
            "model": "gpt-4o",
            "messages": PROMPT_MESSAGES,
            "max_tokens": 2000,
        }

        result = self.client.chat.completions.create(**params)
        response = result.choices[0].message.content
        print("Response from OpenAI API:", response)

        pattern = r'Frame\s(\d+):\sDescription\s-\s.*?,\sActivity\s-\s([^,]+),\sTimestamp\s-\s([\d.]+)(?=\s|$)'
        match = re.search(pattern, response)

        # if match:
        if match:
            frame_number = int(match.group(1))
            activity = match.group(2)
            timestamp = float(match.group(3))
            return {
                    "frame_id": frame_number,
                    "timestamp [s]": timestamp,
                    "activity": activity,
                }
        else:
            print("No match found in the response")
        

    def binary_search(self, start, end, identified_activities):
        if start >= end:
            return []

        mid = (start + end) // 2
        print(f"Binary search range: {start}-{end}, mid: {mid}")

        mid_frame_result = self.query_frame(mid)
        results = []

        if mid_frame_result:
            activity = mid_frame_result["activity"]
            if activity not in identified_activities:
                identified_activities.add(activity)
                results.append(mid_frame_result)
            left_results = self.binary_search(start, mid, identified_activities)
            results.extend(left_results)
        else:
            right_results = self.binary_search(mid + 1, end, identified_activities)
            results.extend(right_results)
        return results

    def prompting(self, save_path):
        identified_activities = set()
        activity_data = self.binary_search(0, len(self.base64Frames),identified_activities)
        print("Filtered Activity Data:", activity_data)
        output_df = pd.DataFrame(activity_data)
        output_df.to_csv(os.path.join(save_path, "output.csv"), index=False)
        return output_df
    
if __name__ == "__main__":
    worksp_id = "<your_workspace_id>"
    rec_id = "<your_recording_id>"
    cloud_api_key = "<your_cloud_API_token>"
    DOWNLOAD_PATH = "<your_path>/recs.zip"
    OPENAI_API_KEY = '<your_openAI_key>'
    
    download_path = os.path.normpath(DOWNLOAD_PATH)
    download_path = Path(download_path)

    # Download recording
    download_recording(rec_id, worksp_id, download_path, cloud_api_key)
    recpath = Path(download_path / rec_id)
    files = glob.glob(str(Path(recpath, "*.mp4")))
    if len(files) != 1:
        error = "There should be only one video in the raw folder!"
        raise Exception(error)
    video_path = files[0]

    # Process video
    activity_rec_module = ActivityRecognition()
    video_df = activity_rec_module.read_video_ts(video_path)
    output_df = pd.DataFrame(video_df)
    output_df.to_csv(os.path.join(recpath, 'video_df.csv'), index=False)
    print(len(activity_rec_module.base64Frames), "frames read.")
    print(len(video_df['timestamp [s]']))

    output = activity_rec_module.prompting(recpath)
    if output is not None:
        print(output)
    else:
        print("No valid data returned from the API.")

    for index, row in output.iterrows():
        print(f"Relative timestamp: {row['timestamp [s]']}")
        print(row['activity'])
        send_event_to_cloud(worksp_id, rec_id, row['activity'], row['timestamp [s]'], cloud_api_key)

    