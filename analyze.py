import json
import copy

SONAR_EVENT_MARK = "[SONAR-EVENT]"
SONAR_RECORD_MARK = "[SONAR-RECORD]"


def compare(map1, map2, ex):
    for key in map2:
        if key in ex:
            continue
        if key not in map1:
            print(key + " is different here")
        elif str(map1[key]) != str(map2[key]):
            print(key + " is different here")
            if key == "conditions" or key == "phase":
                print(str(map1[key]))
                print(str(map2[key]))

def constructEventMap(path):
    eventMap = {}
    for line in open(path).readlines():
        if SONAR_EVENT_MARK not in line:
            continue
        line = line[line.find(SONAR_EVENT_MARK):].strip()
        tokens = line.split("\t")
        eventID = tokens[1]
        eventType = tokens[2]
        eventObject = json.loads(tokens[3])
        name = eventObject["metadata"]["name"]
        if name not in eventMap:
            eventMap[name] = []
        eventMap[name].append({"eventID": eventID, "eventType": eventType, "eventObject": eventObject})
    return eventMap

def constructRecords(path):
    records = []
    for line in open(path).readlines():
        if SONAR_RECORD_MARK not in line:
            continue
        line = line[line.find(SONAR_RECORD_MARK):].strip()
        tokens = line.split("\t")
        effects = json.loads(tokens[1])
        eventID = tokens[2]
        eventType = tokens[3]
        eventObject = json.loads(tokens[4])
        name = eventObject["metadata"]["name"]
        records.append({"effects": effects, "name": name, "eventID": eventID, "eventType": eventType, "eventObject": eventObject})
    return records

def findPreviousEventWithName(id, name, eventMap):
    assert name in eventMap, "invalid name %s, not found in eventMap" % (name)
    for i in range(len(eventMap[name])):
        if eventMap[name][i]["eventID"] == id:
            if i == 0:
                return None, eventMap[name][i]
            else:
                return eventMap[name][i-1], eventMap[name][i]

def compressObject(prevObject, curObject, slimPrevObject, slimCurObject):
    toDel = []
    allKeys = set(curObject.keys()).union(prevObject.keys())
    for key in allKeys:
        if key not in curObject:
            # slimPrevObject[key] = "SONAR-EXISTENCE"
            continue
        elif key not in prevObject:
            # slimCurObject[key] = "SONAR-EXISTENCE"
            continue
        elif key == "resourceVersion" or key == "time" or key == "managedFields" or key == "lastTransitionTime" or key == "generation":
            # slimCurObject[key] = None
            # slimPrevObject[key] = None
            toDel.append(key)
        elif str(curObject[key]) != str(prevObject[key]):
            if isinstance(curObject[key], dict):
                res = compressObject(prevObject[key], curObject[key], slimPrevObject[key], slimCurObject[key])
                if res:
                    # slimCurObject[key] = None
                    # slimPrevObject[key] = None
                    toDel.append(key)
            elif isinstance(curObject[key], list):
                for i in range(len(curObject[key])):
                    if i >= len(prevObject[key]):
                        break
                    elif str(curObject[key][i]) != str(prevObject[key][i]):
                        if isinstance(curObject[key][i], dict):
                            res = compressObject(prevObject[key][i], curObject[key][i], slimPrevObject[key][i], slimCurObject[key][i])
                            if res:
                                slimCurObject[key][i] = "SONAR-SKIP"
                                slimPrevObject[key][i] = "SONAR-SKIP"
                        elif isinstance(curObject[key][i], list):
                            assert False
                        else:
                            continue
                    else:
                        slimCurObject[key][i] = "SONAR-SKIP"
                        slimPrevObject[key][i] = "SONAR-SKIP"
            else:
                continue
        else:
            # slimCurObject[key] = None
            # slimPrevObject[key] = None
            toDel.append(key)
    for key in toDel:
        del slimCurObject[key]
        del slimPrevObject[key]
    if len(slimCurObject) == 0 and len(slimPrevObject) == 0:
        return True
    return False

def diffEvents(prevEvent, curEvent):
    assert prevEvent["eventType"] == "Updated"
    assert curEvent["eventType"] == "Updated"
    prevObject = prevEvent["eventObject"]
    curObject = curEvent["eventObject"]
    assert prevObject["metadata"]["name"] == curObject["metadata"]["name"]

    slimPrevObject = copy.deepcopy(prevObject)
    slimCurObject = copy.deepcopy(curObject)
    compressObject(prevObject, curObject, slimPrevObject, slimCurObject)
    return slimPrevObject, slimCurObject


def traverseRecordsWithName(records, eventMap, name):
    triggeringPoints = []
    for record in records:
        if record["name"] != name:
            continue
        prevEvent, curEvent = findPreviousEventWithName(record["eventID"], record["name"], eventMap)
        tp = {  "name": name, "namespace": curEvent["eventObject"]["metadata"]["namespace"],
                "otype": curEvent["eventObject"]["metadata"]["selfLink"].split("/")[5],
                "effects": record["effects"]}
        print("Object name(space):", tp["name"], tp["namespace"])
        print("Object type:", tp["otype"])
        print("Triggered effects:", tp["effects"])
        if prevEvent is None:
            tp["ttype"] = "event"
            print("Triggering event:", record["eventType"], record["eventObject"])
        else:
            if prevEvent["eventType"] != curEvent["eventType"]:
                tp["ttype"] = "event-type-delta"
                tp["prevEventType"] = prevEvent["eventType"]
                tp["curEventType"] = curEvent["eventType"]
                print("Triggering type:", prevEvent["eventType"], curEvent["eventType"])
            else:
                slimPrevObject, slimCurObject = diffEvents(prevEvent, curEvent)
                tp["ttype"] = "event-content-delta"
                tp["prevEvent"] = slimPrevObject
                tp["curEvent"] = slimCurObject
                print("Triggering diff:")
                print("Prev:")
                print(slimPrevObject)
                print("")
                print("Cur:")
                print(slimCurObject)
        print("==========================================================")
        triggeringPoints.append(tp)
    return triggeringPoints

if __name__ == "__main__":
    path = "log/ca2/learn/sonar-server.log"
    eventMap = constructEventMap(path)
    records = constructRecords(path)
    json.dump(eventMap, open("event-map.json", "w"), indent=4)
    json.dump(records, open("records.json", "w"), indent=4)
    
    triggeringPoints = []
    for name in eventMap:
        triggeringPoints = triggeringPoints + traverseRecordsWithName(records, eventMap, name)
    json.dump(triggeringPoints, open("triggering-points.json", "w"), indent=4)

