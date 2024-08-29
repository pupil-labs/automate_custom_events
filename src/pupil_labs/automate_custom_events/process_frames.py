from openai import OpenAI
import pandas as pd
import re
import os
import json
import aiohttp
from pupil_labs.automate_custom_events.cloud_interaction import send_event_to_cloud
import asyncio

class ProcessFrames:
    def __init__(self, base64Frames, vid_modules, OPENAI_API_KEY, cloudtoken, recID, workID, 
                 gm_description, gm_code, arm_activity1, arm_event_code1, batch_size,
                 start_time_seconds=25, end_time_seconds=35):
        
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
        self.gm_description = gm_description
        self.arm_activity = arm_activity1
        # Flags for tracking activities
        self.gm_flag = False  # Flag for gaze module
        self.arm_flag = False  # Flag for arm activity

        # Time range parameters
        self.start_time_seconds = int(start_time_seconds)
        self.end_time_seconds = int(end_time_seconds)

        # Prompts (GM = gaze module, ARM = Activity Recognition Module)
        self.gm_start_code = "starts_" + gm_code
        self.gm_end_code = "stops_" + gm_code
        self.arm_start_code = "starts_" + arm_event_code1
        self.arm_end_code = "stops_" + arm_event_code1

        self.all_codes = [
            self.gm_start_code, 
            self.gm_end_code,
            self.arm_start_code, 
            self.arm_end_code
        ]

        self.base_prompt = f"""
        Act as an experienced video annotator specialized in eye-tracking data. You will analyze video frames where a red circle indicates 
        the user's gaze point.

        For every frame, perform the following two tasks:

        1. **Gaze Activity Recognition**: Identify if the frame shows the user engaged in the following activity: "{gm_description}". If so, send the corresponding code: {self.gm_start_code} or {self.gm_end_code}. Remember, the red circle indicates the user's gaze point.

        2. **Scene Activity Recognition**: Identify if the frame shows the user performing this specific activity: "{arm_activity1}". If so, send the corresponding code: {self.arm_start_code} or {self.arm_end_code}.

        **Important**:
        - **Scan each frame for all possible events**. If multiple activities are observed in the same frame, return the code corresponding to the activity that is best described in the frame.
        - If no events are observed in a frame, respond with code == None.

        Ensure your responses are precise and include all relevant codes ({self.gm_start_code}, {self.gm_end_code}, {self.arm_start_code}, {self.arm_end_code}) that correspond to the identified activities within the frame. Adhering to these instructions is crucial for accurate annotation.
        """

        self.format = f"""
        The format should be always the same except for the variables that change (<number>, <timestamp_float_number>, <code>). 
        Do not add any extra dots, letters, or characters. 
        
        - If you find a frame that matches the start of the activity "The user starts {gm_description}" the response should be: Frame <self.mydf['frames']>: Timestamp - <self.mydf['timestamp [s]]>, Code - {self.gm_start_code}
        - If you find a frame that matches the end of the activity "The user stops {gm_description}" the response should be: Frame <self.mydf['frames']>: Timestamp - <self.mydf['timestamp [s]]>, Code - {self.gm_end_code}
        - If you find a frame that matches the start of the activity {arm_activity1}: Frame <self.mydf['frames']>: Timestamp - <self.mydf['timestamp [s]]>, Code - {self.arm_start_code}
        - If you find a frame that matches the end of the activity {arm_activity1}: Frame <self.mydf['frames']>: Timestamp - <self.mydf['timestamp [s]]>, Code - {self.arm_end_code}
        - If a frame doesn't match any of those activities: Frame <self.mydf['frames']>: Timestamp - <self.mydf['timestamp [s]]>, Code - None
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
            print(f"Timestamp {timestamp} is not within selected timerange")
            return None

        base64_frames_content = [{"image": self.base64Frames[index], "resize": 768}]
        video_gaze_df_content = [self.mydf.iloc[index].to_dict()]
        print(f"GM Flag is: {self.gm_flag}")
        print(f"ARM Flag is: {self.arm_flag}")

              
        PROMPT_MESSAGES = [
            {
                "role": "system",
                "content": (self.base_prompt + self.format),
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

                    pattern = r'Frame\s(\d+):\sTimestamp\s-\s([\d.]+),\sCode\s-\s(\w+)'
                    matches = re.findall(pattern, response_message)

                    if matches:
                        for match in matches:
                            frame_number = int(match[0])
                            timestamp = float(match[1])
                            code = match[2]
                            # LOGGING for Debugging
                            print(f"GM Flag: {self.gm_flag}, ARM Flag: {self.arm_flag}, Detected Code: {code}")

                            # --- Gaze Module ---
                            gm_event_sent = False  
                            if not self.gm_flag:  # If gm_flag is False, check for start event
                                if code == self.gm_start_code:
                                    self.gm_flag = True
                                    send_event_to_cloud(self.workspaceid, self.recid, code, timestamp, self.cloud_token)
                                    self.last_event = code
                                    print("Send GM_start_event when activity hasn't started (Flag false)")
                                    gm_event_sent = True
                            elif code == self.gm_end_code and self.gm_flag:  # If gm_flag is True, check for end event
                                self.gm_flag = False
                                send_event_to_cloud(self.workspaceid, self.recid, code, timestamp, self.cloud_token)
                                self.last_event = code
                                print("Send GM_end_event when activity has already started (Flag true)")
                                gm_event_sent = True
                            
                            # If GM event is sent, return the response and don't process further
                            if gm_event_sent:
                                return {
                                    "frame_id": frame_number,
                                    "timestamp [s]": timestamp,
                                    "code": code,
                                }

                            # --- Activity Recognition Module ---
                            arm_event_sent = False  # Track whether we send ARM events
                            if not self.arm_flag:  # If arm_flag is False, check for start event
                                if code == self.arm_start_code:
                                    self.arm_flag = True
                                    send_event_to_cloud(self.workspaceid, self.recid, code, timestamp, self.cloud_token)
                                    self.last_event = code
                                    print("Send ARM_start_event when activity hasn't started (Flag false)")
                                    arm_event_sent = True
                            elif code == self.arm_end_code and self.arm_flag:  # If arm_flag is True, check for end event
                                self.arm_flag = False
                                send_event_to_cloud(self.workspaceid, self.recid, code, timestamp, self.cloud_token)
                                self.last_event = code
                                print("Send ARM_end_event when activity has already started (Flag true)")
                                arm_event_sent = True
                            
                            # If ARM event is sent, return the response
                            if arm_event_sent:
                                return {
                                    "frame_id": frame_number,
                                    "timestamp [s]": timestamp,
                                    "code": code,
                                }

                        # No event sent, return None
                        return None
                    else:
                        print("No match found in the response")
                        return None
                elif response.status == 429:
                    retry_count += 1
                    wait_time = 2 ** retry_count  # Exponential backoff
                    print(f"Rate limit hit. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"Error: {response.status}")
                    return None
        print("Max retries reached. Exiting.")
        return None
    
    async def binary_search(self, session, start, end, identified_activities):
            if start >= end:
                return []

            mid = (start + end) // 2
            print(f"Binary search range: {start}-{end}, mid: {mid}")

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
            print(f"Processed batch {i} to {end}, results: {batch_results}")

    async def prompting(self, save_path, batch_size):
        async with aiohttp.ClientSession() as session:
            activity_data = await self.process_batches(session, batch_size)
            print("Filtered Activity Data:", activity_data)
            output_df = pd.DataFrame(activity_data)
            output_df.to_csv(os.path.join(save_path, "output_detected_events.csv"), index=False)
            return output_df
            #return await self.process_batches(session, batch_size, save_path)

