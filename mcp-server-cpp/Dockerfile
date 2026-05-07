FROM ubuntu:24.04 AS build

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential \
      cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY mcp-server-cpp/ ./
RUN cmake -S . -B build \
    && cmake --build build --config Release

FROM ubuntu:24.04
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /app/build/mcp-server-cpp /usr/local/bin/mcp-server-cpp

ENV MCP_HOST=0.0.0.0 \
    MCP_PORT=80 \
    GCP_PROJECT=ingestaokraken \
    GCP_REGION=us-east1

EXPOSE 80
ENTRYPOINT ["/usr/local/bin/mcp-server-cpp"]
