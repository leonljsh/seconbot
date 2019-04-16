FROM python:3.7-alpine
ENV PYTHONUNBUFFERED 1
RUN mkdir /bot
ADD requirements.txt /bot/
WORKDIR /bot
RUN pip install -r requirements.txt
