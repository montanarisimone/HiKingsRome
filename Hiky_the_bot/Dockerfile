FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# -u: unbuffered stdout/stderr so logs appear in real time in docker logs
CMD ["python", "-u", "HikyTheBot.py"]
