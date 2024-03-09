FROM python:3.11
RUN useradd -ms /bin /bash user
USER user
WORKDIR /home/user
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["python", "main.py"]
