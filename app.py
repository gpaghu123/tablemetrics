from prometheus_client import start_http_server, Gauge, Info, make_wsgi_app
import prometheus_client
import time
import base64
import pycurl
import certifi
from io import BytesIO
import sys
import json
import datetime
from datetime import timedelta


prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)

def get_metrics(item):
    # print(item)

    time_since_lastLoadTime = datetime.datetime.now() - datetime.datetime.fromtimestamp(item["lastLoadTime"]/1e3)
    time_since_lastReplicationTime = datetime.datetime.now() - datetime.datetime.fromtimestamp(item["lastReplicationTime"]/1e3)
    match item["replicationStatus"]:
        case "Enabled":
            replicating = 1
        case _:
            replicating = 0
    rname = item["id"]
    sizeFact = item["tableSize"][-2:]
    sizeNum = float(item["tableSize"].split(" ")[0])
    match sizeFact:
        case "MB":
            sizeRet = sizeNum/1e3
        case "GB":
            sizeRet = sizeNum/1.0
        case "TB":
            sizeRet = sizeNum * 1e3
        case _:
            tb = sys.exc_info()[2]
            raise(ValueError("Invalid table size value")).with_traceback(tb)
    # print(rname)
    return (rname,replicating,sizeRet,time_since_lastLoadTime/timedelta(minutes=1),time_since_lastReplicationTime/timedelta(minutes=1))

def refresh_table_metrics():
    print("refreshing...")
    token= base64.b64encode("admin:Uh68bJcGJithBQl87Q9bp1SW0jZ0kfwht4ZV6u45".encode("UTF-8"))
    buffer = BytesIO()
    c = pycurl.Curl()
    customheaders = ["Authorization: ZenApiKey {0}".format(base64.b64encode("admin:Uh68bJcGJithBQl87Q9bp1SW0jZ0kfwht4ZV6u45".encode("ascii")).decode('UTF8'))]
    c.setopt(c.URL,"https://cpd-zen1.apps.dgsvt5.cp.fyre.ibm.com/icp4data-databases/dg-1672018833030580/zen1/clone_system/clone_engine/clone_table")
    c.setopt(c.HTTPHEADER, customheaders)
    c.setopt(c.SSL_VERIFYPEER, 0)
    c.setopt(c.SSL_VERIFYHOST, 0)
    c.setopt(c.CUSTOMREQUEST, "GET")
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.CAINFO, certifi.where())
    try:
        c.perform()
    except:
        print(sys.exc_info())
    finally:
        c.close()

    #print(buffer.getvalue().decode('iso-8859-1'))
    jsonstr = json.loads(buffer.getvalue().decode('iso-8859-1'))
    #print(jsonstr)
    return(jsonstr["result"])
# f = open("instance-level-metrics.txt","r")
# jsonstr = json.load(f)
ary = refresh_table_metrics()
ns = 'DGTable'
#subsys = ary["cloneEngineName"]+"_"+ary["locationName"]
#ary = ary["tableCloneStatus"]
nameAry = {}
for item in ary:
    rname,replicating,sizeRet,lastload,lastrepl = get_metrics(item)
    metricAry = {}
    metricAry["repl"] = Gauge("Replicating","Table replication. 1=Enabled",namespace=rname)
    metricAry["size"] = Gauge("TableSize","Table size in GB",namespace=rname)
    metricAry["lastload"]= Gauge("lastload","Minutes since last load",namespace=rname)
    metricAry["lastrepl"]= Gauge("lastrepl","Minutes since last replicate",namespace=rname)
    nameAry[rname] = metricAry
if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(8080)
    # Generate some requests.
    #generalInfo.set_function(get_Value)
while True:
    i = 0

    ary = refresh_table_metrics()
    for item in ary:
        rname,replicating,sizeRet,lastload,lastrepl = get_metrics(item)
        nameAry[rname]["repl"].set(replicating)
        nameAry[rname]["size"].set(replicating)
        nameAry[rname]["lastload"].set(lastload)
        nameAry[rname]["lastrepl"].set(lastrepl)
    time.sleep(30)
