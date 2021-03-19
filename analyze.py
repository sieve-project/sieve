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

# def diffMetadata(prevMetadata, curMetadata):
#     diff = {}
#     for key in curMetadata:
#         if key == "resourceVersion" or key == "managedFields":
#             continue
#         elif key not in prevMetadata:
#             diff[key] = [None, curMetadata[key]]
#         elif str(curMetadata[key]) != str(prevMetadata[key]):
#             diff[key] = [prevMetadata[key], curMetadata[key]]
#     return diff

# def diffObject(prevObject, curObject, diff):
#     for key in curObject:
#         if key not in prevObject:
#             diff[key] = curObject[key]
#         elif str(curObject[key]) != str(prevObject[key]):
#             if isinstance(curObject[key], dict):
#                 diff[key] = {}
#                 diffObject(prevObject[key], curObject[key], diff[key])
#             elif isinstance(curObject[key], list):
#                 diff[key] = []
#                 for i in range(len(curObject[key])):
#                     if i >= len(prevObject):
#                         diff[key][i] = curObject[key][i]
#                     elif str(curObject[key][i]) != str(prevObject[key][i]):
#                         if isinstance(curObject[key][i], dict):
#                             diff[key][i] = {}
#                             diffObject(prevObject[key][i], curObject[key][i], diff[key][i])
#                         elif isinstance(curObject[key][i], list):
#                             assert False
#                         else:
#                             diff[key][i] = curObject[key][i]
#             else:
#                 diff[key] = curObject[key]

def compressObject(prevObject, curObject, slimPrevObject, slimCurObject):
    toDel = []
    for key in curObject:
        if key not in prevObject:
            continue
        elif key == "resourceVersion" or key == "time" or key == "managedFields" or key == "lastTransitionTime" or key == "generation":
            slimCurObject[key] = None
            slimPrevObject[key] = None
            toDel.append(key)
        elif str(curObject[key]) != str(prevObject[key]):
            if isinstance(curObject[key], dict):
                res = compressObject(prevObject[key], curObject[key], slimPrevObject[key], slimCurObject[key])
                if res:
                    slimCurObject[key] = None
                    slimPrevObject[key] = None
                    toDel.append(key)
            elif isinstance(curObject[key], list):
                for i in range(len(curObject[key])):
                    if i >= len(prevObject[key]):
                        break
                    elif str(curObject[key][i]) != str(prevObject[key][i]):
                        if isinstance(curObject[key][i], dict):
                            res = compressObject(prevObject[key][i], curObject[key][i], slimPrevObject[key][i], slimCurObject[key][i])
                            if res:
                                slimCurObject[key][i] = None
                                slimPrevObject[key][i] = None
                        elif isinstance(curObject[key][i], list):
                            assert False
                        else:
                            continue
                    else:
                        slimCurObject[key][i] = None
                        slimPrevObject[key][i] = None
            else:
                continue
        else:
            slimCurObject[key] = None
            slimPrevObject[key] = None
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
    for record in records:
        if record["name"] != name:
            continue
        prevEvent, curEvent = findPreviousEventWithName(record["eventID"], record["name"], eventMap)
        print("Object name:", name)
        print("Triggered effects:", record["effects"])
        if prevEvent is None:
            print("Triggering event:", record["eventType"], record["eventObject"])
        else:
            if prevEvent["eventType"] != curEvent["eventType"]:
                print("Triggering type:", prevEvent["eventType"], curEvent["eventType"])
            else:
                slimPrevObject, slimCurObject = diffEvents(prevEvent, curEvent)
                print("Triggering diff:")
                print("Prev:")
                print(slimPrevObject)
                print("")
                print("Cur:")
                print(slimCurObject)
        print("==========================================================")

if __name__ == "__main__":
    path = "log/ca2/learn/sonar-server.log"
    eventMap = constructEventMap(path)
    records = constructRecords(path)
    json.dump(eventMap, open("event-map.json", "w"), indent=4)
    json.dump(records, open("records.json", "w"), indent=4)
    
    for name in eventMap:
        traverseRecordsWithName(records, eventMap, name)
