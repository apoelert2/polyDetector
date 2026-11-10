FROM docker.io/library/maven:3.9-eclipse-temurin-25 AS build
WORKDIR /app
COPY pom.xml checkstyle.xml ./
RUN mvn dependency:go-offline -B
COPY src ./src
# Tests need a container runtime (Testcontainers); they run in lint.sh, not in the image build.
RUN mvn package -DskipTests -B

FROM docker.io/library/eclipse-temurin:25-jre-alpine
RUN apk add --no-cache procps && adduser -D -H app
WORKDIR /app
COPY --from=build /app/target/ws-subscriber-1.0.0.jar app.jar
USER app
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD pgrep -f "app.jar" || exit 1
ENTRYPOINT ["java", "-jar", "app.jar"]
