FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot source
COPY bot.py .

# Run the bot (PORT env is set by Hugging Face Spaces automatically)
CMD ["python", "bot.py"]
