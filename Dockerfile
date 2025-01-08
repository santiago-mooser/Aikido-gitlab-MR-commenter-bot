FROM 3.14.0a3-alpine3.21

RUN apk update && \
    apk add --no-cache libcurl git gpg gpg-agent

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY lib/ .
COPY requirements.txt .
COPY entrypoint.sh .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT [ "./entrypoint.sh" ]
