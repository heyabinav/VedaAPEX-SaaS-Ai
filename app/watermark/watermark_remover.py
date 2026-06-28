import os
import cv2
import numpy as np
import logging

logger = logging.getLogger("media_backend")


class WatermarkRemover:
    """
    Watermark Remover implementing mask-based AI smart fill and object reconstruction
    using pre-trained LaMa models with a fallback to advanced OpenCV inpainting.
    """

    def __init__(self):
        self.lama_available = False
        self.weights_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "weights")
        os.makedirs(self.weights_dir, exist_ok=True)

        # Check if an ONNX Runtime is installed for LaMa models
        try:
            import onnxruntime as ort

            self.ort_session = None
            self.lama_model_path = os.path.join(self.weights_dir, "lama_cleaner.onnx")

            if os.path.exists(self.lama_model_path):
                self.ort_session = ort.InferenceSession(self.lama_model_path)
                self.lama_available = True
                logger.info("LaMa pre-trained ONNX model successfully loaded.")
            else:
                logger.info(
                    "LaMa ONNX model weights not found in weights/. Using OpenCV inpainting fallback."
                )
        except Exception as e:
            logger.info(f"ONNX Runtime not available or failed to load. Detail: {e}")

    def remove_watermark(
        self,
        image_path: str,
        mask_path: str,
        output_path: str,
        algorithm: str = "telea",  # "telea", "ns" (Navier-Stokes), or "lama"
    ) -> str:
        """
        Removes a watermark from an image using a black-and-white binary mask.
        White pixels (255) on the mask indicate the region to be inpainted.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Source image not found at {image_path}")
        if not os.path.exists(mask_path):
            raise FileNotFoundError(f"Watermark mask not found at {mask_path}")

        img = cv2.imread(image_path)
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

        if img is None:
            raise ValueError(f"Failed to read image at {image_path}")
        if mask is None:
            raise ValueError(f"Failed to read mask at {mask_path}")

        # Ensure the mask matches the image size
        if img.shape[:2] != mask.shape[:2]:
            logger.info("Resizing mask to match original image dimensions...")
            mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)

        # 1. Attempt LaMa cleaner AI smart fill if available
        if self.lama_available and algorithm.lower() == "lama":
            try:
                result = self._process_lama(img, mask)
                cv2.imwrite(output_path, result)
                logger.info(f"Watermark removed and saved to {output_path} (LaMa AI)")
                return output_path
            except Exception as e:
                logger.error(f"LaMa AI processing failed. Falling back to OpenCV. Error: {e}")
                # Fallback to OpenCV

        # 2. Advanced OpenCV Inpainting fallback
        return self._process_opencv_inpainting(img, mask, output_path, algorithm)

    def _process_lama(self, img: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Runs inference on the pre-trained LaMa (Large Mask Inpainting) network using ONNX.
        """
        # Preprocess image: convert to RGB, float32, normalize, transpose to [1, 3, H, W]
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]

        # LaMa works best on sizes divisible by 8
        new_h = (h // 8) * 8
        new_w = (w // 8) * 8

        img_resized = cv2.resize(img_rgb, (new_w, new_h)).astype(np.float32) / 255.0
        mask_resized = cv2.resize(mask, (new_w, new_h)).astype(np.float32) / 255.0
        mask_resized = np.expand_dims(mask_resized, axis=2)  # H, W, 1

        # Format as NCHW [1, 3, H, W] and [1, 1, H, W]
        img_input = np.expand_dims(img_resized.transpose(2, 0, 1), axis=0)
        mask_input = np.expand_dims(mask_resized.transpose(2, 0, 1), axis=0)

        # Run inference session
        inputs = {
            self.ort_session.get_inputs()[0].name: img_input,
            self.ort_session.get_inputs()[1].name: mask_input,
        }
        outputs = self.ort_session.run(None, inputs)
        output_img = outputs[0][0]  # 3, H, W

        # Postprocess: transpose, denormalize, convert back to uint8 BGR, resize to original
        output_rgb = (output_img.transpose(1, 2, 0) * 255.0).clip(0, 255).astype(np.uint8)
        output_bgr = cv2.cvtColor(output_rgb, cv2.COLOR_RGB2BGR)

        return cv2.resize(output_bgr, (w, h))

    def _process_opencv_inpainting(
        self, img: np.ndarray, mask: np.ndarray, output_path: str, algorithm: str
    ) -> str:
        """
        Advanced OpenCV inpainting pipeline using Morphological Dilation & Telea/Navier-Stokes.
        """
        logger.info(f"Running OpenCV Inpainting Pipeline (Algorithm: {algorithm})...")

        # 1. Mask preprocessing: ensure binary threshold
        _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

        # 2. Morpohological Dilation: Expand the mask slightly (by 3 pixels)
        # to ensure that the bounding edges of the watermark are fully inpainted.
        # This resolves bleeding edges and ghost residues.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated_mask = cv2.dilate(binary_mask, kernel, iterations=1)

        # 3. Select Inpainting Flag
        flags = cv2.INPAINT_TELEA
        if algorithm.lower() == "ns":
            flags = cv2.INPAINT_NS

        # 4. Perform Inpainting
        # inpaintRadius = 5 (neighborhood around a pixel to be inpainted)
        inpainted = cv2.inpaint(img, dilated_mask, inpaintRadius=5, flags=flags)

        # 5. Boundary Blending: Apply local feathering to blend the inpainted area
        # into the original picture seamlessly.
        blended = self._apply_local_feathering(img, inpainted, dilated_mask)

        cv2.imwrite(output_path, blended)
        logger.info(f"Watermark removed successfully. Output saved to {output_path}")
        return output_path

    def _apply_local_feathering(
        self, original: np.ndarray, inpainted: np.ndarray, mask: np.ndarray
    ) -> np.ndarray:
        """
        Feathers boundaries between the original image and the inpainted region to remove hard edges.
        """
        # Create a soft feathering mask
        # Blur the mask to create gradient transitions from 0 to 1 at the edges
        mask_blur = cv2.GaussianBlur(mask.astype(np.float32), (9, 9), 0) / 255.0
        mask_blur = np.expand_dims(mask_blur, axis=2)  # Make it H, W, 1

        # Linear interpolation: final = original * (1 - mask) + inpainted * mask
        blended = (
            original.astype(np.float32) * (1.0 - mask_blur)
            + inpainted.astype(np.float32) * mask_blur
        )
        return blended.clip(0, 255).astype(np.uint8)
