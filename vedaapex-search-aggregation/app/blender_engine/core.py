import subprocess
import os
import logging
from typing import Dict, Any

logger = logging.getLogger("blender_engine")


class BlenderEngine:
    """
    Core engine wrapper to run headless Blender procedural scripts.
    Requires Blender to be installed in the system PATH.
    """

    @staticmethod
    def run_script(script_path: str, args: Dict[str, Any]) -> str:
        """
        Executes a blender script in headless mode.
        """
        output_file = args.get("output_path", "model.glb")

        # Build command: blender -b --python script.py -- [args]
        cmd = [
            "blender",
            "-b",  # Background mode
            "--python",
            script_path,
            "--",
            "--output",
            output_file,
        ]

        # Add additional procedural args
        for k, v in args.items():
            if k != "output_path":
                cmd.extend([f"--{k}", str(v)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Blender output: {result.stdout}")
            return output_file
        except subprocess.CalledProcessError as e:
            logger.error(f"Blender script failed: {e.stderr}")
            raise Exception(f"3D Generation Error: {e.stderr}")

    @staticmethod
    def create_mesh_task(task_type: str, params: Dict[str, Any]) -> str:
        """
        Route to specific procedural scripts.
        """
        # Logic to map task_type to specific scripts in app/generators/
        script_map = {
            "chair": "app/generators/furniture_gen.py",
            "room": "app/room_designer/room_gen.py",
        }

        script = script_map.get(task_type, "app/generators/primitive_gen.py")
        return BlenderEngine.run_script(script, params)
