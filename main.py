import  threading
import  time
import random
from functionTracking import *

@TrackExecutionTime
def printHello(name):
    print('hello ' + name + '!')
    time.sleep(random.randint(5, 10))
@TrackExecutionTime
def calculate():
    while(True):
        try:

            s = input('Please enter two addents: ')
            s = s.split()
            if(len(s) != 2): raise Exception('Error: expected 2 arguments.')
            x = int(s[0])
            y = int(s[1])
            print(x+y)
            break
        except ValueError:
            print('Error: recieved non-numerical arguments.')
        except Exception as e:
            print(str(e))



if __name__ == '__main__':
    threads = list()
    threads.append(threading.Thread(target=printHello, args=('Dogs',)))
    threads.append(threading.Thread(target=printHello, args=('Cats',)))
    threads.append(threading.Thread(target=printHello, args=('Lizards',)))
    threads.append(threading.Thread(target=printHello, args=('Computers',)))

    print('Type input to echo')
    print(input())
    for thrd in threads: thrd.start()
    calculate()
    calculate()
    calculate()

    print('Type input to echo')
    print(input())
    for thrd in threads: thrd.join()





