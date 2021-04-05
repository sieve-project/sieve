# Build the manager binary
FROM golang:1.15 as builder

WORKDIR /workspace

COPY . ./

# Build
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GO111MODULE=on go build -a -o manager main.go


FROM alpine:latest
WORKDIR /
COPY --from=builder /workspace/manager .

RUN apk update
RUN apk upgrade
RUN apk add bash

CMD ["sleep", "infinity"]
