# Generate evaluation table from test json
# Dependencies: pip3 install pandas numpy xlsxwriter
# Usage: python3 gen_evaluation_table.py path_to_test.json
# Output will be located cwd as evaluation-time-of-test.xlsx
import json
import pandas as pd
import numpy as np
import os
import argparse

def generate_anaylze_table(json_path):
    test_id = os.path.splitext(json_path)[0][len("test-summary-"):]
    data = json.loads(open(json_path).read())
    time_table = []
    alarm_table = []
    config_table = []
    to_fill = "fill_me"
    test_type_list = ["atomicity-violation", "time-travel", "observability-gap"]
    def make_test_key(test_type, key):
        test_type_map = {
            "atomicity-violation": "atom-vio",
            "time-travel": "time-travel",
            "observability-gap": "obs-gap",
            "all": "all",
            "events": "events",
        }
        return '%s (%s)'%(key, test_type_map[test_type])
    for operator in data:
        if operator == 'failed':
            continue
        for workload in data[operator]:
            time_data = {
                'operator': operator,
                'workload': workload,
                make_test_key("all", "test_time"): 0,
                make_test_key("all", "avg_time"): 0,
            }
            alarm_data = {
                'operator': operator,
                'workload': workload,
                '# all the new bugs': to_fill,
                '# new bugs (excluding by-product) ones we can reliably reproduce (the three types)': to_fill,
                '# total alarms': 0,
                '# total false alarms': to_fill,
            }
            config_data = {
                'operator': operator,
                'workload': workload,
            }
            total_durations = []
            for test_type in test_type_list:
                if test_type in data[operator][workload]:
                    test_set = data[operator][workload][test_type]
                else:
                    test_set = []
                ret_map = {i : 0 for i in range(-4, 2)}
                durations = []
                for config in test_set:
                    test = test_set[config]
                    ret_val = test['ret_val']
                    if ret_val > 0:
                        ret_map[1] += 1
                    else:
                        ret_map[ret_val] += 1
                    durations.append(test['duration'])
                total_durations.extend(durations)
                durations = np.array(durations)
                time_data[make_test_key(test_type, "test_time")] = np.sum(durations)
                time_data[make_test_key(test_type, "avg_time")] =  0 if len(durations) == 0 else np.mean(durations)
                alarm_data[make_test_key(test_type, "# total run")] = len(test_set)
                alarm_data[make_test_key(test_type, "# no failure (0)")] = ret_map[0]
                alarm_data[make_test_key(test_type, "# injection not started (-1)")] = ret_map[-1]
                alarm_data[make_test_key(test_type, "# injection not finished (-2)")] = ret_map[-2]
                alarm_data[make_test_key(test_type, "# cmd not returned (-3)")] = ret_map[-3]
                alarm_data[make_test_key(test_type, "# exception (-4)")] = ret_map[-4]
                alarm_data[make_test_key(test_type, "# total alarm (alarm > 0)")] = ret_map[1]
                alarm_data[make_test_key(test_type, "# flaky")] = to_fill
                alarm_data[make_test_key(test_type, "# true alarm (alarm > 0)")] = to_fill
                alarm_data[make_test_key(test_type, "# false alarm (alarm > 0)")] = to_fill
                alarm_data['# total alarms'] += ret_map[1]
                config_data[make_test_key(test_type, "# final")] = 0
                config_data[make_test_key(test_type, "# before cancellable pass")] = 0
                config_data[make_test_key(test_type, "# before detectable pass")] = 0
            total_durations = np.array(total_durations)
            time_data[make_test_key("all", "test_time")] = np.sum(total_durations)
            time_data[make_test_key("all", "avg_time")] = np.mean(total_durations)
            config_data[make_test_key("events", "# events (API server)")] = 0
            config_data[make_test_key("events", "# events (heard by operator)")] = 0
            config_data[make_test_key("events", "# write by operator")] = 0
            time_table.append(time_data)
            alarm_table.append(alarm_data)
            config_table.append(config_data)

    time_df = pd.DataFrame(time_table)
    alarm_df = pd.DataFrame(alarm_table)
    config_df = pd.DataFrame(config_table)
    
    dfs = {"massive testing - time": time_df, 
          "massive testing - alarm": alarm_df,
          "config generation": config_df}
    
    writer = pd.ExcelWriter('evaluation-%s.xlsx'%(test_id), engine='xlsxwriter')
    for sheetname, df in dfs.items():  # loop through `dict` of dataframes
        df.to_excel(writer, index=False, sheet_name=sheetname)  # send df to writer
        worksheet = writer.sheets[sheetname]  # pull worksheet object
        for idx, col in enumerate(df):  # loop through all columns
            series = df[col]
            max_len = max((
                series.astype(str).map(len).max(),  # len of largest item
                len(str(series.name))  # len of column name/header
                )) + 1  # adding a little extra space
            worksheet.set_column(idx, idx, max_len)  # set column width
    writer.save()

#     with pd.ExcelWriter('%s.xlsx'%(test_id)) as writer:  
#         time_df.to_excel(writer, index=False, sheet_name="massive testing - time")
#         alarm_df.to_excel(writer, index=False, sheet_name="massive testing - alarm")
#         config_df.to_excel(writer, index=False, sheet_name="config generation")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate anaylze table')
    parser.add_argument('json', help='test json path')
    args = parser.parse_args()
    generate_anaylze_table(args.json)