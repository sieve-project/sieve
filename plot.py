import numpy as np
import matplotlib.pyplot as plt


BASELINE = "baseline"
AFTER_R1 = "after-sp"
AFTER_R2 = "after-cp"
FINAL = "final"

operator_name_map = {
    "cassandra-operator": "cassandra-\noperator",
    "zookeeper-operator": "zookeeper-\noperator",
    "rabbitmq-operator": "rabbitmq-\noperator",
    "mongodb-operator": "mongodb-\noperator",
    "cass-operator": "cass-\noperator",
    "casskop-operator": "casskop",
    "xtradb-operator": "xtradb-\noperator",
    "yugabyte-operator": "yugabyte-\noperator",
    "nifikop-operator": "nifikop",
}


spec_map = {}
f = open("test_plan_stats.tsv")
f.readline()
for line in f.readlines():
    tokens = line.strip().split("\t")
    operator = operator_name_map[tokens[0]]
    spec_map[operator] = {}
    spec_map[operator][BASELINE] = int(tokens[1])
    spec_map[operator][AFTER_R1] = int(tokens[2])
    spec_map[operator][AFTER_R2] = int(tokens[3])
    spec_map[operator][FINAL] = int(tokens[4])

operators = list(spec_map.keys())
operators.sort()
ind = np.arange(len(operators))

spec_list_map = {BASELINE: {}, AFTER_R1: {}, AFTER_R2: {}, FINAL: {}}


for prune in [BASELINE, AFTER_R1, AFTER_R2, FINAL]:
    spec_list_map[prune] = [spec_map[op][prune] for op in operators]

bar_width = 0.15
bar_space = bar_width + 0.02

shift_map = {
    BASELINE: -1.5 * bar_space,
    AFTER_R1: -0.5 * bar_space,
    AFTER_R2: 0.5 * bar_space,
    FINAL: 1.5 * bar_space,
}

color_map = {
    # BASELINE: "lightsalmon",
    BASELINE: "azure",
    AFTER_R1: "paleturquoise",
    # AFTER_R1: "darkorange",
    # AFTER_R2: "lightgreen",
    AFTER_R2: "darkturquoise",
    # FINAL: "lightskyblue",
    FINAL: "royalblue",
}
label_map = {
    BASELINE: "baseline",
    AFTER_R1: "prune by causality",
    AFTER_R2: "prune updates",
    FINAL: "deterministic timing",
}

rotation = 45
tick_font = 50
label_font = 53
legend_font = 35
str_font = 35
plt.rcParams["figure.figsize"] = (28, 12)
# plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["axes.linewidth"] = 5

string_float_ratio_map = {
    0: {BASELINE: 0.0, AFTER_R1: 0.5, AFTER_R2: 0.0, FINAL: 0.0},  # cass
    1: {BASELINE: 0.65, AFTER_R1: 0.6, AFTER_R2: 0.4, FINAL: 0.0},  # cassandra
    2: {BASELINE: 0.3, AFTER_R1: 0.0, AFTER_R2: 0.2, FINAL: 0.0},  # casskop
    3: {BASELINE: 0.0, AFTER_R1: 0.0, AFTER_R2: 0.4, FINAL: 0.0},  # mongodb
    4: {BASELINE: 0.6, AFTER_R1: 0.1, AFTER_R2: 0.0, FINAL: 0.0},  # nifi
    5: {BASELINE: 0.4, AFTER_R1: 0.15, AFTER_R2: 0.0, FINAL: 0.0},  # rabbitmq
    6: {BASELINE: 0.3, AFTER_R1: 0.0, AFTER_R2: 0.4, FINAL: 0.0},  # xtradb
    7: {BASELINE: 0.0, AFTER_R1: 0.05, AFTER_R2: 0.0, FINAL: 0.0},  # yugabyte
    8: {BASELINE: 0.0, AFTER_R1: 0.0, AFTER_R2: 0.0, FINAL: 0.0},  # zookeeper
}

for prune in [BASELINE, AFTER_R1, AFTER_R2, FINAL]:
    np_array_spec = np.array(spec_list_map[prune])
    align = "center"
    plt.bar(
        ind + shift_map[prune],
        np_array_spec,
        width=bar_width,
        label=label_map[prune],
        color=color_map[prune],
        edgecolor="black",
        align=align,
        linewidth=3,
    )
    for i in range(len(spec_list_map[prune])):
        ratio = 1.05
        if i in string_float_ratio_map:
            ratio += string_float_ratio_map[i][prune]
        plt.text(
            i + shift_map[prune] - 0.075,
            spec_list_map[prune][i] * ratio,
            str(spec_list_map[prune][i]),
            fontsize=str_font,
        )

plt.yscale("log")
plt.yticks(fontsize=tick_font - 5)
plt.xticks(ind, operators, fontsize=tick_font, rotation=rotation)
plt.ylabel("# Test Plans", fontsize=label_font - 5)
plt.gca().set_ylim(top=300000)
plt.gca().yaxis.grid(True)
plt.legend(fontsize=legend_font, loc="upper left")
plt.savefig("fig8.pdf", bbox_inches="tight")
