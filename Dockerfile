FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN base64 --help
RUN jq --help
RUN echo "$GCP_JSON_BASE64" | base64 --decode | jq > gcp-credentials.json
ENTRYPOINT ["python", "main.py"]
