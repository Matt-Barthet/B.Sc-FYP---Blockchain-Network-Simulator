from Util import *

'''
Transaction (pure python) class represents an on-chain transaction.
The fee of a transactions depicts the amount the miner will be paid.
'''
class Transaction:
    def __init__(self, hash, to_address, from_address, value, fee):
        self.hash = hash
        self.to_address = to_address
        self.from_address = from_address
        self.value = value
        self.fee = fee

'''
Block (pure python) class represents a collection of on-chain transactions.
Blocks contain a dictionary of the transactions they encapsulate.
Transactions are selected from an available pool based off their fee.
'''
class Block:
    def __init__(self, hash, father, timestamp, process, depth, transactions):
        self.hash = hash
        self.father = father
        self.timestamp = timestamp
        self.process = process
        self.depth = depth
        self.transactions = transactions

'''
Block Tree class represent the collection of blocks in the network.
Uses depth values to identify the ordering of blocks.
'''
class Blocktree(Pyc.CComponent):
    def __init__(self, name):
        Pyc.CComponent.__init__(self, name)

        '''
        Defining the variables and references used by the process class.
        These will be used in communication through the message boxes.
        '''
        self.blocks = []
        self.v_appendedBlock = self.addVariable("Appended Block", Pyc.TVarType.t_string, "0x0")
        self.r_lastBlock = self.addReference("Last Block")

        '''
        Creating the message boxes that will be used to communicate with the processes
        Wiring the variables according to their direction in communication.
        '''
        self.addMessageBox("Process")
        self.addMessageBoxImport("Process", self.r_lastBlock, "Last Block")
        self.addMessageBoxExport("Process", self.v_appendedBlock, "Appended Block")

    #TODO
    def appendBlock(self):
        print("Appending Block")

'''
Oracle class represents the abstract oracle entity.
Randomly selects the next winning process based on their merit.
'''
class Oracle(Pyc.CComponent):

    def __init__(self, name):
        Pyc.CComponent.__init__(self, name)

        '''
        Defining the system variables and references used by the process class.
        These will be used in communication through the message boxes.
        '''
        self.v_tokenHolder = self.addVariable("Token Holder", Pyc.TVarType.t_string, "0x0")
        self.v_meanBlockTime = self.addVariable("Mean Block Time", Pyc.TVarType.t_float, 0.0)
        self.v_tokenGenerated = self.addVariable("Token Generated", Pyc.TVarType.t_bool, False)
        self.r_merit = self.addReference("Merit")
        self.r_address = self.addReference("Address")

        '''
        Creating the message boxes that will be used to communicate with the oracle and block tree.
        Wiring the variables according to their direction in communication.
        '''
        self.addMessageBox("Process")
        self.addMessageBoxImport("Process", self.r_merit, "Merit")
        self.addMessageBoxImport("Process", self.r_address, "Address")
        self.addMessageBoxExport("Process", self.v_tokenHolder, "Token Holder")
        self.addMessageBoxExport("Process", self.v_tokenGenerated, "Token Generated")

        '''
        Constructing the Automaton which contains the states of the oracle class.
        The initial state is set to working as required.
        '''
        self.processAutomaton = self.addAutomaton("Oracle Automaton")
        self.waiting = self.addState("Oracle Automaton", "Waiting", 0)
        self.tokenGenerated = self.addState("Oracle Automaton", "Token Generated", 1)
        self.processAutomaton.setInitState(self.waiting)

        '''
        Defining the transitions between states of the process automaton.
        '''
        self.waitingToGenerated = self.waiting.addTransition("Waiting-to-Generated")
        self.waitingToGenerated.setCondition(self.generatedCondition)
        self.waitingToGenerated.addTarget(self.tokenGenerated)

        self.generatedToWaiting = self.tokenGenerated.addTransition("Generated-to-Waiting")
        self.generatedToWaiting.setCondition(self.waitingCondition)
        self.generatedToWaiting.addTarget(self.waiting)

    '''
    Defining the conditions for the transitions of the oracle automaton.
    '''
    #TODO
    def generatedCondition(self):
        return True

    #TODO
    def waitingCondition(self):
        return True

    '''
    Oracle Method to choose the next process to generate the latest block.
    Generates a token which updates all the processes with the address of the selected process.
    Once complete, the method delays before entering the waiting state again.
    '''
    #TODO
    def selectProcess(self):
        print ("Selecting Process")

