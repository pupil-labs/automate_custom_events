import pandas as pd
from pathlib import Path
import os
import glob
import logging
import numpy as np
from pupil_labs.automate_custom_events.cloud_interaction import download_recording
from pupil_labs.automate_custom_events.read_data import get_baseframes, create_gaze_overlay_video
from pupil_labs.automate_custom_events.activity_recognition_module import ActivityRecognitionAsync
from pupil_labs.automate_custom_events.gaze_module import GazeMappingAsync
from pupil_labs.dynamic_content_on_rim.video.read import read_video_ts


async def run_gaze_module(OPENAI_API_KEY, worksp_id, rec_id, cloud_api_key, download_path, recpath, object_desc, description, event_code):
    download_recording(rec_id, worksp_id, download_path, cloud_api_key)
    recpath = Path(download_path / rec_id)
    files = glob.glob(str(Path(recpath, "*.mp4")))

    raw_video_path = files[0]

    # Format to read timestamps
    oftype = {"timestamp [ns]": np.uint64}

    # read video 
    _, frames, pts, ts = read_video_ts(raw_video_path)

    # Read gaze data 
    logging.info("Reading gaze data...")
    gaze_df = pd.read_csv(Path(recpath, 'gaze.csv'), dtype=oftype)

    # Read the world timestamps (needed for gaze module)
    logging.info("Reading world timestamps...")

    world_timestamps_df = pd.read_csv(
        Path(recpath, "world_timestamps.csv"), dtype=oftype
    )
    
    # Prepare df for Gaze Module
    ts_world = world_timestamps_df["timestamp [ns]"]

    video_for_gaze_module = pd.DataFrame(
        { "frames": np.arange(frames),
            "pts": [int(pt) for pt in pts],
            "timestamp [ns]": ts_world,
        }
        )
    
    logging.info("Merging video and gaze dfs..")
    selected_col = ["timestamp [ns]", "gaze x [px]",  "gaze y [px]"]
    gaze_df = gaze_df[selected_col]
    gaze_df = gaze_df.sort_values(by="timestamp [ns]")
    video_for_gaze_module = video_for_gaze_module.sort_values(by="timestamp [ns]")

    merged_sc_gaze = pd.merge_asof(
        video_for_gaze_module,
        gaze_df,
        on="timestamp [ns]",
        direction="nearest",
        suffixes=["video", "gaze"]
    )
    gaze_overlay_path = os.path.join(recpath, "gaze_overlay.mp4")

    create_gaze_overlay_video(merged_sc_gaze, raw_video_path, ts_world, gaze_overlay_path)
    merged_sc_gaze.to_csv(os.path.join(recpath, 'merged_sc_gaze_GM.csv'), index=False)

    logging.info(
            "[white bold on #0d122a]◎ Start with Gaze Mapping Module! ⚡️[/]",
            extra={"markup": True},
        )
    video_df_for_gaze_module, baseframes_gaze_module = get_baseframes(gaze_overlay_path)
    print(object_desc)
    print(description)
    print(event_code)
    # # ASYNC
    gaze_async_module = GazeMappingAsync(baseframes_gaze_module, video_df_for_gaze_module, OPENAI_API_KEY, rec_id, worksp_id, object_desc, description, event_code)
    gaze_module_async_OUTPUT = await gaze_async_module.prompting(recpath)
    print(gaze_module_async_OUTPUT)

    logging.info(
            "[white bold on #0d122a]◎ Gaze Mapping Module completed! ⚡️[/]",
            extra={"markup": True},
        )

async def run_activity_recognition_module(OPENAI_API_KEY, worksp_id, rec_id, cloud_api_key, download_path, recpath, object_desc, activity1, activity2, event_code1, event_code2):
    download_recording(rec_id, worksp_id, download_path, cloud_api_key)
    recpath = Path(download_path / rec_id)
    files = glob.glob(str(Path(recpath, "*.mp4")))

    raw_video_path = files[0]
    
    logging.info(
            "[white bold on #0d122a]◎ Start with Activity Recognition Module! ⚡️[/]",
            extra={"markup": True},
        )
    video_df_for_activity_rec_module, baseframes_activity_rec_module = get_baseframes(raw_video_path)
    output_df_activity_rec = pd.DataFrame(video_df_for_activity_rec_module)
    output_df_activity_rec.to_csv(os.path.join(recpath, 'sc_video_decoded_ARM.csv'), index=False)
    print(object_desc)
    print(activity1)
    print(activity2)
    print(event_code1)
    print(event_code2)
    
    activity_rec_async_module = ActivityRecognitionAsync(baseframes_activity_rec_module, video_df_for_activity_rec_module, OPENAI_API_KEY, rec_id, worksp_id, cloud_api_key, object_desc, activity1, activity2, event_code1, event_code2)

    activity_rec_module_OUTPUT = await activity_rec_async_module.prompting(recpath)
    print(activity_rec_module_OUTPUT)
    logging.info(
            "[white bold on #0d122a]◎ Activity Recognition Module completed! ⚡️[/]",
            extra={"markup": True},
        )
    # for index, row in activity_rec_module_OUTPUT.iterrows():
    #     print(f"Relative timestamp: {row['timestamp [s]']}")
    #     print(row['activity'])
    #     send_event_to_cloud(worksp_id, rec_id, row['activity'], row['timestamp [s]'], cloud_api_key)

