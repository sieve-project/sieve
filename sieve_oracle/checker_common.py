def generate_alarm(sub_alarm, msg):
    return "[ALARM]" + sub_alarm + " " + msg


def generate_warn(msg):
    return "[WARN] " + msg


def generate_fatal(msg):
    return "[FATAL] " + msg
