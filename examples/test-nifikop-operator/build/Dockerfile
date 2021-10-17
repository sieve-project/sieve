# Build the manager binary
FROM golang:1.15 as builder

WORKDIR /workspace
# Copy the go source
COPY . ./

RUN go mod tidy

# Build
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GO111MODULE=on go build -a -o manager main.go

# Use distroless as minimal base image to package the manager binary
# Refer to https://github.com/GoogleContainerTools/distroless for more details
FROM gcr.io/distroless/static:nonroot
LABEL org.opencontainers.image.documentation="https://github.com/Orange-OpenSource/nifikop/blob/master/README.md"
LABEL org.opencontainers.image.authors="Alexandre Guitton <aguitton.ext@orange.com>"
LABEL org.opencontainers.image.source="https://github.com/Orange-OpenSource/nifikop"
LABEL org.opencontainers.image.vendor="Orange France - Digital Factory"
LABEL org.opencontainers.image.version="0.1"
LABEL org.opencontainers.image.description="Operateur des Gestion de Clusters Nifi"
LABEL org.opencontainers.image.url="https://github.com/Orange-OpenSource/nifikop"
LABEL org.opencontainers.image.title="Operateur NiFi"

LABEL org.label-schema.usage="https://github.com/Orange-OpenSource/nifikop/blob/master/README.md"
LABEL org.label-schema.docker.cmd="/usr/local/bin/nifikop"
LABEL org.label-schema.docker.cmd.devel="N/A"
LABEL org.label-schema.docker.cmd.test="N/A"
LABEL org.label-schema.docker.cmd.help="N/A"
LABEL org.label-schema.docker.cmd.debug="N/A"
LABEL org.label-schema.docker.params="LOG_LEVEL=define loglevel,RESYNC_PERIOD=period in second to execute resynchronisation,WATCH_NAMESPACE=namespace to watch for nificlusters,OPERATOR_NAME=name of the operator instance pod"

WORKDIR /
COPY --from=builder /workspace/manager .

#USER 65532:65532
USER 1001:1001

ENTRYPOINT ["/manager"]
