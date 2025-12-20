"""SinkIn AI API service for inference and upscaling."""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import requests

from config import get_settings

logger = logging.getLogger(__name__)


def _pretty(data: Dict[str, Any]) -> str:
    """Nicely format dictionaries for console logs."""
    return json.dumps(data, indent=2, sort_keys=True)


class SinkInService:
    """Service for interacting with SinkIn AI API."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.sinkin_base_url

    def _get_api_key(self) -> str:
        """Get API key from settings."""
        api_key = self.settings.sinkin_api_key
        if not api_key:
            raise ValueError("SINKIN_API_KEY not configured. Please add it to .env file.")
        return api_key

    def inference(
        self,
        model_id: str,
        prompt: str,
        negative_prompt: Optional[str] = None,
        use_default_neg: bool = True,
        width: int = 512,
        height: int = 768,
        steps: int = 30,
        scale: float = 7.5,
        num_images: int = 4,
        seed: int = -1,
        scheduler: str = "DPMSolverMultistep",
        lora: Optional[str] = None,
        lora_scale: float = 0.75,
        init_image_path: Optional[str] = None,
        image_strength: float = 0.75,
        controlnet: Optional[str] = None,
        log_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Call SinkIn /inference API.
        
        Returns:
            Tuple of (payload_dict, response_dict)
        """
        api_key = self._get_api_key()
        
        # Build request payload
        payload = {
            "access_token": api_key,
            "model_id": model_id,
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "scale": scale,
            "num_images": num_images,
            "seed": seed,
            "scheduler": scheduler,
            "use_default_neg": "true" if use_default_neg else "false",
        }
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        if lora:
            payload["lora"] = lora
            payload["lora_scale"] = lora_scale

        # Prepare files for img2img
        files = None
        if init_image_path:
            payload["image_strength"] = image_strength
            if controlnet:
                payload["controlnet"] = controlnet
            
            # Open image file
            image_path = Path(init_image_path)
            if image_path.exists():
                files = {"init_image_file": open(image_path, "rb")}

        # Create payload copy without API key for logging
        payload_for_log = {k: v for k, v in payload.items() if k != "access_token"}
        
        context = log_context or {}
        logger.info(
            "🛠️  Generating images | batch=%s job=%s model=%s scheduler=%s seed=%s num_images=%s",
            context.get("batch_number"),
            context.get("job_id"),
            model_id,
            scheduler,
            seed,
            num_images,
        )
        logger.debug("📦 Payload\n%s", _pretty(payload_for_log))

        try:
            response = requests.post(
                f"{self.base_url}/inference",
                data=payload,
                files=files,
                timeout=120,  # 2 minute timeout for generation
            )
            response.raise_for_status()
            response_data = response.json()
            logger.info(
                "✨ SinkIn inference succeeded | batch=%s job=%s inf_id=%s credit=%s images=%s",
                context.get("batch_number"),
                context.get("job_id"),
                response_data.get("inf_id"),
                response_data.get("credit_cost"),
                len(response_data.get("images", [])),
            )
        except requests.RequestException as e:
            response_data = {"error_code": 1, "message": str(e)}
            logger.error(
                "💥 SinkIn inference failed | batch=%s job=%s model=%s error=%s\nPayload:\n%s",
                context.get("batch_number"),
                context.get("job_id"),
                model_id,
                str(e),
                _pretty(payload_for_log),
            )
        finally:
            # Close file if opened
            if files:
                files["init_image_file"].close()

        return payload_for_log, response_data

    def upscale(
        self,
        inf_id: str,
        image_url: str,
        upscale_type: str = "esrgan",
        scale: float = 2.0,
        strength: float = 0.6,
    ) -> Dict[str, Any]:
        """
        Call SinkIn /upscale API.
        
        Args:
            inf_id: The inference ID from the original generation
            image_url: URL of the image to upscale
            upscale_type: 'esrgan' or 'hires_fix'
            scale: Scale factor 2-4 (ESRGAN only)
            strength: Strength 0-1 (Hires Fix only)
            
        Returns:
            Response dict with 'output' (upscaled image URL) on success
        """
        api_key = self._get_api_key()
        
        payload = {
            "access_token": api_key,
            "inf_id": inf_id,
            "url": image_url,
            "type": upscale_type,
        }
        
        # Add type-specific parameters
        if upscale_type == "esrgan":
            payload["scale"] = scale
        elif upscale_type == "hires_fix":
            payload["strength"] = strength
        
        try:
            response = requests.post(
                f"{self.base_url}/upscale",
                data=payload,
                timeout=120,  # Upscaling can take time
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error_code": 1, "message": str(e)}

    def get_models(self) -> Dict[str, Any]:
        """Get available models from SinkIn API."""
        api_key = self._get_api_key()
        
        try:
            response = requests.post(
                f"{self.base_url}/models",
                data={"access_token": api_key},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error_code": 1, "message": str(e)}


# Singleton instance
sinkin_service = SinkInService()
