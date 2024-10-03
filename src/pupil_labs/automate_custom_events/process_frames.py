from openai import OpenAI
import pandas as pd
import re
import os
import json
import aiohttp
from pupil_labs.automate_custom_events.cloud_interaction import send_event_to_cloud
import asyncio
import logging

logger = logging.getLogger(__name__)

class ProcessFrames:
    def __init__(self, base64Frames, vid_modules, OPENAI_API_KEY, cloudtoken, recID, workID,
                 prompt_description, prompt_codes, batch_size,
                 start_time_seconds, end_time_seconds):#gm_code, arm_activity1, arm_event_code1,

        # General params
        self.base64Frames = base64Frames
        self.workspaceid = workID
        self.recid = recID
        self.cloud_token = cloudtoken
        self.OPENAI_API_KEY = OPENAI_API_KEY
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.mydf = vid_modules
        self.session_cost = 0
        self.batch_size = batch_size

        # Time range parameters
        self.start_time_seconds = int(start_time_seconds)
        self.end_time_seconds = int(end_time_seconds)

        self.activities = re.split(r'\s*;\s*', prompt_description)
        self.codes = re.split(r'\s*;\s*', prompt_codes)

        # Initialize activity states
        self.activity_states = {code: False for code in self.codes}

        self.base_prompt = f"""
        You are an experienced video annotator specialized in eye-tracking data analysis.

        **Task:**
        - Analyze the frames of this egocentric video, the red circle in the overlay indicates where the wearer is looking.
        - Identify when any of the specified activities happen in the video based on the visual content (video feed) and the gaze location (red circle).

        **Activities and Corresponding Codes:**

        The activities are:
        {self.activities}

        The corresponding codes are:
        {self.codes}

        **Instructions:**

        - For each frame:
            - Examine the visual elements and the position of the gaze overlay.
            - Determine if any of the specified activities are detected in the frame.
                - If an activity is detected, record the following information:
                    - **Frame Number:** [frame number]
                    - **Timestamp:** [timestamp from the provided dataframe]
                    - **Code:** [corresponding activity code]
                - If an activity is not detected, move to the next frame. 
        - Only consider the activities listed above. Be as precise as possible. 
        - Ensure the output is accurate and formatted correctly.

        **Output Format:**

        ```
        Frame [frame number]: Timestamp - [timestamp], Code - [code]
        ```

        **Examples:**

        - If in frame 25 the user is cutting a red pepper and the timestamp is 65, the output should be:
            ```
            Frame 25: Timestamp - 65, Code - cutting_red_pper
            ```
        - If in frame 50 the user is looking at the rear mirror, the output should be:
            ```
            Frame 50: Timestamp - [timestamp], Code - looking_rear_mirror
            ```
        """

        self.last_event = None

    def is_within_time_range(self, timestamp):
        # Check if the timestamp is within the start_time_seconds and end_time_seconds
        if self.start_time_seconds is not None and timestamp < self.start_time_seconds:
            return False
        if self.end_time_seconds is not None and timestamp > self.end_time_seconds:
            return False
        return True

    async def query_frame(self, index, session):
        # Check if the frame's timestamp is within the specified time range
        timestamp = self.mydf.iloc[index]['timestamp [s]']
        if not self.is_within_time_range(timestamp):
            #print(f"Timestamp {timestamp} is not within selected timerange")
            return None

        base64_frames_content = [{"image": self.base64Frames[index], "resize": 768}]
        video_gaze_df_content = [self.mydf.iloc[index].to_dict()]

        PROMPT_MESSAGES = [
            {
                "role": "system",
                "content": (self.base_prompt),
            },
            {
                "role": "user",
                "content": f"The frames are extracted from this video and the timestamps and frame numbers are stored in this dataframe: {json.dumps(video_gaze_df_content)}",
            },
            {
                "role": "user",
                "content": base64_frames_content
            }
        ]

        params = {
            "model": "gpt-4o",
            "messages": PROMPT_MESSAGES,
            "max_tokens": 300,
        }
        headers = {
            "Authorization": f"Bearer {self.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        retry_count = 0
        max_retries = 5
        while retry_count < max_retries:
            async with session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=params) as response:
                if response.status == 200:
                    result = await response.json()
                    response_message = result['choices'][0]['message']['content']
                    print("Response from OpenAI API:", response_message)

                    # Updated regex pattern to match the new output format
                    pattern = r'Frame\s(\d+):\sTimestamp\s-\s([\d.]+),\sCode\s-\s(\w+_\w+)'
                    matches = re.findall(pattern, response_message)

                    if matches:
                        for match in matches:
                            frame_number = int(match[0])
                            timestamp = float(match[1])
                            code = match[2]
                            # # Check if the activity code is valid
                            if code not in self.codes:
                                print("The activity was not detected")
                                continue

                            # Get the current state of the activity
                            activity_active = self.activity_states[code]
                        
                            if not activity_active:
                                # Activity is starting or being detected for the first time
                                self.activity_states[code] = True
                                send_event_to_cloud(self.workspaceid, self.recid, code, timestamp, self.cloud_token)
                                logger.info(f"Activity detected: {code}")
                            else:
                                # Activity already detected, ignore
                                logger.debug(f"Event for {code} already sent - ignoring.")
                                
                        return {
                            "frame_id": frame_number,
                            "timestamp [s]": timestamp,
                            "code": code,
                        }
                    else:
                        print("No match found in the response")
                        return None
                elif response.status == 429:
                    retry_count += 1
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.warning(f"Rate limit hit. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.warning(f"Error: {response.status}")
                    return None
        print("Max retries reached. Exiting.")
        return None

    async def binary_search(self, session, start, end, identified_activities):
        if start >= end:
            return []

        mid = (start + end) // 2
        #print(f"Binary search range: {start}-{end}, mid: {mid}")

        results = []
        # Process the mid frame and ensure both prompts are evaluated
        mid_frame_result = await self.query_frame(mid, session)
        if mid_frame_result:
            activity = mid_frame_result["code"]
            if activity not in identified_activities:
                identified_activities.add(activity)
                results.append(mid_frame_result)
            left_results = await self.binary_search(session, start, mid, identified_activities)
            results.extend(left_results)
        else:
            right_results = await self.binary_search(session, mid + 1, end, identified_activities)
            results.extend(right_results)
        return results

    async def process_batches(self, session, batch_size):
        identified_activities = set()
        all_results = []
        for i in range(0, len(self.base64Frames), batch_size):
            end = min(i + batch_size, len(self.base64Frames))
            batch_results = await self.binary_search(session, i, end, identified_activities)
            all_results.extend(batch_results)
            #print(f"Processed batch {i} to {end}, results: {batch_results}")

    async def prompting(self, save_path, batch_size):
        async with aiohttp.ClientSession() as session:
            activity_data = await self.process_batches(session, batch_size)
            print("Filtered Activity Data:", activity_data)
            output_df = pd.DataFrame(activity_data)
            output_df.to_csv(os.path.join(save_path, "output_detected_events.csv"), index=False)
            return output_df
            #return await self.process_batches(session, batch_size, save_path)

