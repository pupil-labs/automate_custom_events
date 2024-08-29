import base64
import av
import logging
import cv2
import numpy as np
from rich.progress import Progress
import pandas as pd
from fractions import Fraction


def isMonotonicInc(arr):
    return np.all(np.diff(arr) >= 0)

def get_baseframes(video_path, audio=False, auto_thread_type=True):
        """
        A function to read a video, extract frames, and store them as base64 encoded strings.
        :param video_path: the path to the video
        """
        base64Frames =[]
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
                        base64Frames.append(base64.b64encode(buffer).decode("utf-8"))

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
        video_df = pd.DataFrame(
        {
            "frames": np.arange(nframes),
            "pts": [int(pt) for pt in pts],
            "timestamp [ns]": ts,
            "timestamp [s]": timestamps_s
        }
        )   
        return video_df, base64Frames #, fps, nframes, pts, ts

def get_frame(av_container, pts, last_pts, frame, audio=False):
    """
    Gets the frame at the given timestamp.
    :param av_container: The container of the video.
    :param pts: The pts of the frame we are looking for.
    :param last_pts: The last pts of the video readed.
    :param frame: Last frame decoded.
    """
    if audio:
        strm = av_container.streams.audio[0]
    else:
        strm = av_container.streams.video[0]
    if last_pts < pts:
        try:
            for frame in av_container.decode(strm):
                logging.debug(
                    f"Frame {frame.pts} read from video and looking for {pts}"
                )
                if pts == frame.pts:
                    last_pts = frame.pts
                    return frame, last_pts
                if pts < frame.pts:
                    logging.warning(f"Frame {pts} not found in video, used {frame.pts}")
                    last_pts = frame.pts
                    return frame, last_pts
        except av.EOFError:
            logging.info("End of the file")
            return None, last_pts
    else:
        logging.debug("This frame was already decoded")
        return frame, last_pts
    
def create_gaze_overlay_video(merged_video, video_path, world_timestamps_df, output_file):
    start = world_timestamps_df[0]
    merged_video = merged_video[merged_video["timestamp [ns]"] >= start]
    
    # Read first frame
    with av.open(video_path) as vid_container:
        logging.info("Reading first frames")
        vid_frame = next(vid_container.decode(video=0))
       
    num_processed_frames = 0

    # Get the output path
    logging.info(f"Output path: {output_file}")

    # Here we go!
    with av.open(video_path) as video, av.open(output_file, "w") as out_container:
        logging.info("Ready to process video")
        # Prepare the output video
        out_video = out_container.add_stream("libx264", rate=30, options={"crf": "18"})
        out_video.width =  video.streams.video[0].width
        out_video.height = video.streams.video[0].height
        out_video.pix_fmt = "yuv420p"
        out_video.codec_context.time_base = Fraction(1, 30)
       
        lpts= -1

        # For every frame in the video
        with Progress() as progress_bar:
            video_task = progress_bar.add_task(
                "📹 Processing video", total=merged_video.shape[0]
            )
            while num_processed_frames < merged_video.shape[0]:
                row = merged_video.iloc[num_processed_frames]
                # Get the frame
                vid_frame, lpts = get_frame(
                    video, int(row["pts"]), lpts, vid_frame
                )
                if vid_frame is None:
                    break
                img_original = vid_frame.to_ndarray(format="rgb24")
                
                # Prepare the frame
                frame = cv2.cvtColor(img_original, cv2.COLOR_RGB2BGR)
                frame = np.asarray(frame, dtype=np.float32)
                frame = frame[:, :, :]
                xy = row[["gaze x [px]", "gaze y [px]"]].to_numpy(dtype=np.int32)

                # make a aoi_circle on the gaze
                if not np.isnan(xy).any():
                    cv2.circle(frame, xy, 20, (0, 0, 255), 10)

                # Finally get the frame ready.
                out_ = cv2.normalize(
                    frame, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U
                )
                # Convert to av frame
                cv2.cvtColor(out_, cv2.COLOR_BGR2RGB, out_)
                np.expand_dims(out_, axis=2)
                out_frame = av.VideoFrame.from_ndarray(out_, format="rgb24")
                for packet in out_video.encode(out_frame):
                    out_container.mux(packet)
                progress_bar.advance(video_task)
                num_processed_frames += 1
            progress_bar.stop_task(video_task)
            for packet in out_video.encode(None):
                out_container.mux(packet)

            out_container.close()
            
        logging.info(
            "[white bold on #0d122a]◎ Gaze overlay video has been created! ⚡️[/]",
            extra={"markup": True},
        )
        cv2.destroyAllWindows()
    