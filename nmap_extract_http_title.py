#coding:utf-8

'''
parse nmap output and extract the http title
'''
import gevent,time,cchardet
from gevent import monkey
monkey.patch_all()
import  re,threading
from queue import Queue
import urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup

FILE_NAME="139_196_web.txt"
OUT_FILE="aaa.txt"
NUM_OF_THREAD = 50
#FILE_NAME="test.txxt"

class UrlParser(threading.Thread):
    def __init__(self,outFile,queue):
        threading.Thread.__init__(self)
        self._file = outFile
        self._queue = queue
    
    def run(self):
        schema = ""
        host = ""
        for line in self._file:
            if "Nmap scan report for" in line:
                host = line.split(" ")[-1].strip()

            if re.search(r"\bopen\b",line) != None:
                schema,port = self.parse_port_schema(line)
                url = schema + "://" + host + ":" + port
                self._queue.put(url)

        # 放入5个 保证gevent能够正常退出
        for i in range(NUM_OF_THREAD):
            self._queue.put("quit")
    
    def parse_port_schema(self,line):
        schema = line.split(" ")[-1].strip()
        if schema !="https":
            schema = "http"
        port = line.split(" ")[0].split("/")[0].strip()
        return schema,port

class TitleParser(threading.Thread):

    def __init__(self,queue):
        threading.Thread.__init__(self)
        self._queue = queue
        self._outFile = open(OUT_FILE,'w',encoding="utf-8")


        self._res = {}
        self._http = urllib3.PoolManager(cert_reqs='CERT_NONE')

    def run(self):
        gthreads = [gevent.spawn(self._scan,i) for i in range(NUM_OF_THREAD)]   
        gevent.joinall(gthreads)

    def _scan(self,i):
        response = None
        retCode = 0

        while True:
            url = self._queue.get()               
            if url == "quit":
                break
            try:
                response = self._http.request('GET',url,headers = headers,timeout=5)
                retCode = response.status
                if (response.status != 200):
                    title = ""
                else:
#responseText = self.utf8_transfer(response.data)
#                    html = response.data
#                    encodeType = cchardet.detect(html) 
#                    encoding = "utf-8" if encodeType["encoding"] == None else encodeType["encoding"]
#                    responseText =  html.decode(encoding)
#                    title = self.parse_title(responseText)
                    title = self.parse_title(response.data)
            except Exception as e:
                retCode = 500
                title = ""
                print(e)
            finally: 
                self._outFile.write( url + " " + str(retCode) + " " + title + "\n")   
                self._outFile.flush()

    def parse_title(self,content):
        title = ""
#        titleList = re.findall(r"<title>.*</title>",content)
        html = BeautifulSoup(content,'lxml')
        if html != None:
            if html.title != None:
                title = html.title.string.strip()
        return title
#        if titleList != []:
#            title = titleList[0][7:-8].strip()
#        return title
    def close(self):
        self._outFile.close()
           
def main():
    urlQueue= Queue()
    with open(FILE_NAME) as webFile:
        producer = UrlParser(webFile,urlQueue)
        consumer = TitleParser(urlQueue)
        producer.start()
        consumer.start()
        producer.join()
        consumer.join()
        consumer.close()
        print("提取成功")
        

if __name__ == '__main__':
    main()
