controllers_to_check = {
    "cass-operator": ["recreate", "scaledown-scaleup"],
    "cassandra-operator": ["recreate", "scaledown-scaleup"],
    "casskop-operator": ["recreate", "scaledown-to-zero", "reducepdb"],
    "elastic-operator": ["recreate", "scaledown-scaleup"],
    "mongodb-operator": [
        "recreate",
        "scaleup-scaledown",
        "disable-enable-shard",
        "disable-enable-arbiter",
        "run-cert-manager",
    ],
    "nifikop-operator": ["recreate", "scaledown-scaleup", "change-config"],
    "rabbitmq-operator": ["recreate", "scaleup-scaledown", "resize-pvc"],
    "xtradb-operator": [
        "recreate",
        "disable-enable-haproxy",
        "disable-enable-proxysql",
        "run-cert-manager",
        "scaleup-scaledown",
    ],
    "yugabyte-operator": [
        "recreate",
        "scaleup-scaledown-tserver",
        "disable-enable-tls",
        "disable-enable-tuiport",
    ],
    "zookeeper-operator": ["recreate", "scaledown-scaleup"],
}
