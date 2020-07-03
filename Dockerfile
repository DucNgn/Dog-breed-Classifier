FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5000
ENV GOOGLE_APPLICATION_CREDENTIALS="/usr/src/app/GCloud_credentials.json"

CMD ["python", "./app.py"]

EXPOSE $PORT


