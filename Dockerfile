FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV MDP_BDD="$MDP_BDD"
ENV OPENAI_API_KEY="$OPENAI_API_KEY"
ENV TELEGRAM_TOKEN="$TELEGRAM_TOKEN"
RUN echo "$GCP_JSON_BASE64" | base64 --decode > our-ratio-415208-75a140e48770.json
EXPOSE 8000
CMD ["python", "main.py"]
