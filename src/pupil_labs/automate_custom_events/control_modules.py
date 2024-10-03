import pandas as pd
from pathlib import Path
import os
import glob
import logging
import numpy as np
from pupil_labs.automate_custom_events.cloud_interaction import download_recording
from pupil_labs.automate_custom_events.read_data import get_baseframes, create_gaze_overlay_video
from pupil_labs.automate_custom_events.process_frames import ProcessFrames
from pupil_labs.dynamic_content_on_rim.video.read import read_video_ts


async def run_modules(OPENAI_API_KEY, worksp_id, rec_id, cloud_api_key, download_path,
                      recpath, description, event_code, batch_size, start_time_seconds, end_time_seconds
                      ):

    #############################################################################
    # 1. Download, read data, and create gaze overlay video to be sent to OpenAI
    #############################################################################
    logging.info("[white bold on #0d122a]◎ Getting the recording data from Pupil Cloud! ⚡️[/]", extra={"markup": True})

    download_recording(rec_id, worksp_id, download_path, cloud_api_key)
    recpath = Path(download_path / rec_id)
    files = glob.glob(str(Path(recpath, "*.mp4")))
    gaze_overlay_path = os.path.join(recpath, "gaze_overlay.mp4")
    if os.path.exists(gaze_overlay_path):
        logging.debug(f"{gaze_overlay_path} exists.")

    else:
        logging.warning(f"{gaze_overlay_path} does not exist.")
        raw_video_path = files[0]

        # Format to read timestamps
        oftype = {"timestamp [ns]": np.uint64}

        # read video
        _, frames, pts, ts = read_video_ts(raw_video_path)

        # Read gaze data
        logging.debug("Reading gaze data...")
        gaze_df = pd.read_csv(Path(recpath, 'gaze.csv'), dtype=oftype)

        # Read the world timestamps (needed for gaze module)
        logging.debug("Reading world timestamps...")

        world_timestamps_df = pd.read_csv(
            Path(recpath, "world_timestamps.csv"), dtype=oftype
        )

        # Prepare df for gaze overlay
        ts_world = world_timestamps_df["timestamp [ns]"]

        video_for_gaze_module = pd.DataFrame({
            "frames": np.arange(frames),
            "pts": [int(pt) for pt in pts],
            "timestamp [ns]": ts_world,
        })

        logging.debug("Merging video and gaze dfs..")
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

        # If it doesn't exist
        create_gaze_overlay_video(merged_sc_gaze, raw_video_path, ts_world, gaze_overlay_path)
        merged_sc_gaze.to_csv(os.path.join(recpath, 'merged_sc_gaze_GM.csv'), index=False)

    #############################################################################
    # 2. Read gaze_overlay_video and get baseframes
    #############################################################################
    video_df_for_modules, baseframes_modules = get_baseframes(gaze_overlay_path)
    output_get_baseframes = pd.DataFrame(video_df_for_modules)
    output_get_baseframes.to_csv(os.path.join(recpath, 'output_get_baseframes.csv'), index=False)

    #############################################################################
    # 3. Process Frames with GPT-v
    #############################################################################
    logging.info("Start processing the frames..")
    async_process_frames = ProcessFrames(baseframes_modules, video_df_for_modules, OPENAI_API_KEY, cloud_api_key, rec_id, worksp_id, description,
                                         event_code, int(batch_size),
                                         start_time_seconds, end_time_seconds
                                         )
    
    async_process_frames_output_events = await async_process_frames.prompting(recpath, int(batch_size))
    print(async_process_frames_output_events)
    final_output_path = pd.DataFrame(async_process_frames_output_events)
    final_output_path.to_csv(os.path.join(recpath, 'custom_events.csv'), index=False)
    logging.info("[white bold on #0d122a]◎ Activity recognition completed and events sent! ⚡️[/]", extra={"markup": True})

    return final_output_path
