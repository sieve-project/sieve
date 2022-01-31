controllers_to_check = {
    "cassandra-operator": ["recreate", "scaledown-scaleup"],
    "zookeeper-operator": ["recreate", "scaledown-scaleup"],
    "rabbitmq-operator": ["recreate", "scaleup-scaledown", "resize-pvc"],
    "mongodb-operator": [
        "recreate",
        "scaleup-scaledown",
        "disable-enable-shard",
        "disable-enable-arbiter",
        "run-cert-manager",
    ],
    "cass-operator": ["recreate", "scaledown-scaleup"],
    "casskop-operator": ["recreate", "scaledown-to-zero", "reducepdb"],
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
    "nifikop-operator": ["recreate", "scaledown-scaleup", "change-config"],
}
