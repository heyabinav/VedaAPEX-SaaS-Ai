# ─── Ultra Plan Daily Free API Limits ────────────────────
ULTRA_DAILY_LIMITS = {
    "text_to_text": 500,
    "text_to_image": 100,
    "image_to_image": 100,
    "text_to_video": 20,
    "image_to_video": 20,
    "video_enhancement": 25,
    "image_enhancement": 200,
    "watermark_removal": 100,
    "ai_logo": 50,
    "ppt_generator": 30,
    "pdf_generator": 50,
    "excel_word": 50,
    "ai_code": 200,
    "ai_3d_model": 15,
    "ai_animation": 25,
    "apex_ads": 100,
    "home_design": 25,
    "interior_design": 25,
}

# ─── Mapping tool types to limit keys ────────────────────
TOOL_TYPE_TO_LIMIT_KEY = {
    "text": "text_to_text",
    "image": "text_to_image",  # default to text2img for generic image type
    "video": "text_to_video",
    "bg_removal": "watermark_removal",  # reuse for now or add new
    "image_enhance": "image_enhancement",
    "ppt": "ppt_generator",
    "word": "excel_word",
    "excel": "excel_word",
    "pdf": "pdf_generator",
    "animation": "ai_animation",
    "code": "ai_code",
    "design": "ai_logo",  # design tool mapped to logo limit or generic
    "ads": "apex_ads",
    "home_design": "home_design",
    "interior_design": "interior_design",
    "home_map": "home_design",  # reuse home_design limit for maps
    "3d": "ai_3d_model",
    "tts": "text_to_text",  # tts uses text limit or 100/day etc.
}
