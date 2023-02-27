FROM --platform=$BUILDPLATFORM golang:1.19.5 AS deps

ARG TARGETOS TARGETARCH KCTRL_VER=development
WORKDIR /workspace

# dependencies
COPY ./hack/dependencies.* ./hack/
COPY go.* ./
COPY vendor vendor
RUN mkdir out
RUN go run ./hack/dependencies.go install -d out --arch ${TARGETARCH} --os ${TARGETOS}

# kapp-controller
COPY . .
# helpful ldflags reference: https://www.digitalocean.com/community/tutorials/using-ldflags-to-set-version-information-for-go-applications
RUN --mount=type=cache,target=/root/.cache/go-build \
  CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} \
  go build -mod=vendor -ldflags="-X 'main.Version=$KCTRL_VER'" -trimpath -o out/kapp-controller ./cmd/controller

# --- run image ---
FROM photon:4.0

# Install openssh for git
RUN tdnf install -y git openssh-clients

# Create the kapp-controller user in the root group, the home directory will be mounted as a volume
RUN echo "kapp-controller:x:1000:0:/home/kapp-controller:/usr/sbin/nologin" > /etc/passwd
# Give the root group write access to the openssh's root bundle directory
# so we can rename the certs file with our dynamic config, and append custom roots at runtime
RUN chmod g+w /etc/pki/tls/certs
# Copy the ca-bundle so we have an original
RUN cp /etc/pki/tls/certs/ca-bundle.crt /etc/pki/tls/certs/ca-bundle.crt.orig

COPY --from=deps /workspace/out/* ./

# Run as kapp-controller by default, will be overridden to a random uid on OpenShift
USER 1000
ENV PATH="/:${PATH}"
ENTRYPOINT ["/kapp-controller"]
