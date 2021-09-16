#!/usr/bin/env python3
import py_cui
import controllers
import os
import json


def run():
    data = json.loads(open(".sieve_tui_session").read())
    operator = data["operator"]
    workload = data["workload"]
    action = data["action"]
    mode = controllers.test_suites[operator][workload].mode
    print(operator, workload, action, mode)
    if action in ["learn-once", "learn-twice"]:
        os.system("python3 sieve.py -p %s -t %s -s learn -m %s" % (operator, workload, action))
    elif action == "test":
        os.system("python3 sieve.py -p %s -t %s" % (operator, workload))
    elif action == "build for learn":
        os.system("python3 build.py -p %s -m learn" % (operator))
    elif action == "build for test":
        os.system("python3 build.py -p %s -m %s" % (operator, mode))
    elif action == "learn check only":
        os.system(
            "python3 sieve.py -p %s -t %s -s learn --phase=check_only"
            % (operator, workload)
        )
    elif action == "test check only":
        os.system(
            "python3 sieve.py -p %s -t %s --phase=check_only" % (operator, workload)
        )


class SieveTUI:

    # We add type annotations to our master PyCUI objects for improved intellisense
    def __init__(self, master: py_cui.PyCUI):

        self.master = master

        # The scrolled list cells that will contain our tasks in each of the three categories
        self.operator_scroll_cell = self.master.add_scroll_menu(
            "Operator", 0, 0, row_span=6, column_span=2
        )
        self.workload_scroll_cell = self.master.add_scroll_menu(
            "Workload", 0, 2, row_span=6, column_span=2
        )
        self.action_scroll_cell = self.master.add_scroll_menu(
            "Action", 0, 4, row_span=6, column_span=2
        )

        self.operator_scroll_cell.add_item_list(controllers.test_suites.keys())

        self.operator_scroll_cell.add_key_command(
            py_cui.keys.KEY_ENTER, self.goto_workload
        )
        self.workload_scroll_cell.add_key_command(
            py_cui.keys.KEY_ENTER, self.goto_action
        )
        self.action_scroll_cell.add_key_command(py_cui.keys.KEY_ENTER, self.take_action)

        self.master.set_selected_widget(self.operator_scroll_cell.get_id())

    def goto_workload(self):
        operator = self.operator_scroll_cell.get()
        self.workload_scroll_cell.clear()
        self.workload_scroll_cell.add_item_list(
            controllers.test_suites[operator].keys()
        )
        self.master.set_selected_widget(self.workload_scroll_cell.get_id())

    def goto_action(self):
        operator = self.operator_scroll_cell.get()
        workload = self.workload_scroll_cell.get()
        actions = [
            "learn-once",
            "learn-twice",
            "test",
            "build for learn",
            "build for test",
            "learn check only",
            "test check only",
        ]
        self.action_scroll_cell.clear()
        self.action_scroll_cell.add_item_list(actions)
        self.master.set_selected_widget(self.action_scroll_cell.get_id())

    def take_action(self):
        operator = self.operator_scroll_cell.get()
        workload = self.workload_scroll_cell.get()
        action = self.action_scroll_cell.get()

        data = {"operator": operator, "workload": workload, "action": action}

        open(".sieve_tui_session", "w").write(json.dumps(data))

        self.master.run_on_exit(run)
        self.master.stop()


# Create the CUI with 7 rows 6 columns, pass it to the wrapper object, and start it
root = py_cui.PyCUI(7, 6)
root.set_title("Sieve Terminal UI")
s = SieveTUI(root)
root.start()
