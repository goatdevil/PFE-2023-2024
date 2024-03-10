FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN echo "$GCP_JSON_BASE64" | base64 --decode | jq > our-ratio-415208-65186935a597.json
ENTRYPOINT ["python", "main.py"]
