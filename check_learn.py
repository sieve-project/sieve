import glob
import os

gen_configs = glob.glob(
    os.path.join(
        "log/*-operator/*/learn/learn-once/learn.yaml/*/*.yaml",
    )
)

reprod_configs = glob.glob("reprod/*.yaml")

for reprod_config in reprod_configs:
    found = False
    for gen_config in gen_configs:
        if open(reprod_config).read() == open(gen_config).read():
            print(reprod_config + " <= " + gen_config)
            found = True
    if not found:
        print("\033[91m" + reprod_config + " not found\033[0m")
