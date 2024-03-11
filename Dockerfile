FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN echo "$GCP_JSON_BASE64" | base64 --decode > our-ratio-415208-75a140e48770.json
ENTRYPOINT ["python", "main.py"]
