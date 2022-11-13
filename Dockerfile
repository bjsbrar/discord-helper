FROM python:3.9-slim

# Download latest listing of available packages:
RUN apt-get -y update
# Upgrade already installed packages:
#RUN apt-get -y upgrade
# Install ffmpeg:
RUN apt-get -y install ffmpeg

# Install & use pipenv
COPY Pipfile Pipfile.lock ./
RUN python -m pip install --upgrade pip
RUN pip install pipenv && pipenv install --dev --system --deploy

# Set Environment Variables
ENV BOT_TOKEN=$BOT_TOKEN
ENV BOT_ID=$BOT_ID

WORKDIR /app
COPY . /app


# Creates a non-root user and adds permission to access the /app folder
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

CMD ["python", "MessageScheduler.py"]
