FROM ubuntu:20.04

# Set the working directory in the container
WORKDIR /usr/src/app

COPY . .

RUN apt-get update && apt-get install -y python3 python3-pip

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

# Set the FLASK_ENV environment variable
ENV FLASK_ENV=development

CMD ["python3", "main.py"]
