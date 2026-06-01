FROM python:3.12-slim
RUN apt-get update && apt-get install -y git
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/dev.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]