'''
Process class represents the miners in a PoW blockchain network.
Their network power is depicted by their merit.
'''
class Process(Pyc.CComponent):
    def __init__(self, name):
        Pyc.CComponent.__init__(self, name)

        '''
        Declaring the list of pending blocks and known blocks.
        These are populated from the block tree.
        Pending Blocks are all the blocks that are present on the block tree but not received by the process.
        Known blocks contain the list of blocks that are received by the process.
        '''
        self.pendingBlocks = []
        self.knownBlocks = []
        '''
        Defining the variables used by the process class.
        These will be used in communication through the message boxes.
        '''
        self.v_meanTransitTime = self.addVariable("Mean Transit Time", Pyc.TVarType.t_float, 0.0)
        self.v_lastBlock = self.addVariable("Last Block", Pyc.TVarType.t_string, "0x0")
        self.v_merit = self.addVariable("Merit", Pyc.TVarType.t_int, 0)
        self.v_address = self.addVariable("Address", Pyc.TVarType.t_string, "0x0")

        '''
        Defining the variables that are referenced by the process class.
        These are imported through the message boxes connected to the class.
        '''
        self.r_appendedBlock = self.addReference("Appended Block")
        self.r_tokenHolder = self.addReference("Token Holder")
        self.r_tokenGenerated = self.addReference("Token Generated")

        '''
        Creating the message boxes that will be used to communicate with the oracle and block tree.
        Wiring the variables according to their direction in communication.
        '''
        self.addMessageBox("Oracle")
        self.addMessageBox("Blocktree")
        self.addMessageBoxImport("Oracle", self.r_tokenHolder, "Token Holder")
        self.addMessageBoxImport("Oracle", self.r_tokenGenerated, "Token Generated")
        self.addMessageBoxImport("Blocktree", self.r_appendedBlock, "Appended Block")
        self.addMessageBoxExport("Oracle", self.v_address, "Address")
        self.addMessageBoxExport("Oracle", self.v_merit, "Merit")
        self.addMessageBoxExport("Blocktree", self.v_lastBlock, "Last Block")

        '''
        Constructing the Automaton which contains the states of the process class.
        The initial state is set to working as required.
        '''
        self.processAutomaton = self.addAutomaton("Process Automaton")
        self.working = self.addState("Process Automaton", "Working", 0)
        self.claimToken = self.addState("Process Automaton", "Claim Token", 1)
        self.tokenHeld = self.addState("Process Automaton", "Token Held", 2)
        self.processAutomaton.setInitState(self.working)

        '''
        Constructing the Automaton which contains the possible states of the block objects.
        The initial state of a block is set to idle.
        '''
        self.blockAutomaton = self.addAutomaton("Block Automaton")
        self.idle = self.addState("Block Automaton", "Idle", 0)
        self.transit = self.addState("Block Automaton", "Transit", 1)
        self.arrived = self.addState("Block Automaton", "Arrived", 2)
        self.blockAutomaton.setInitState(self.idle)

        '''
        Defining the transitions between states of the process automaton.
        '''
        workingToClaim = self.working.addTransition("Working-to-Claim")
        workingToClaim.setCondition(self.tokenGeneratedCondition, True)
        workingToClaim.addTarget(self.claimToken, Pyc.TTransType.trans)

        claimToToken = self.claimToken.addTransition("Claim-to-Token")
        claimToToken.setCondition(self.holdTokenCondition, True)
        claimToToken.addTarget(self.tokenHeld, Pyc.TTransType.trans)

        claimToWorking = self.claimToken.addTransition("Claim-to-Working")
        claimToWorking.setCondition(self.holdTokenCondition, False)
        claimToWorking.addTarget(self.working, Pyc.TTransType.trans)

        tokenToWorking = self.tokenHeld.addTransition("Token-to-Working")
        tokenToWorking.setCondition(self.workingCondition, True)
        tokenToWorking.addTarget(self.working, Pyc.TTransType.trans)

        '''
        Defining the transitions between states of the block automaton
        '''
        idleToTransit = self.idle.addTransition("Idle-to-Transit")
        idleToTransit.setCondition(self.blockTransitCondition)
        idleToTransit.addTarget(self.transit, Pyc.TTransType.trans)

        transitToArrived= self.transit.addTransition("Transit-to-Arrived")
        transitToArrived.setCondition(self.blockArrivedCondition)
        transitToArrived.addTarget(self.arrived, Pyc.TTransType.trans)

        arriveToIdle = self.transit.addTransition("Arrive-to-Idle")
        arriveToIdle.setCondition(self.blockIdleCondition)
        arriveToIdle.addTarget(self.idle, Pyc.TTransType.trans)

    '''
    Defining the conditions for the transitions of the process automaton.
    '''
    def tokenGeneratedCondition(self):
        return self.r_tokenGenerated

    #TODO
    def workingCondition(self):
        return True

    #TODO
    def holdTokenCondition(self):
        return True

    '''
    Defining the conditions for the transitions of the block automaton.
    '''
    #TODO
    def blockTransitCondition(self):
        return True

    #TODO
    def blockArrivedCondition(self):
        return True

    #TODO
    def blockIdleCondition(self):
        return True

    '''
    Method adds a new pending block to the list stored by the process.
    First checks if the block is present in the list of pending/known blocks.
    '''
    #TODO
    def newPendingBlock(self):
        print("New Pending Block")

    '''
    Method simulates the reception of a new block by the process.
    This places the new block in the list of known blocks if the father is found in the list.
    '''
    #TODO
    def receiveBlock(self):
        print("Receive new block")

    '''
    Method to "mine" a token if the selected process is the token holder.
    '''
    #TODO
    def consumeToken(self):
        print("Conusuming Token")

    '''
    Method to put the process into a "working" state.
    '''
    #TODO
    def delayProcess(self):
        print("Delaying Process")

'''
Simulator class represents the implemented simulator system.
Creates and connects the various components outlined above.
'''
class Simulator(Pyc.CSystem):
    def __init__(self, name, process_count):
        Pyc.CSystem.__init__(self, name)

        '''
        Initialising system oracle and block tree.
        Only one of each is needed in all configurations of the simulator.
        '''
        self.oracle = Oracle("System Oracle")
        self.blocktree = Blocktree("Blocktree")

        '''
        Initialising the system miners or processes.
        The amount of processes varies according to the configuration of the simulator.
        '''
        self.processes = []
        for i in range(0, process_count):
            self.processes.append(Process("Process " + str(i + 1)))

            '''
            Connecting the message boxes of the system components.
            These connections facilitate the communication in the network.
            '''
            self.connect(self.oracle, "Process", self.processes[i], "Oracle")
            self.connect(self.processes[i], "Blocktree", self.blocktree, "Process")

'''
Creating an instance of the Simulator.
Configurations should be taken from the XML file in the project directory.
'''

#TODO - Script which runs the simulator.
simulator = Simulator("Simulator", 5)
print(simulator.processes[4].name())
