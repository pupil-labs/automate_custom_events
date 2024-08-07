
from openai import OpenAI
import pandas as pd
import re
import os
import json
from pupil_labs.automate_custom_events.get_cost import OpenAICost
import aiohttp
from pupil_labs.automate_custom_events.cloud_interaction import send_event_to_cloud

import asyncio
class ActivityRecognition:
    def __init__(self, base64Frames, video_df, OPENAI_API_KEY):
        self.base64Frames = base64Frames
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.video_df = video_df
        self.object = "book"
        self.session_cost = 0
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
            "max_tokens": 300,
        }

        result = self.client.chat.completions.create(**params)
        response = result.choices[0].message.content
        print("Response from OpenAI API:", response)

        # response_cost = (
        #     response.usage.prompt_tokens / int(1e6) * OpenAICost.input_cost(self.model)
        #     + response.usage.completion_tokens
        #     / int(1e6)
        #     * OpenAICost.output_cost(self.model)
        #     + OpenAICost.frame_cost(self.model)
        # )

        # TTS_cost = (
        #     len(response.choices[0].message.content)
        #     / int(1e6)
        #     * OpenAICost.output_cost("tts-1")
        # )
        # self.session_cost += response_cost + TTS_cost
        # print(
        #     f"R: {response.choices[0].message.content}, approx cost(GPT/TTS): {response_cost} / {TTS_cost} $ Total: {response_cost+TTS_cost} $"
        # )

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
        output_df.to_csv(os.path.join(save_path, "output_activity_recognition_events.csv"), index=False)
        return output_df

class ActivityRecognitionAsync:
    def __init__(self, base64Frames, video_df, OPENAI_API_KEY, recID, workID, cloudtoken, object, activity1, activity2, code1, code2):
        self.base64Frames = base64Frames
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.video_df = video_df
        self.recid = recID
        self.workspaceid = workID
        self.cloud_token = cloudtoken
        self.OPENAI_API_KEY = OPENAI_API_KEY
        self.object = object
        self.session_cost = 0
        self.code1 = code1
        self.code2 = code2
        self.activity1 = f"""Activity 1: {activity1}". 
        This frame should depict the exact moment this happens: {activity1}. 
        Code this frame as '{code1}'. 
        """

        self.activity2 = f"""Activity 2: {activity2}". 
        This frame should depict the exact moment this happens: {activity2}. 
        """

        self.base_prompt = f"""Act as an experienced video-annotator. You will be given frames and you are assigned a task to identify frames with pre-defined descriptions and tag them by adding labels. 
        Identify frames that match the following activities and send the respective codes :
        - Activity 1: {self.activity1}. Code this frame as {code1}. 
        - Activity 2: {self.activity2}. Code this frame as {code2}. 
        If a frame does not match either activity, code this frame as None. 
        Find only the frame that matches this description. You will be penalized if you return more than one frames.
        """        
        
        self.format = f"""The format should be always the same except for the variables that change (<number>, <activity_code>, <timestamp_float_number>). 
        Do not add any extra dots, letters, or characters. 
        Here is the format: "Frame <frame_number>: Activity - <activity_variable>, Timestamp - <timestamp_float_number>". 
        For example, if you find a frame that matches the description {activity1}: "Frame 120: Activity - {code1}, Timestamp - 4.798511111"
        Or for example, if you find a frame that matches the description {activity2}: "Frame 125: Activity - {code2}, Timestamp - 4.798911111"
        Or for example, if a frame doesn't match any of those activities: "Frame 130: Activity - None, Timestamp - 4.798911111"
        """


    async def query_frame(self, index, session):
        base64_frames_content = [{"image": self.base64Frames[index], "resize": 768}]
        video_df_content = [self.video_df.iloc[index].to_dict()]

        PROMPT_MESSAGES = [
            {"role": "system", "content": (self.base_prompt + self.format)},
            {"role": "user", "content":  f"Here are the activities: {self.activity1} ,  {self.activity2})"},
            {"role": "user", "content": f"The frames are extracted from this video and the timestamps and frame numbers are stored in this dataframe: {json.dumps(video_df_content)}"},
            {"role": "user", "content": base64_frames_content},
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

                    # response_cost = (
                    #     response.usage.prompt_tokens / int(1e6) * OpenAICost.input_cost(self.model)
                    #     + response.usage.completion_tokens
                    #     / int(1e6)
                    #     * OpenAICost.output_cost(self.model)
                    #     + OpenAICost.frame_cost(self.model)
                    # )

                    # TTS_cost = (
                    #     len(response.choices[0].message.content)
                    #     / int(1e6)
                    #     * OpenAICost.output_cost("tts-1")
                    # )
                    # self.session_cost += response_cost + TTS_cost
                    # print(
                    #     f"R: {response_message}, approx cost(GPT/TTS): {response_cost} / {TTS_cost} $ Total: {response_cost+TTS_cost} $"
                    # )

                    pattern = r'Frame\s(\d+):\sActivity\s-\s([^,]+),\sTimestamp\s-\s([\d.]+)(?=\s|$)'
                    match = re.search(pattern, response_message)

                    if match:
                        frame_number = int(match.group(1))
                        activity = match.group(2)
                        timestamp = float(match.group(3))
                        if activity == self.code1 or activity == self.code1:
                            send_event_to_cloud(self.workspaceid, self.recid, activity, timestamp, self.cloud_token)
                        return {"frame_id": frame_number, "timestamp [s]": timestamp, "activity": activity}
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

    async def binary_search(self, start, end, identified_activities, session):
        if start >= end:
            return []

        mid = (start + end) // 2
        print(f"Binary search range: {start}-{end}, mid: {mid}")

        mid_frame_result = await self.query_frame(mid, session)
        results = []

        if mid_frame_result:
            activity = mid_frame_result["activity"]
            if activity not in identified_activities:
                identified_activities.add(activity)
                results.append(mid_frame_result)
            left_results = await self.binary_search(start, mid, identified_activities, session)
            results.extend(left_results)
        else:
            right_results = await self.binary_search(mid + 1, end, identified_activities, session)
            results.extend(right_results)
        return results

    async def prompting(self, save_path):
        async with aiohttp.ClientSession() as session:
            identified_activities = set()
            activity_data = await self.binary_search(0, len(self.base64Frames), identified_activities, session)
            print("Filtered Activity Data:", activity_data)
            output_df = pd.DataFrame(activity_data)
            output_df.to_csv(os.path.join(save_path, "output_activity_recognition_events.csv"), index=False)
            return output_df