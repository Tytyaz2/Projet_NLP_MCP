# Base python image
FROM python:3.11-slim
# Defining /app as default working directory in the container
WORKDIR /app
# Copy dependencies
COPY requirements.txt .
# Installing librairies
RUN pip install --no-cache-dir -r requirements.txt
# Copying rest of the code including mcp_server.py to /app
COPY . .
# Max root authorized by Docker specified when 'docker run'
ENV CONTAINER_ROOT=/data_mount
# Listening 8000 port (MCP Server)
EXPOSE 8000
# Launching server command when container running
CMD ["python", "mcp_server.py"]