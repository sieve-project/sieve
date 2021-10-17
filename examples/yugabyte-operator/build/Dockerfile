ARG GOLANG_BASE_IMAGE=golang:1.13.9

FROM ${GOLANG_BASE_IMAGE} AS builder

WORKDIR /src

# Copy go.mod and go.sum separately to ensure we re-download dependencies only
# when these files change
COPY go.mod go.sum ./

# Fetch Go modules in a separate layer for better caching
# RUN go mod download

COPY . ./

RUN cd cmd/manager \
    && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags "-w" \
    -o /tmp/yugabyte-operator

FROM registry.access.redhat.com/ubi7/ubi-minimal:latest

ENV OPERATOR=/usr/local/bin/yugabyte-operator \
    USER_UID=1001 \
    USER_NAME=yugabyte-operator

COPY --from=builder /tmp/yugabyte-operator /usr/local/bin/yugabyte-operator

COPY build/bin /usr/local/bin
RUN  /usr/local/bin/user_setup

ENTRYPOINT ["/usr/local/bin/entrypoint"]

USER ${USER_UID}
