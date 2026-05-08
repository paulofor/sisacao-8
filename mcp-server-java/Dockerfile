FROM maven:3.9.8-eclipse-temurin-21 AS build
WORKDIR /app
COPY mcp-server-java/pom.xml .
COPY mcp-server-java/src ./src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:21-jre
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg apt-transport-https && \
    curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
      | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
      > /etc/apt/sources.list.d/google-cloud-sdk.list && \
    apt-get update && apt-get install -y --no-install-recommends google-cloud-cli && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /opt/app
COPY --from=build /app/target/mcp-server-java-0.0.1-SNAPSHOT.jar /opt/app/mcp-server-java.jar
EXPOSE 80
ENV SERVER_PORT=80
ENTRYPOINT ["java","-jar","/opt/app/mcp-server-java.jar"]
