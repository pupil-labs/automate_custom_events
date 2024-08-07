
from openai import OpenAI
import pandas as pd
import re
import os
import json
import time
import random
import openai
from tenacity import retry, stop_after_attempt, wait_random_exponential
from pupil_labs.automate_custom_events.get_cost import OpenAICost
import asyncio 
import aiohttp
from pupil_labs.automate_custom_events.cloud_interaction import send_event_to_cloud

class GazeMappingAsync:
    def __init__(self, base64Frames, vid_gaze_module, OPENAI_API_KEY, recID, workID, object, description, code):
        self.base64Frames = base64Frames
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.mydf = vid_gaze_module
        self.object_code = code
        self.session_cost = 0
        self.cloud_token = "KBezmSp3cq2jE2RNTvrSvWeYkhFQMENk2hTjw7hEZq3F"
        self.recid = recID
        self.OPENAI_API_KEY = OPENAI_API_KEY
        self.workspaceid= workID
        self.description = description
        self.base_prompt = f"""
        Act as an experienced video-annotator. I am sending you images with a red circle which indicates where the wearer is looking at. 
        Identify frames that match these descriptions: 
        1. The user starts {description}. 
        2. The user stops {description}
        Find only the frame that match these descriptions. You will be penalized if you return more than one frames.
        """

        self.description_code = f"""For frames that match this description "The user starts {description}, send code== start_{code}. 
        For frames that match this description "The user stops {description}, send code== stop_{code}. 
        Otherwise, if the frame does not match any of those descriptions send a code==None. 
        """
        self.format = f"""
        The format should be always the same except for the variables that change (<number>, <timestamp_float_number>, <code>). 
        Do not add any extra dots, letters, or characters. 
        Here is the format: Frame <self.mydf['frames']>: Timestamp - <self.mydf['timestamp [s]]>, Code - <code>. 
        For example, if you find a frame that matches the description "The user starts {description}" the response should be: Frame 9: Timestamp - 4.798511111, Code - start_{code}
        For example, if you find a frame that matches the description "The user stops {description}" the response should be: Frame 9: Timestamp - 4.798511111, Code - stop_{code}

        If a frame does not match this description {description}: Frame 9: Timestamp - 4.798511111, Code - None
        """
        self.token_count =0

    async def query_frame(self, index, session):
        base64_frames_content = [{"image": self.base64Frames[index], "resize": 768}]
        video_gaze_df_content = [self.mydf.iloc[index].to_dict()]

        PROMPT_MESSAGES = [
            {
                "role": "system",
                "content": (self.base_prompt + self.format),
            },
            {
                "role": "user",
                "content": f"{self.description_code}",
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

                    pattern = r'Frame\s(\d+):\sTimestamp\s-\s([\d.]+),\sCode\s-\s(\w+)'
                    match = re.search(pattern, response_message)

                    if match:
                        frame_number = int(match.group(1))
                        timestamp = float(match.group(2))
                        code = match.group(3)
                        if code == f"start_{self.object_code}" or code == f"stop_{self.object_code}":
                            send_event_to_cloud(self.workspaceid, self.recid, code, timestamp, self.cloud_token)
                            return {
                            "frame_id": frame_number,
                            "timestamp [s]": timestamp,
                            "code": code,
                            "gaze_at": True,
                        }
                        else:
                            continue
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
            activity = mid_frame_result["gaze_at"]
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
            output_df.to_csv(os.path.join(save_path, "output_gaze_module_events.csv"), index=False)
            return output_df

class GazeMapping:
    def __init__(self, base64Frames, vid_gaze_module, OPENAI_API_KEY):
        self.base64Frames = base64Frames
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.mydf = vid_gaze_module
        self.object = "bottle"
        self.session_cost = 0
        self.description = f"The wearer starts looking at a {self.object}."
        self.base_prompt = f"""
        Act as an experienced video-annotator. I am sending you images with a red circle which indicates where the wearer is looking at. 
        Identify frames that match this description: {self.description}. 
        Find only the frame that matches this description. You will be penalized if you return more than one frames.
        """

        self.code = f"""For frames that match this description {self.description}, send code== {self.object}. Otherwise, send a code=='None'. 
        """
        self.format = """
        The format should be always the same except for the variables that change (<number>, <timestamp_float_number>, <code>). 
        Do not add any extra dots, letters, or characters. Here is the format: "Frame <self.mydf['frames']>: Timestamp - <self.mydf['timestamp [s]]>, Code - <code>". 
        Consider this example: "Frame 9: Timestamp - 4.798511111, Code - bottle"
        """
        self.token_count =0

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    def completion_with_backoff(self, **kwargs):
        return self.client.chat.completions.create(**kwargs)

    def query_frame(self, index, retries=10, backoff_factor=2, jitter_factor=0.1):
        base64_frames_content = [{"image": self.base64Frames[index], "resize": 768}]
        video_gaze_df_content = [self.mydf.iloc[index].to_dict()]

        PROMPT_MESSAGES = [
            {
                "role": "system",
                "content": (self.base_prompt + self.format),
            },
            {
                "role": "user",
                "content": f"Find the frame that match this description: {self.description}. {self.code}",
            },
            {
                "role": "user",
                "content": f"The frame data is: {json.dumps(video_gaze_df_content)}",
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
        
        for attempt in range(retries):
            try:
                result = self.completion_with_backoff(**params)
                #result = self.client.chat.completions.create(**params)
                response = result.choices[0].message.content

                print("Response from OpenAI API:", response)
                pattern = r'Frame\s(\d+):\sTimestamp\s-\s([\d.]+),\sCode\s-\s(\w+)'
                # self.token_count += result.usage.total_tokens

                match = re.search(pattern, response)    

                if match:
                    frame_number = int(match.group(1))
                    timestamp = float(match.group(2))
                    return {
                        "frame_id": frame_number,
                        "timestamp [s]": timestamp,
                        "gaze_at": True,
                    }
                else:
                    print("No match found in the response")
                    return None
            except openai.RateLimitError as e:
                wait_time = backoff_factor ** attempt + random.uniform(0, jitter_factor)
                print(f"Rate limit exceeded: {e}. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
        raise Exception("Exceeded maximum retries for rate limit errors.")

    def binary_search(self, start, end, identified_activities, max_tokens_per_min=30000):
        if start >= end:
            return []

        mid = (start + end) // 2
        print(f"Binary search range: {start}-{end}, mid: {mid}")

        # Check token usage and wait if necessary
        if self.token_count >= max_tokens_per_min:
            print(f"Token limit of {max_tokens_per_min} tokens per minute reached. Waiting for reset...")
            time.sleep(60)  # Wait for a minute to reset the token count
            self.token_count = 0

        mid_frame_result = self.query_frame(mid)
        results = []

        if mid_frame_result:
            activity = mid_frame_result["gaze_at"]
            if activity not in identified_activities:
                identified_activities.add(activity)
                results.append(mid_frame_result)
            left_results = self.binary_search(start, mid, identified_activities)
            results.extend(left_results)
        else:
            right_results = self.binary_search(mid + 1, end, identified_activities)
            results.extend(right_results)
        return results

    def process_batches(self, batch_size, save_path, pause_between_batches):
        identified_activities = set()
        all_results = []
        for i in range(0, len(self.base64Frames), batch_size):
            end = min(i + batch_size, len(self.base64Frames))
            batch_results = self.binary_search(i, end, identified_activities)
            all_results.extend(batch_results)
            print(f"Processed batch {i} to {end}, results: {batch_results}")

            # Pause between batches to avoid rate limits
            print(f"Pausing for {pause_between_batches} seconds to avoid rate limits.")
            time.sleep(pause_between_batches)

        print("Filtered Activity Data:", all_results)
        output_df = pd.DataFrame(all_results)
        output_df.to_csv(os.path.join(save_path, "output_gaze_module_events.csv"), index=False)
        return output_df

    def prompting(self, save_path, batch_size=10, pause_between_batches=30):

        activity_data =  self.process_batches(batch_size, save_path, pause_between_batches)
        print("Filtered Activity Data:", activity_data)
        output_df = pd.DataFrame(activity_data)
        output_df.to_csv(os.path.join(save_path, "output_activity_recognition_events.csv"), index=False)
        return output_df
    # def binary_search(self, start, end, identified_activities):
    #     if start >= end:
    #         return []

    #     mid = (start + end) // 2
    #     print(f"Binary search range: {start}-{end}, mid: {mid}")

    #     mid_frame_result = self.query_frame(mid)
    #     results = []

    #     if mid_frame_result:
    #         activity = mid_frame_result["gaze_at"]
    #         if activity not in identified_activities:
    #             identified_activities.add(activity)
    #             results.append(mid_frame_result)
    #         left_results = self.binary_search(start, mid, identified_activities)
    #         results.extend(left_results)
    #     else:
    #         right_results = self.binary_search(mid + 1, end, identified_activities)
    #         results.extend(right_results)
    #     return results

    # def prompting(self, save_path):
    #     identified_activities = set()
    #     activity_data = self.binary_search(0, len(self.base64Frames),identified_activities)
    #     print("Filtered Activity Data:", activity_data)
    #     output_df = pd.DataFrame(activity_data)
    #     output_df.to_csv(os.path.join(save_path, "output_gaze_module_events.csv"), index=False)
    #     return output_df

