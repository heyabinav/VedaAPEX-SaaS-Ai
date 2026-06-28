import io
import logging

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger("media_backend")


class BackgroundRemover:
    """
    Background removal using rembg when available, with GrabCut fallback for CPU-only environments.
    """

    def __init__(self):
        self.rembg_available = False
        self._rembg_remove = None

        try:
            from rembg import remove

            self._rembg_remove = remove
            self.rembg_available = True
            logger.info("rembg background removal is available.")
        except Exception as error:
            logger.warning(f"rembg is unavailable, falling back to GrabCut. Detail: {error}")

    def remove_background_image(
        self,
        input_path: str,
        output_path: str,
        background_color: tuple[int, int, int] | None = None,
    ) -> str:
        if self.rembg_available and self._rembg_remove:
            with Image.open(input_path) as source_image:
                result = self._rembg_remove(source_image)
                output_image = (
                    result if isinstance(result, Image.Image) else Image.open(io.BytesIO(result))
                )

                if background_color is not None:
                    canvas = Image.new("RGBA", output_image.size, (*background_color, 255))
                    output_image = Image.alpha_composite(
                        canvas, output_image.convert("RGBA")
                    ).convert("RGB")
                else:
                    output_image = output_image.convert("RGBA")

                output_image.save(output_path)
                return output_path

        return self._remove_with_grabcut(input_path, output_path, background_color)

    def remove_background_frame(
        self,
        frame: np.ndarray,
        background_color: tuple[int, int, int] | None = (255, 255, 255),
    ) -> np.ndarray:
        if self.rembg_available and self._rembg_remove:
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            result = self._rembg_remove(image)
            output_image = (
                result if isinstance(result, Image.Image) else Image.open(io.BytesIO(result))
            )

            if background_color is not None:
                canvas = Image.new("RGBA", output_image.size, (*background_color, 255))
                output_image = Image.alpha_composite(canvas, output_image.convert("RGBA")).convert(
                    "RGB"
                )
            else:
                output_image = output_image.convert("RGBA").convert("RGB")

            return cv2.cvtColor(np.array(output_image), cv2.COLOR_RGB2BGR)

        return self._grabcut_frame(frame, background_color)

    def _remove_with_grabcut(
        self,
        input_path: str,
        output_path: str,
        background_color: tuple[int, int, int] | None,
    ) -> str:
        image = cv2.imread(input_path)
        if image is None:
            raise ValueError(f"Failed to read image at {input_path}")

        processed = self._grabcut_frame(image, background_color)
        cv2.imwrite(output_path, processed)
        return output_path

    def _grabcut_frame(
        self, frame: np.ndarray, background_color: tuple[int, int, int] | None
    ) -> np.ndarray:
        height, width = frame.shape[:2]
        rect = (10, 10, max(1, width - 20), max(1, height - 20))
        mask = np.zeros(frame.shape[:2], np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        cv2.grabCut(frame, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        foreground_mask = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")
        foreground = frame * foreground_mask[:, :, np.newaxis]

        if background_color is None:
            background = np.zeros_like(frame)
        else:
            background = np.full_like(frame, background_color, dtype=np.uint8)

        inverse_mask = 1 - foreground_mask[:, :, np.newaxis]
        return foreground + (background * inverse_mask)
