import pandas
import argparse
import os

def gen_alarm_evaluation(path: os.PathLike) -> pandas.DataFrame:
    # |operator|test|mode|config|host|ret_val|result|comment|
    inspectionDF = pandas.read_csv(path, header=0)
    alarm_table = []
    operators = inspectionDF['operator'].unique()

    for operator in operators:
        operatorDF = inspectionDF[inspectionDF['operator'] == operator]
        tests = operatorDF['test'].unique()
        for test in tests:
            testDF = operatorDF[operatorDF['test'] == test]
            alarmDF = testDF[testDF['ret_val'] > 0]
            total_alarms = len(alarmDF.index)
            total_bugs = len(testDF[(testDF['result'] == 'newbug') | (testDF['result'] == 'by-product')])
            total_newbugs = len(testDF[testDF['result'] == 'newbug'])
            total_false_alarms = len(testDF[testDF['result'] == 'false-alarm'])

            alarm_data = {
                'operator': operator,
                'test case': test,
                '# all the new bugs': total_bugs,
                '# new bugs (excluding by-product) ones we can reliably reproduce (the three types)': total_newbugs,
                '# total alarms': total_alarms,
                '# total false alarms': total_false_alarms
            }

            modes = ['atomicity-violation', 'time-travel', 'observability-gap']

            for mode in modes:    
                modeDF = testDF[testDF['mode'] == mode]
                mode_total = len(modeDF.index)
                mode_no_fail_count = len(modeDF[modeDF['ret_val'] == 0])
                mode_not_started_count = len(modeDF[modeDF['ret_val'] == -1])
                mode_not_finished_count = len(modeDF[modeDF['ret_val'] == -2])
                mode_not_returned_count = len(modeDF[modeDF['ret_val'] == -3])
                mode_exception_count = len(modeDF[modeDF['ret_val'] == -4])

                mode_flaky_count = len(modeDF[modeDF['result'] == 'flaky'])
                mode_newbug_count = len(modeDF[(modeDF['result'] == 'newbug') | (modeDF['result'] == 'by-product')])
                mode_false_alarm_count = len(modeDF[modeDF['result'] == 'false_alarm'])

                alarm_data['# total run (%s)' % mode] = mode_total
                alarm_data['# no failure (0) (%s)' % mode] = mode_no_fail_count
                alarm_data['# injection not started (-1) (%s)' % mode] = mode_not_started_count
                alarm_data['# injection not finished (-2) (%s)' % mode] = mode_not_finished_count
                alarm_data['# cmd not returned (-3) (%s)' % mode] = mode_not_returned_count
                alarm_data['# exception (-4) (%s)' % mode] = mode_exception_count
                alarm_data['# flaky (%s)' % mode] = mode_flaky_count
                alarm_data['# true alarm (%s)' % mode] = mode_newbug_count
                alarm_data['# false alarm (%s)' % mode] = mode_false_alarm_count

            alarm_table.append(alarm_data)
    return alarm_table

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate evaluation alarm sheet from inspection results.")
    parser.add_argument('-f', dest='input', help="Input file", required=True)
    args = parser.parse_args()
    test_id = os.path.splitext(os.path.basename(args.input))[0][len("test-summary-"):]

    alarm_df = pandas.DataFrame(gen_alarm_evaluation(args.input))
    writer = pandas.ExcelWriter('evaluation-alarm-%s.xlsx'%(test_id), engine='xlsxwriter')
    alarm_df.to_excel(writer, index=False)
    writer.save()