import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

prompt = """Design a premium, editorial LinkedIn cover banner for an AI-first agency called SARVAYA.
Ultra-wide cinematic format. Minimal and typographic. Dark near-black background
with extremely subtle film grain. A single vivid lime-green accent color is the only
color besides white and grey — the lime should feel electric but sparingly used.

LEFT HALF of the canvas:
Giant wordmark reading exactly: SARVAYA
— uppercase, bold geometric sans-serif (Syne-style), extra-heavy weight, tight letter
spacing. Fill the letters with a smooth gradient from bright white at the top to soft
mid-grey at the bottom. Make the wordmark the clear hero of the composition, very
large but with generous breathing room.

Directly beneath the wordmark, a single small lowercase tagline in light grey:
we complete your business.

Below the tagline, a single horizontal row of five small capsule-shaped pill tags,
each with a thin lime-green outline, transparent fill, and lime-green uppercase text.
The pills read, from left to right, exactly:
AI AUTOMATION   |   AEO / GEO   |   WEB DEVELOPMENT   |   SAAS   |   PRODUCT
Space the pills evenly with small gaps. Text inside pills should be legible, not tiny.

RIGHT HALF of the canvas:
Negative space with a very soft, restrained composition — a subtle radial lime-green
glow blooming out of the right-center at low opacity, a faint thin vertical lime accent
line, and a few small lime particle dots floating. No icons, no logos, no illustrations,
no photographs, no people.

Overall mood: dark, confident, premium agency, editorial, cinematic. Very high contrast.
Absolutely DO NOT render any color codes, hex values, hashtags, pound signs, #
characters, URLs, phone numbers, email addresses, or watermarks anywhere in the image.
Only the text I specified above should appear — nothing else."""

import time
from google.genai.errors import ServerError

models_to_try = [
    ("gemini-3-pro-image-preview", "4K", "21:9"),
    ("gemini-2.5-flash-image-preview", "2K", "21:9"),
    ("gemini-2.5-flash-image", "2K", "21:9"),
]

response = None
for model, size, ratio in models_to_try:
    for attempt in range(3):
        try:
            print(f"trying {model} (attempt {attempt+1})")
            response = client.models.generate_content(
                model=model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE'],
                    image_config=types.ImageConfig(
                        aspect_ratio=ratio,
                        image_size=size,
                    ),
                ),
            )
            print(f"success with {model}")
            break
        except ServerError as e:
            wait = 20
            print(f"  failed: {e}. sleeping {wait}s")
            time.sleep(wait)
        except Exception as e:
            print(f"  model error: {e}")
            break
    if response is not None:
        break

if response is None:
    raise SystemExit("Gemini API still unavailable after retries")

from PIL import Image as PILImage
import io

out_raw = r"C:\Users\Claude\Desktop\New folder (2)\assets\images\linkedin-banner-raw.png"
out = r"C:\Users\Claude\Desktop\New folder (2)\assets\images\linkedin-banner.png"
for part in response.parts:
    if part.text:
        print(part.text)
    elif part.inline_data:
        data = part.inline_data.data
        pil = PILImage.open(io.BytesIO(data))
        pil.save(out_raw)
        print(f"Saved raw: {out_raw}  size={pil.size}  mode={pil.mode}")
        # LinkedIn banner target: 1584 x 396 (4:1). Center-crop then resize.
        w, h = pil.size
        target_ratio = 1584 / 396  # 4.0
        current_ratio = w / h
        if current_ratio > target_ratio:
            # too wide -> crop width
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            pil = pil.crop((left, 0, left + new_w, h))
        else:
            # too tall -> crop height
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            pil = pil.crop((0, top, w, top + new_h))
        pil = pil.resize((1584, 396), PILImage.LANCZOS)
        pil.save(out, format="PNG", optimize=True)
        print(f"Saved LinkedIn-sized: {out}  size={pil.size}")
