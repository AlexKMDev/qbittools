FROM python:3-alpine

RUN apk add --no-cache git ca-certificates
WORKDIR /app
COPY . .
RUN pip3 install -r requirements.txt

ENTRYPOINT ["./qbittools.py"]
