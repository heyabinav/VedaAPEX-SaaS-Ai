import json

# ─── Generation Credit Costs ────────────────────────────
GENERATION_COSTS = {
    "IMAGE": 5,
    "VIDEO": 20,
    "PPT": 10,
    "MODEL_3D": 15,
    "BG_REMOVAL": 2,
    "TEXT": 1,
    "TTS": 3,
}

# ─── Subscription Plans Config ──────────────────────────
SUBSCRIPTION_PLANS = {
    "FREE": {
        "name": "Free",
        "slug": "free",
        "price": 0,
        "token_allocation": 100,
        "daily_credits": 200,
        "features": json.dumps(
            [
                "100 credits on signup",
                "200 daily free credits",
                "Basic image generation",
                "Standard quality",
                "Community support",
            ]
        ),
    },
    "PRO": {
        "name": "Pro Plan",
        "slug": "pro",
        "price": 200,
        "token_allocation": 999999,  # Unlimited indicator for credits
        "daily_credits": 999999,
        "badge": "Most Popular",
        "features": json.dumps(
            [
                "Unlimited Text to Text AI",
                "Unlimited Image to Image AI",
                "Unlimited Text to Video",
                "Unlimited Image to Video",
                "AI Logo Generator",
                "AI PPT Generator",
                "AI Excel File Generator",
                "AI Word File Generator",
                "AI Background Remover",
                "AI 3D Model Generator",
                "Fast AI Processing",
                "Cloud Storage",
                "API Access",
                "Commercial Use",
                "Modern Dashboard",
                "History Saving",
                "Download Support",
            ]
        ),
    },
    "MAX": {
        "name": "Max Plan",
        "slug": "max",
        "price": 500,
        "token_allocation": 999999,
        "daily_credits": 999999,
        "badge": "Advanced AI Suite",
        "features": json.dumps(
            [
                "Everything in Pro Plan",
                "Advanced Text to Text Models",
                "Advanced Text to Image",
                "Advanced Image to Video",
                "Text to Animation",
                "Image to Animation",
                "Video to Animation",
                "Advanced Logo Generator",
                "AI PDF Generator",
                "Advanced PPT Generator",
                "Advanced Excel/Word Generator",
                "AI 3D Model Create & Edit",
                "AI Code Generator",
                "AI Creativity Ideas Generator",
                "AI Design Generator",
                "Apex Ads Generator",
                "Premium AI Models",
                "Priority Rendering",
                "Faster Queue",
                "High Resolution Export",
                "Developer APIs",
                "Custom Templates",
            ]
        ),
    },
    "ULTRA": {
        "name": "Ultra Plan",
        "slug": "ultra",
        "price": 1000,
        "token_allocation": 999999,
        "daily_credits": 999999,
        "badge": "Ultimate AI Power",
        "features": json.dumps(
            [
                "Everything in Max Plan",
                "3 More Advanced Apex Ads Generators",
                "AI Home Map Generator",
                "AI Home Design Generator",
                "AI Interior Design Generator",
                "Upload Home Image for AI Design",
                "AI Color Suggestions for Home",
                "Ultra Fast Rendering",
                "Premium 4K Exports",
                "Unlimited Premium AI Models",
                "Advanced Animation Studio",
                "Advanced 3D AI Editing",
                "AI Architecture Tools",
                "AI Smart Layout Generator",
                "Enterprise APIs",
                "Team Workspace",
                "Cloud Sync",
                "AI Project Collaboration",
                "Dedicated AI Resources",
                "Premium Support",
            ]
        ),
    },
}

# ─── Daily Reward Tiers ──────────────────────────────────
DAILY_REWARD_TIERS = [
    {"min_streak": 1, "max_streak": 7, "credits": 10},
    {"min_streak": 8, "max_streak": 14, "credits": 15},
    {"min_streak": 15, "max_streak": 21, "credits": 20},
    {"min_streak": 22, "max_streak": 30, "credits": 30},
    {"min_streak": 31, "max_streak": 999999, "credits": 50},
]

SIGNUP_BONUS_CREDITS = 100
REFERRAL_BONUS_CREDITS = 50
DAILY_FREE_CREDITS = 200


def get_daily_reward_credits(streak: int) -> int:
    for tier in DAILY_REWARD_TIERS:
        if tier["min_streak"] <= streak <= tier["max_streak"]:
            return tier["credits"]
    return 10
