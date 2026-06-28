import subprocess
import json
import os
import re
import logging

logger = logging.getLogger("media_backend")


class VideoProcessor:
    """
    Subprocess-based wrapper for FFmpeg and FFprobe to perform robust, optimized video operations.
    """

    @staticmethod
    def run_command(cmd: list[str]) -> tuple[str, str]:
        """
        Executes a command and returns stdout and stderr. Raises error if execution fails.
        """
        try:
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            return result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}. Error: {e.stderr}")
            raise RuntimeError(f"FFmpeg operation failed: {e.stderr.strip()}")

    @classmethod
    def get_video_info(cls, video_path: str) -> dict:
        """
        Queries video attributes using FFprobe and parses JSON metadata.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at {video_path}")

        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            video_path,
        ]

        try:
            stdout, _ = cls.run_command(cmd)
            info = json.loads(stdout)
        except Exception as e:
            logger.warning(
                f"Failed parsing video info using JSON, running regex fallback. Error: {e}"
            )
            return cls._get_video_info_fallback(video_path)

        video_stream = None
        audio_stream = None

        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video" and not video_stream:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and not audio_stream:
                audio_stream = stream

        if not video_stream:
            raise RuntimeError("No valid video stream detected in input file.")

        # Determine FPS
        fps = 25.0
        r_frame_rate = video_stream.get("r_frame_rate", "25/1")
        if r_frame_rate and "/" in r_frame_rate:
            try:
                num, den = map(float, r_frame_rate.split("/"))
                if den != 0:
                    fps = num / den
            except ValueError:
                pass

        # Determine duration
        duration = 0.0
        duration_str = video_stream.get("duration") or info.get("format", {}).get("duration")
        if duration_str:
            try:
                duration = float(duration_str)
            except ValueError:
                pass

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        frame_count = int(video_stream.get("nb_frames") or 0)

        # Calculate frame count fallback if not found
        if frame_count == 0 and duration > 0:
            frame_count = int(duration * fps)

        return {
            "fps": round(fps, 3),
            "duration": round(duration, 3),
            "width": width,
            "height": height,
            "has_audio": audio_stream is not None,
            "frame_count": frame_count or 100,
            "codec": video_stream.get("codec_name", "h264"),
        }

    @classmethod
    def _get_video_info_fallback(cls, video_path: str) -> dict:
        """
        Regex-based parsing fallback for ffprobe execution issues.
        """
        cmd = ["ffmpeg", "-i", video_path]
        try:
            # ffmpeg always outputs stream info to stderr when called with only input path
            process = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            output = process.stderr
        except Exception:
            return {
                "fps": 25.0,
                "duration": 10.0,
                "width": 1280,
                "height": 720,
                "has_audio": True,
                "frame_count": 250,
                "codec": "h264",
            }

        # Width/height parsing
        width, height = 1280, 720
        dim_match = re.search(r", (\d{3,4})x(\d{3,4})", output)
        if dim_match:
            width = int(dim_match.group(1))
            height = int(dim_match.group(2))

        # FPS parsing
        fps = 25.0
        fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", output)
        if fps_match:
            fps = float(fps_match.group(1))

        # Duration parsing
        duration = 10.0
        dur_match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2})\.(\d{2})", output)
        if dur_match:
            hours = int(dur_match.group(1))
            minutes = int(dur_match.group(2))
            seconds = int(dur_match.group(3))
            centiseconds = int(dur_match.group(4))
            duration = hours * 3600 + minutes * 60 + seconds + centiseconds / 100.0

        has_audio = "Audio:" in output
        frame_count = int(duration * fps)

        return {
            "fps": round(fps, 3),
            "duration": round(duration, 3),
            "width": width,
            "height": height,
            "has_audio": has_audio,
            "frame_count": frame_count or 100,
            "codec": "h264",
        }

    @classmethod
    def extract_frames(cls, video_path: str, output_dir: str) -> tuple[str, float]:
        """
        Extracts all video frames as PNG images into a target directory.
        Returns the output file format pattern and the framerate.
        """
        os.makedirs(output_dir, exist_ok=True)
        info = cls.get_video_info(video_path)
        fps = info["fps"]

        pattern = os.path.join(output_dir, "frame_%08d.png")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-q:v",
            "2",  # High quality extraction
            pattern,
        ]

        logger.info(f"Extracting frames from {video_path} at {fps} FPS...")
        cls.run_command(cmd)
        return pattern, fps

    @classmethod
    def assemble_video(
        cls,
        frame_dir: str,
        original_video_path: str,
        output_path: str,
        fps: float,
        has_audio: bool,
    ) -> str:
        """
        Reassembles enhanced frames into a high-quality video using FFmpeg, preserving audio.
        """
        frame_pattern = os.path.join(frame_dir, "frame_%08d.png")

        # Build assembly command
        # Input 0: sequence of frames
        # Input 1: original video (for audio copying)
        cmd = ["ffmpeg", "-y", "-r", str(fps), "-i", frame_pattern]

        if has_audio and os.path.exists(original_video_path):
            cmd.extend(["-i", original_video_path])
            cmd.extend(
                [
                    "-map",
                    "0:v",  # Video from frame input
                    "-map",
                    "1:a?",  # Audio from original input (optional if missing)
                    "-c:a",
                    "aac",  # AAC encoder for general device support
                    "-b:a",
                    "192k",  # Audio bitrate
                ]
            )
        else:
            cmd.extend(["-map", "0:v"])

        # Video encoding settings for performance and premium web streaming compatibility
        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "medium",  # Balanced encoding speed vs size
                "-crf",
                "18",  # Low crf = high quality visually lossless
                output_path,
            ]
        )

        logger.info(f"Reassembling video to {output_path}...")
        cls.run_command(cmd)
        return output_path

    @classmethod
    def compress_video(cls, video_path: str, output_path: str) -> str:
        """
        Compresses a video to save SaaS cloud bandwidth using a fast, high-quality H264 profile.
        """
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-c:v",
            "libx264",
            "-crf",
            "24",
            "-preset",
            "faster",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            output_path,
        ]
        logger.info(f"Compressing video from {video_path}...")
        cls.run_command(cmd)
        return output_path
