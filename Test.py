from Util import *
import numpy as np
import hashlib

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
    def __init__(self, father = None, process = None, transactions = []):

        """
        If the block provided is not the genesis block, create the object according to parent block.
        If the block has no father, ie: is the genesis block of the blockchain, create a preset genesis block.
        """
        if father is not None:
            self.father = father
            self.timestamp = time.time()
            self.process = process
            self.depth = father.depth + 1
            self.transactions = transactions
            string_to_hash = father.hash + str(self.timestamp) + process
            hash_object = hashlib.sha256(string_to_hash.encode('utf-8'))
            self.hash = hash_object.hexdigest()
        else:
            self.depth = 0
            self.timestamp = time.time()
            self.father = None
            hash_object = hashlib.sha256(b'genesis')
            self.hash = hash_object.hexdigest()


'''
Block Tree class represent the collection of blocks in the network.
Uses depth values to identify the ordering of blocks.
'''
class Blocktree(Pyc.CComponent):
    def __init__(self, name):
        Pyc.CComponent.__init__(self, name)

        '''
        Creating the systems genesis block and dictionary of blocks.
        The dictionary maps {block hash -> block object}
        '''
        genesis = Block()
        self.blocks = {genesis.hash: genesis}

        '''
        Defining the variables and references used by the process class.
        These will be used in communication through the message boxes.
        '''
        self.v_appendedBlock = self.addVariable("Appended Block", Pyc.TVarType.t_string, "0x0")
        self.r_lastBlock = self.addReference("Last Block")

        '''
        Creating the message boxes that will be used to communicate with the processes
        Wiring the variables according to their direction in communication.
        '''
        self.addMessageBox("Process")
        self.addMessageBoxImport("Process", self.r_lastBlock, "Last Block")
        self.addMessageBoxExport("Process", self.v_appendedBlock, "Appended Block")

        '''
        Creating sensitive method that is called whenever the reference last block changes.
        '''
        self.r_lastBlock.addSensitiveMethod("Append Block", self.appendBlock)

    '''
    Adding the given block to the list of blocks held by the block tree.
    Updating the appendedBlock Variable to notify all the process of the latest block to the tree.
    '''
    def appendBlock(self):
        self.v_appendedBlock = self.v_appendedBlock.setValue(self.r_lastBlock.value(self.r_lastBlock.cnct() - 1))


'''
Oracle class represents the abstract oracle entity.
Randomly selects the next winning process based on their merit.
'''
class Oracle(Pyc.CComponent):

    def __init__(self, name, total_merit):
        Pyc.CComponent.__init__(self, name)

        '''
        Defining the system variables and references used by the process class.
        These will be used in communication through the message boxes.
        '''
        self.merits = {}
        self.last_time = time.time()
        self.total_merit = total_merit
        self.v_tokenHolder = self.addVariable("Token Holder", Pyc.TVarType.t_string, "0x0")
        self.v_meanBlockTime = self.addVariable("Mean Block Time", Pyc.TVarType.t_float, 1.0)
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
        self.waitingToGenerated.setCondition(self.generatedCondition, True)
        self.waitingToGenerated.addTarget(self.tokenGenerated)

        self.generatedToWaiting = self.tokenGenerated.addTransition("Generated-to-Waiting")
        self.generatedToWaiting.setCondition(self.generatedCondition, False)
        self.generatedToWaiting.addTarget(self.waiting)

    '''
    Creates a dictionary mapping the addresses of processes to their merit for the selection process.
    '''
    def addProcesses(self, processes):
        for i in range(0, len(processes)):
            normalised_merit = processes[i].v_merit.value() / self.total_merit
            self.merits.update({processes[i].v_address.value(): normalised_merit})

    '''
    Oracle Method to choose the next process to generate the latest block.
    Generates a token and sets the token holder to the chosen process' address.
    Once complete, the last block time is set to the current time to send the oracle back into a waiting state.
    '''
    def selectProcess(self):
        choice = np.random.choice(list(self.merits.keys()), 1, p=list(self.merits.values()))
        self.v_tokenHolder = self.v_tokenHolder.setValue(choice[0])
        self.v_tokenGenerated = self.v_tokenGenerated.setValue(True)
        self.last_time = time.time()

    '''
    The generated condition fires true iff the elapsed time since the last process selection 
    is greater than the mean block time. When the generated condition fires false the oracle
    assumes the waiting state.
    '''
    def generatedCondition(self):
        if time.time() - self.last_time > self.v_meanBlockTime.value():
            return True
        return False


