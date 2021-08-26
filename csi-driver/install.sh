#!/bin/sh

SNAPSHOTTER_VERSION=v2.0.1

# Install VolumeSnapshot CRD
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/${SNAPSHOTTER_VERSION}/config/crd/snapshot.storage.k8s.io_volumesnapshotclasses.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/${SNAPSHOTTER_VERSION}/config/crd/snapshot.storage.k8s.io_volumesnapshotcontents.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/${SNAPSHOTTER_VERSION}/config/crd/snapshot.storage.k8s.io_volumesnapshots.yaml

# Create snapshot controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/${SNAPSHOTTER_VERSION}/deploy/kubernetes/snapshot-controller/rbac-snapshot-controller.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/${SNAPSHOTTER_VERSION}/deploy/kubernetes/snapshot-controller/setup-snapshot-controller.yaml

# Check for install
kubectl get volumesnapshotclasses.snapshot.storage.k8s.io
kubectl get volumesnapshots.snapshot.storage.k8s.io
kubectl get volumesnapshotcontents.snapshot.storage.k8s.io

# Deploy
./deploy/kubernetes-latest/deploy.sh

# Check for pod
kubectl get pods

sleep 60s

kubectl get pods

kubectl apply -f csi-storageclass.yaml

sleep 10s

# Change default storage class
kubectl patch storageclass standard -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'
kubectl patch storageclass csi-hostpath-sc -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

kubectl get storageclass
