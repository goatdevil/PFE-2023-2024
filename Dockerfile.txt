FROM python:3.11
RUN useradd -ms /bin /bash user
USER user
WORKDIR /home/user
COPY requirement.txt
RUN pip install -r requirements.txt && rm requirements.txt
COPY src .
ENTRYPOINT ["python", "main.py"]
