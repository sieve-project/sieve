# NiFiKop - Nifi Kubernetes operator Helm chart

This Helm chart install NiFiKop the Orange's Nifi Kubernetes operator to create/configure/manage NiFi 
clusters in a Kubernetes Namespace.

It will use Custom Ressources Definition CRDs:
 
- `nificlusters.nifi.orange.com`, 
- `nifiusers.nifi.orange.com`, 
- `nifiusergroups.nifi.orange.com`, 
- `nifiregistryclients.nifi.orange.com`, 
- `nifiparametercontexts.nifi.orange.com`, 
- `nifidataflows.nifi.orange.com`, 

which implements kubernetes custom ressource definition.

## Introduction

### Configuration

The following tables lists the configurable parameters of the NiFi Operator Helm chart and their default values.

| Parameter                        | Description                                      | Default                                   |
|----------------------------------|--------------------------------------------------|-------------------------------------------|
| `image.repository`               | Image                                            | `orangeopensource/nifikop`                |
| `image.tag`                      | Image tag                                        | `v0.6.3-release`                          |
| `image.pullPolicy`               | Image pull policy                                | `Always`                                  |
| `image.imagePullSecrets.enabled` | Enable tue use of secret for docker image        | `false`                                   |
| `image.imagePullSecrets.name`    | Name of the secret to connect to docker registry | -                                         |
| `certManager.enabled`            | Enable cert-manager integration                  | `true`                                    |
| `rbacEnable`                     | If true, create & use RBAC resources             | `true`                                    |
| `resources`                      | Pod resource requests & limits                   | `{}`                                      |
| `metricService`                  | deploy service for metrics                       | `false`                                   |
| `debug.enabled`                  | activate DEBUG log level                         | `false`                                   |
| `certManager.clusterScoped`      | If true setup cluster scoped resources           | `false`                            |
| `namespaces`                     | List of namespaces where Operator watches for custom resources. Make sure the operator ServiceAccount is granted `get` permissions on this `Node` resource when using limited RBACs.| `""` i.e. all namespaces |
| `nodeSelector`                   | Node selector configuration for operator pod     | `{}`                                      |
| `affinity`                       | Node affinity configuration for operator pod     | `{}`                                      |
| `tolerations`                    | Toleration configuration for operator pod        | `{}`                                      |
| `serviceAccount.create`          | Whether the SA creation is delegated to the chart or not       | `true`                                      |
| `serviceAccount.name`            | Name of the SA used for NiFiKop deployment       | release name                                     |


Specify each parameter using the `--set key=value[,key=value]` argument to `helm install`. For example,

Alternatively, a YAML file that specifies the values for the above parameters can be provided while installing the chart. For example,

```console
$ helm install nifikop \
    orange-incubator/nifikop \
    -f values.yaml
```

### Installing the Chart

In the case where you don't want to deploy the crds using helm (`--skip-crds`) or you are using a version of kubernetes that is under 1.16, you need to deploy manually the crds beforehand:

```console
kubectl apply -f https://raw.githubusercontent.com/Orange-OpenSource/nifikop/master/deploy/crds/v1beta1/nifi.orange.com_nificlusters_crd.yaml
kubectl apply -f https://raw.githubusercontent.com/Orange-OpenSource/nifikop/master/deploy/crds/v1beta1/nifi.orange.com_nifiusers_crd.yaml
kubectl apply -f https://raw.githubusercontent.com/Orange-OpenSource/nifikop/master/deploy/crds/v1beta1/nifi.orange.com_nifiusergroups_crd.yaml
kubectl apply -f https://raw.githubusercontent.com/Orange-OpenSource/nifikop/master/deploy/crds/v1beta1/nifi.orange.com_nifidataflows_crd.yaml
kubectl apply -f https://raw.githubusercontent.com/Orange-OpenSource/nifikop/master/deploy/crds/v1beta1/nifi.orange.com_nifiparametercontexts_crd.yaml
kubectl apply -f https://raw.githubusercontent.com/Orange-OpenSource/nifikop/master/deploy/crds/v1beta1/nifi.orange.com_nifiregistryclients_crd.yaml
```

You can make a dry run of the chart before deploying :

```console 
helm install nifikop orange-incubator/nifikop \
    --dry-run \
    --debug.enabled \
    --set debug.enabled=true \
    --set namespaces={"nifikop"}
```

To install the chart with the release name `nifikop` :

```console
$ helm install nifikop orange-incubator/nifikop --set namespaces={"nifikop"}
```

We can surcharge default parameters using `--set` flag :

```console
$ helm install nifikop orange-incubator/nifikop --replace --set image.tag=asyncronous 
```

> the `--replace` flag allow you to reuses a charts release name


### Listing deployed charts

```
helm list
```

### Get Status for the helm deployment :

```
helm status nifikop
```

## Uninstaling the Charts

If you want to delete the operator from your Kubernetes cluster, the operator deployment 
should be deleted.

```
$ helm del nifikop
```

The command removes all the Kubernetes components associated with the chart and deletes the helm release.

> The CRD created by the chart are not removed by default and should be manually cleaned up (if required)

Manually delete the CRD:

```
kubectl delete crd nificlusters.nifi.orange.com
kubectl delete crd nifiusers.nifi.orange.com
kubectl delete crd nifiusergroups.nifi.orange.com
kubectl delete crd nifiregistryclients.nifi.orange.com
kubectl delete crd nifiparametercontexts.nifi.orange.com
kubectl delete crd nifidataflows.nifi.orange.com
```

> **!!!!!!!!WARNING!!!!!!!!**
>
> If you delete the CRD then **!!!!!!WAAAARRRRNNIIIIINNG!!!!!!**
>
> It will delete **ALL** Clusters that has been created using this CRD!!!
>
> Please never delete a CRD without very very good care


Helm always keeps records of what releases happened. Need to see the deleted releases? `helm ls --deleted`
shows those, and `helm ls --all` shows all of the releases (deleted and currently deployed, as well as releases that
failed):

Because Helm keeps records of deleted releases, a release name cannot be re-used. (If you really need to re-use a
release name, you can use the `--replace` flag, but it will simply re-use the existing release and replace its
resources.)

Note that because releases are preserved in this way, you can rollback a deleted resource, and have it re-activate.



To purge a release

```console
helm del nifikop
```

## Troubleshooting

### Install of the CRD

By default, the chart will install the CRDs, but this installation is global for the whole
cluster, and you may want to not modify the already deployed CRDs.

In this case there is a parameter to say to not install the CRDs :

```
$ helm install --name nifikop ./helm/nifikop --set namespaces={"nifikop"} --skip-crds
```