FROM python:alpine3.17
RUN apk --no-cache add git rust cargo
RUN python3 -m pip install -U setuptools wheel pip
COPY . .
RUN python3 -m pip install -r requirements.txt
CMD [ "python3", "-u", "main.py" ]