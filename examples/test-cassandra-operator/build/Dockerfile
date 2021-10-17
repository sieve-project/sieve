ARG GOLANG_BASE_IMAGE=golang:1.13.8

FROM ${GOLANG_BASE_IMAGE} AS builder

ARG version

# Create a user so that operator can run as non-root
RUN useradd -u 999 cassandra-operator

WORKDIR /code

# Copy go.mod and go.sum separately to ensure we re-download dependencies only
# when these files change
COPY go.mod go.sum ./

# Fetch Go modules in a separate layer for better caching
# RUN go mod download

COPY . ./

# Build binary
RUN cd cmd/manager \
    && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags "-w -X main.version=${version}" \
    -o /tmp/cassandra-operator

# Build final image
FROM alpine:3.11.2

COPY --from=builder /tmp/cassandra-operator .
COPY --from=builder /etc/passwd /etc/passwd
USER 999
RUN mkdir -p /tmp
CMD ["./cassandra-operator"]
