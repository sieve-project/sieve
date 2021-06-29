package main

import (
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestCancelEvent(t *testing.T) {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	crucialEvent := `{"spec": {"nodeName": "SONAR-NON-NIL"}, "status": {"conditions": [{"type":
	"PodScheduled", "status": "True", "lastProbeTime": null, "lastTransitionTime": "SONAR-NON-NIL"}]}}`
	currentEvent := `{"name":"mongodb-cluster-cfg-1","generateName":"mongodb-cluster-cfg-","namespace":"default","uid":"f42f5c0e-4ff7-41f9-b27e-adf154316e3d","resourceVersion":"1681","creationTimestamp":"2021-06-06T08:22:17Z","Spec":{"NodeName":"kind-worker","ImagePullSecrets":null,"Hostname":"mongodb-cluster-cfg-1","Subdomain":"mongodb-cluster-cfg","Affinity":{"NodeAffinity":null,"PodAffinity":null,"PodAntiAffinity":{"RequiredDuringSchedulingIgnoredDuringExecution":[{"LabelSelector":{"matchLabels":{"app.kubernetes.io/component":"cfg","app.kubernetes.io/instance":"mongodb-cluster","app.kubernetes.io/managed-by":"percona-server-mongodb-operator","app.kubernetes.io/name":"percona-server-mongodb","app.kubernetes.io/part-of":"percona-server-mongodb","app.kubernetes.io/replset":"cfg"}},"Namespaces":null,"TopologyKey":"kubernetes.io/hostname"}],"PreferredDuringSchedulingIgnoredDuringExecution":null}},"SchedulerName":"default-scheduler","Tolerations":[{"Key":"node.kubernetes.io/not-ready","Operator":"Exists","Value":"","Effect":"NoExecute","TolerationSeconds":300},{"Key":"node.kubernetes.io/unreachable","Operator":"Exists","Value":"","Effect":"NoExecute","TolerationSeconds":300}],"HostAliases":null,"PriorityClassName":"","Priority":0,"PreemptionPolicy":null,"DNSConfig":null,"ReadinessGates":null,"RuntimeClassName":null,"Overhead":null,"EnableServiceLinks":true,"TopologySpreadConstraints":null},"Status":{"Phase":"Pending","Conditions":[{"Type":"PodScheduled","Status":"True","LastProbeTime":null,"LastTransitionTime":"2021-06-06T08:22:20Z","Reason":"","Message":""}],"Message":"","Reason":"","NominatedNodeName":"","HostIP":"","PodIPs":null,"StartTime":null,"QOSClass":"Guaranteed","InitContainerStatuses":null,"ContainerStatuses":null,"EphemeralContainerStatuses":null}}`
	assert.False(t, cancelEvent(strToMap(crucialEvent), strToMap(currentEvent)), "Cancel event detect fail")
}