'''
Process class represents the miners in a PoW blockchain network.
Their network power is depicted by their merit.
'''
class Process(Pyc.CComponent):
    def __init__(self, name, address, merit, blocktree):
        Pyc.CComponent.__init__(self, name)

        '''
        Declaring the list of pending blocks and known blocks.
        These are populated from the block tree.
        Pending Blocks are all the blocks that are present on the block tree but not received by the process.
        Known blocks contain the list of blocks that are received by the process.
        '''
        self.pendingBlocks = []
        self.knownBlocks = []
        self.blocktree = blocktree
        '''
        Defining the variables used by the process class.
        These will be used in communication through the message boxes.
        '''
        self.v_meanTransitTime = self.addVariable("Mean Transit Time", Pyc.TVarType.t_float, 0.0)
        self.v_lastBlock = self.addVariable("Last Block", Pyc.TVarType.t_string, "0x0")
        self.v_merit = self.addVariable("Merit", Pyc.TVarType.t_int, merit)
        self.v_address = self.addVariable("Address", Pyc.TVarType.t_string, address)

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
        self.blockAutomatons = []
        self.states = []
        self.transitions = []

        '''
        Defining the transitions between states of the process automaton.
        '''
        self.workingToClaim = self.working.addTransition("Working-to-Claim")
        self.workingToClaim.setCondition(self.tokenGeneratedCondition, True)
        self.workingToClaim.addTarget(self.claimToken, Pyc.TTransType.trans)

        self.claimToToken = self.claimToken.addTransition("Claim-to-Token")
        self.claimToToken.setCondition(self.holdTokenCondition, True)
        self.claimToToken.addTarget(self.tokenHeld, Pyc.TTransType.trans)

        self.claimToWorking = self.claimToken.addTransition("Claim-to-Working")
        self.claimToWorking.setCondition(self.workingCondition, True)
        self.claimToWorking.addTarget(self.working, Pyc.TTransType.trans)

        self.tokenToWorking = self.tokenHeld.addTransition("Token-to-Working")
        self.tokenToWorking.addTarget(self.working, Pyc.TTransType.trans)

        '''
        Setting the sensitive methods which are called whenever their respective transition is fired.
        '''
        self.tokenToWorking.addSensitiveMethod("Consume Token", self.consumeToken)
        self.claimToWorking.addSensitiveMethod("New Pending Block", self.newPendingBlock)

    '''
    Method to create a new automaton for a new block object.
    Automaton, states and transitions are added to their respective lists.
    '''
    def addBlockAutomaton(self, block):
        hash = block.hash
        blockAutomaton = self.addAutomaton(hash)
        idle = self.addState(hash, "Idle", 0)
        transit = self.addState(hash, "Transit", 1)
        arrived = self.addState(hash, "Arrived", 2)
        blockAutomaton.setInitState(idle)

        '''
        Defining the transitions between states of the block automaton.
        '''
        idleToTransit = idle.addTransition("Idle-to-Transit")
        idleToTransit.setCondition(self.blockTransitCondition(hash))
        idleToTransit.addTarget(transit, Pyc.TTransType.trans)

        transitToArrived = transit.addTransition("Transit-to-Arrived")
        transitToArrived.setCondition(self.blockArrivedCondition(block))
        transitToArrived.addTarget(arrived, Pyc.TTransType.trans)

        arrivedToIdle = transit.addTransition("Arrived-to-Idle")
        arrivedToIdle.setCondition(self.blockIdleCondition(block))
        arrivedToIdle.addTarget(idle, Pyc.TTransType.trans)

        arrivedToIdle.addSensitiveMethod("Receive Block", self.receiveBlock(block))

        self.blockAutomatons.append(blockAutomaton)
        self.states.append(idle)
        self.states.append(transit)
        self.states.append(arrived)
        self.transitions.append(idleToTransit)
        self.transitions.append(transitToArrived)
        self.transitions.append(arrivedToIdle)

    '''
    Defining the sensitive methods for the transitions defined above.
    Consume Token: creates a new block object, appends it to known blocks and updates last block.
    '''
    def consumeToken(self):
        father = self.knownBlocks[len(self.knownBlocks) - 1]
        author = self.v_address.value()
        block = Block(father, author, [])
        self.knownBlocks.append(block)
        self.v_lastBlock = self.v_lastBlock.setValue(block.hash)

    '''
    Adds the new pending block to the list of pending blocks.
    The block begins it's transmission from the chosen process to this process.
    '''
    def newPendingBlock(self):
        self.pendingBlocks.append(self.blocktree.blocks[self.r_appendedBlock.value(self.r_appendedBlock.cnctCount() - 1)])
        self.addBlockAutomaton(self.blocktree.blocks[self.r_appendedBlock.value(self.r_appendedBlock.cnctCount() - 1)])

    '''
    Defining the conditions for the transitions of the process automaton:
    Token Generated: if the latest reference update contains true return true.
    '''
    def tokenGeneratedCondition(self):
        return self.r_tokenGenerated.value(self.r_tokenGenerated.cnctCount() - 1)

    '''
    Hold Token: if the address of token holder is this process return true.
    '''
    def holdTokenCondition(self):
        if self.r_tokenHolder.value(self.r_tokenGenerated.cnctCount() - 1) == self.v_address:
            return True
        return False

    '''
    Working: if the appended block is updated the process returns to working state and calls newPendingBlock if
    the new pending block is not found in the list of known/pending blocks.
    '''
    def workingCondition(self):
        if self.r_appendedBlock.value(self.r_appendedBlock.cnctCount() - 1) != self.v_lastBlock:
            if self.r_appendedBlock.value(self.r_appendedBlock.cnctCount() - 1) not in self.pendingBlocks:
                if self.r_appendedBlock.value(self.r_appendedBlock.cnctCount() - 1) not in self.knownBlocks:
                    return True
        return False

    '''
    Defining the conditions for the transitions of the block automaton.
    '''
    def blockTransitCondition(self, block):
        if block in self.pendingBlocks:
            return True
        return False

    def blockArrivedCondition(self, block):
        if time.time() - block.timestamp > self.v_meanTransitTime.value():
            return True
        return False

    def blockIdleCondition(self, block):
        if block.father in self.knownBlocks:
            return True
        return False

    '''
    Method simulates the reception of a new block by the process.
    Adds the new block to the known list of blocks iff its father is in the list.
    '''
    def receiveBlock(self, block):
        self.knownBlocks.append(block)


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
        self.blocktree = Blocktree("Blocktree")
        self.oracle = Oracle("System Oracle", 15)

        '''
        Initialising the system miners or processes.
        The amount of processes varies according to the configuration of the simulator.
        '''
        self.processes = []

        for i in range(0, process_count):
            self.processes.append(Process("Process " + str(i + 1), str(i + 1), i + 1, self.blocktree))

            '''
            Connecting the message boxes of the system components.
            These connections facilitate the communication in the network.
            '''
            self.connect(self.oracle, "Process", self.processes[i], "Oracle")
            self.connect(self.processes[i], "Blocktree", self.blocktree, "Process")

        self.oracle.addProcesses(self.processes)

'''
Creating an instance of the Simulator.
Configurations should be taken from the XML file in the project directory.
'''

if __name__ == '__main__':
    try:
        simulator = Simulator("Simulator", 5)
        #simulator.loadParameters("Simulator.xml")
        beginTime = time.time()
        simulator.simulate()
        if simulator.MPIRank() > 0:
            exit(0)
        endTime = time.time()
        print ("Simulation time = %.2f s"% (endTime - beginTime))
    except Exception as e:
        print(type(e),e)

'''
Simulating the system according to the configuration specified.
Simulation data is stored for analysis.
'''