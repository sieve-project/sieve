# ARG BASE_OS=datastax/doesnotexist

# "builder" compiles and tests the code
# This stage name is important to the Cloud Platform CI/CD infrastructure, and should be preserved
FROM --platform=${BUILDPLATFORM} golang:1.14-stretch as builder

# Disable cgo - this makes static binaries that will work on an Alpine image
ENV CGO_ENABLED=0
# ENV GOPROXY=https://proxy.golang.org,https://gocenter.io,direct

# Target os and arch
ARG TARGETARCH
ENV GOOS=linux
ENV GOARCH=${TARGETARCH}
ENV GOPATH=/go


WORKDIR /cass-operator

COPY go.mod go.sum ./

# Download go deps (including mage)

# COPY instrumented controller-runtime and client-go
COPY . ./

# Still need to go mod download for mage
RUN go mod download

# At this point, we have the top level go.mod, the ./mage level go.mod,
# and the ./operator level go.mod without copying any of the source code yet.
# This means that the dependencies should be nicely without having
# to rerun every time we modify our lib code

# Install mage
# The new go module system will put the version number in the path, so we
# need to wildcard here to work with whatever version we are pinned to
RUN cd $GOPATH/pkg/mod/github.com/magefile/mage* && go run bootstrap.go

# Copy in source code
COPY magefile.go ./
COPY mage ./mage
COPY operator ./operator

ARG VERSION_STAMP=DEV

# Build any code not touched by tests (the generated client)
RUN MO_VERSION=${VERSION_STAMP} mage operator:buildGo

# Second stage
# Produce a smaller image than the one used to build the code
FROM alpine:3.11.2 as cass-operator
ENV GOPATH=.

RUN mkdir -p /var/lib/cass-operator/
RUN touch /var/lib/cass-operator/base_os
# WORKDIR /go

# All we need from the builder image is operator executable
ARG TARGETARCH
COPY --from=builder /cass-operator/build/bin/cass-operator-linux-${TARGETARCH} /bin/operator

# RUN apk update \
#         && apk upgrade \
#         && apk add bash

# Use alpine:3.11.2 solves infinity invalid issue
# CMD ["sleep", "infinity"]

CMD [ "/bin/operator" ]
