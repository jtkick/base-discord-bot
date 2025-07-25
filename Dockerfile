FROM python:3.8-slim-buster

COPY . /app
WORKDIR /app

RUN pip3 install -r requirements.txt
RUN python3 -m pip install -U discord.py[voice]

RUN apt -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg

CMD python3 __main__.py
