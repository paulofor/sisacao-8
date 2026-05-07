FROM maven:3.9.8-eclipse-temurin-21 AS build
WORKDIR /app
COPY mcp-server-java/pom.xml .
COPY mcp-server-java/src ./src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /opt/app
COPY --from=build /app/target/mcp-server-java-0.0.1-SNAPSHOT.jar /opt/app/mcp-server-java.jar
EXPOSE 80
ENV SERVER_PORT=80
ENTRYPOINT ["java","-jar","/opt/app/mcp-server-java.jar"]
