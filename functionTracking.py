import atexit

import threading
import time
from  queue import  Queue

class FunctionMeta:
    #one functionMeta object represents one function that is to be tracked
    exited = False #flag whether utility has been exited from (for good)
    functionsRegistered = list()#list of all the functionMeta objects created
    nextFunctionCallID = 0 #each registered function call has a unique ID provided by this variable
    metaMutex = threading.Lock() #insures unique function call ID as well as that no two FunctionMeta object refer to the same function
    def __init__(self, name):
        self.name = name
        self.activeFunctionCalls = list() # list of tuples: (function_call_ID, function_call_start_time)
        self.finishedCallsCount = 0
        self.finishedCallsLifetime = 0
        self.myMutex = threading.Lock()  #insures consistency when updating object fields
        self.enabled = True #flag that indicates whether profiling is enabled for this function
        self.decorated = False #flag that indicates whether FunctionMeta object has been created by a
        #decorator or by terminal command("$disable function" command). It prevents printing out functions which users have (mistakenly)
        # toogled in terminal and which are not decorated in code

    #prints all FunctionMeta objects information, which the user is subscribed to
    @classmethod
    def printAll(cls):
        print('\033[96m', end='')#making the output color CYAN
        row_format = ( "{:>30} |") * 5
        data = list()
        for meta in cls.functionsRegistered:
            if (meta.enabled and meta.decorated): data.append(meta)
        if (len(data) == 0): print('no decorated and enabled function are available') # avoiding printing headers if no function is toogled
        else:
            print(row_format.format('fn. name', 'avg. call completion time', 'fn. calls completed',
                                                'currently active fn. calls', 'total lifetime'))
            header_border = list()
            for i in range (15): header_border.append(' ')
            for i in range(145): header_border.append('_')
            print(''.join(header_border))
            for meta in data:
                averegeCompleteTime = 0
                activeCallsLifetime = 0
                currentTime = time.time()
                for instace in meta.activeFunctionCalls:
                    activeCallsLifetime += currentTime - instace[1]
                if (meta.finishedCallsCount > 0): averegeCompleteTime = meta.finishedCallsLifetime / meta.finishedCallsCount
                print(row_format.format(meta.name, averegeCompleteTime, meta.finishedCallsCount,
                                        len(meta.activeFunctionCalls), activeCallsLifetime + meta.finishedCallsLifetime))
        print('\033[0m', end='')#resetting the output color

    @classmethod
    def enableAll(cls):
        for meta in cls.functionsRegistered:
            meta.enabled = True

    @classmethod
    def disableAll(cls):
        for meta in cls.functionsRegistered:
            meta.enabled = False

    @classmethod
    def enable(cls, funName):
        for meta in FunctionMeta.functionsRegistered:
            if (meta.name == funName):
                meta.enabled = True
        #doesn't create a new funtionMeta entry as(because) information about
        # functions which are not called yet are not printed anyway and
        #the default value for 'enabled is True
    @classmethod
    def disable(cls, funName):
        cls.metaMutex.acquire()
        for meta in cls.functionsRegistered:
            if (meta.name == funName):
                meta.enabled = False
                cls.metaMutex.release()
                return
        newMeta = FunctionMeta(funName)
        newMeta.enabled = False
        cls.functionsRegistered.append(newMeta)
        cls.metaMutex.release()

def TrackExecutionTime(func):
    def wrapper(*args, **kwargs):

        functionsRegistered = FunctionMeta.functionsRegistered
        functionIndex = -1
        myFunction:FunctionMeta
        trackMyFunction = False
        if(not FunctionMeta.exited):
            FunctionMeta.metaMutex.acquire()
            for i in range(len(functionsRegistered) ):
                if(func.__name__ == functionsRegistered[i].name): functionIndex = i
            if(functionIndex == -1):
                newFunction = FunctionMeta(func.__name__)
                functionIndex = len(functionsRegistered)
                functionsRegistered.append(newFunction)
            FunctionMeta.metaMutex.release()
            myFunction = FunctionMeta.functionsRegistered[functionIndex]
            myFunction.decorated = True

            trackMyFunction = myFunction.enabled
            if(trackMyFunction):
                FunctionMeta.metaMutex.acquire(blocking=True, timeout=-1)
                myId = FunctionMeta.nextFunctionCallID
                FunctionMeta.nextFunctionCallID += 1
                FunctionMeta.metaMutex.release()
                myStartTime = time.time()
                myFunction.activeFunctionCalls.append((myId, myStartTime))

        result = func(*args, **kwargs)

        #it uses local Bool (as opposed to myFunction.enabled), so that it can finish processing started calls(even if they have been
        # toogled off while executing) and avoid giving inconsistent results
        if(trackMyFunction):
            myFunction.myMutex.acquire()
            activeCallIndex = -1
            for i in range(len(myFunction.activeFunctionCalls)):
                if(myId == myFunction.activeFunctionCalls[i]):
                    activeCallIndex = i
            myFunction.activeFunctionCalls.pop(activeCallIndex)
            myFunction.finishedCallsLifetime += (time.time() - myStartTime)
            myFunction.finishedCallsCount += 1
            myFunction.myMutex.release()

        return result
    return wrapper

inputQueue = Queue()


def userInput(arg = None):
    if arg:
        print(arg, end='')
    if(FunctionMeta.exited == False):
        result =  inputQueue.get()
        # previous line is important for a scentario, in which inputDaemon thread exits
        # while the user program still executes. It prevents the user program from
        # blocking on an inputQueue endlessly. In such scenario the input function
        # has already been restored
        if (result != None): return result
        return old_input()

    return  old_input()
old_input = input
input = userInput #input function hijacking

def kernelInput():
    while(True):
        try:
            s = old_input()
            inputElements = s.split()
            if(len(inputElements) == 0):
                inputQueue.put(s)
            elif(inputElements[0] == '$display' and len(inputElements) == 1):
                FunctionMeta.printAll()
            elif(inputElements[0] == '$toogleAllOn'and len(inputElements) == 1):
                FunctionMeta.enableAll()
                print('\033[96m' + 'OK' + '\033[0m')
            elif (inputElements[0] == '$toogleAllOff'and len(inputElements) == 1):
                FunctionMeta.disableAll()
                print('\033[96m' + 'OK' + '\033[0m')
            elif (inputElements[0] == '$exit'and len(inputElements) == 1):
                FunctionMeta.exited = True
                inputQueue.put(None)#None is a poison pill that unstucks the input() functions if they are stuck
                break
            elif(inputElements[0] == '$toogleOn'):
                if(len(inputElements) != 2): inputQueue.put(s)
                else:
                    FunctionMeta.enable(inputElements[1])
                    print('\033[96m' + 'OK' + '\033[0m')
            elif (inputElements[0] == '$toogleOff'):
                if (len(inputElements) != 2): inputQueue.put(s)
                else:
                    FunctionMeta.disable(inputElements[1])
                    print('\033[96m' + 'OK' + '\033[0m')
            else: inputQueue.put(s)
        except:
            break


input_deamon = threading.Thread(target=kernelInput, args=(),)
input_deamon.start()




def exitCode():
    input_deamon.join()
#python program that uses this utility doesn't end until this utility
#has been exited from
atexit.register(exitCode)


