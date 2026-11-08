# Telegram Sticker Booth — CLI image (bring your own Gemini / Telegram keys at runtime).
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sticker_booth/ sticker_booth/
COPY examples/ examples/
COPY my_prompts.example.json .

# Credentials, photos and generated output stay outside the image (mount or env at run time).
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m"]
CMD ["sticker_booth.booth", "--help"]
