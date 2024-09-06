import csv
import threading
import random
import time
import subprocess
from queue import Queue

class keyboardActivity():

    def action(username,password,task,host,sleep,variance,extra,queue):
        while 1==1:
            # Could use Ansible.runner
            #print("Logging in\n")
            queue.put("Logging into "+host+"\n")
            login_result = subprocess.run(["ansible-playbook", "./tasks/keyboard-ctrl-alt-del-login.yml", "-i", "catfish-it-inventory.txt", "-l", host, "-e", "login_password="+password], capture_output=True, text=True )
            queue.put(str(login_result))
            #time.sleep(3)
            #print("Running task: ansible-playbook "+ task+ " -i catfish-it-inventory.txt -l "+ host + " -e login_password="+password+ " -e "+ extra+"\n")
            queue.put("Launching "+task+ " on "+host+"\n")
            task_result = subprocess.run(["ansible-playbook", task, "-i", "catfish-it-inventory.txt", "-l", host, "-e", "login_password="+password, "-e", "website="+extra], capture_output=True, text=True )
            queue.put(str(task_result))
            # ansible-playbook ./tasks/keyboard-ctrl-alt-del-login.yml -i catfish-it-inventory.txt -l haw-ce-wks1 -e login_password='S3cur1ty@Lab'
            # ansible-playbook ./tasks/keyboard-open-edge-website.yml -i catfish-it-inventory.txt -l haw-ce-wks1 -e website='https://www.msn.com'

            mysleep=random.randint(sleep-variance,sleep+variance)*60
            #print(username+" sleeping "+str(mysleep)+"\n")
            queue.put(username+" sleeping "+str(mysleep)+"\n")
            #exit()
            time.sleep(mysleep)

    def printer(queue):
        while 1==1:
            message = queue.get()
            print(message)

    with open('./misc/user-activity.txt') as f:
        mapping = csv.reader(f)
        queue = Queue()
        i=0
        my_print_thread = threading.Thread(target=printer, args=( queue, ), daemon=True)
        my_print_thread.start()
        for row in mapping:
            if i > 0:
                username=row[0]
                password=row[1]
                host=row[2]
                task=row[3]
                sleep=int(row[4])
                variance=int(row[5])
                extra=str(row[6])

                print("starting thread "+str(i)+" for "+username+" "+task+" "+host+" ")
                my_thread = threading.Thread(target=action, args=(username,password ,task, host,sleep ,variance, extra, queue ))
                my_thread.start()
            i=i+1
