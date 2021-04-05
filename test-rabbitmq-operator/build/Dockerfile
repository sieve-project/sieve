# Build the manager binary
FROM golang:1.16 as builder

WORKDIR /workspace

# Copy the go source
COPY . ./

# Build
RUN go mod download k8s.io/apimachinery
RUN go mod download k8s.io/klog
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GO111MODULE=on go build -a -tags timetzdata -o manager main.go

# ---------------------------------------
FROM alpine:latest as etc-builder

ARG GIT_COMMIT
LABEL GitCommit=$GIT_COMMIT

WORKDIR /
COPY --from=builder /workspace/manager .
RUN apk update
RUN apk upgrade
RUN apk add bash

CMD ["sleep", "infinity"]
