from Util import *
import numpy as np
import hashlib

filename = "Bitcoin_Sim_" + str(time.time()) + ".txt"
transit_file = "Bitcoin_Transit_" + str(time.time()) + ".txt"
'''
Function to generate a random number from an exponential distribution,
contained within an upper and lower bound.
'''
def generateBoundedExponential(values):
    while True:
        value = np.random.exponential(values[0])
        if values[1] < value < values[2]:
            return value

'''
Block (pure python) class represents a collection of on-chain transactions.
'''
class Block:
    def __init__(self, father = None, process = None, size = None, transaction_size = None, transaction_count = None):

        """
        If the block provided is not the genesis block, create the object according to parent block.
        If the block has no father, ie: is the genesis block of the blockchain, create a preset genesis block.
        """
        if father is not None:
            self.size = size
            self.transaction_size = transaction_size
            self.transaction_count = transaction_count
            self.father = father
            self.timestamp = time.time()
            self.process = process
            self.depth = father.depth + 1
            string_to_hash = father.hash + str(self.timestamp) + process + str(size) + str(transaction_count) + str(transaction_size)
            hash_object = hashlib.sha256(string_to_hash.encode('utf-8'))
            self.hash = hash_object.hexdigest()
        else:
            self.depth = 0
            self.size = 1024
            self.transaction_count = 1650
            self.transaction_size = 0.64
            self.timestamp = time.time()
            self.father = None
            hash_object = hashlib.sha256(b'genesis')
            self.hash = hash_object.hexdigest()

'''
Process class represents the miners in a PoW blockchain network.
Their network power is depicted by their merit.
'''
class Process(Pyc.CComponent):
    def __init__(self, name, address, merit, blocktree, genesis, oracle, transaction_count, transaction_size, connection_speed):
        Pyc.CComponent.__init__(self, name)
        self.connections = []
        self.blocktree = blocktree
        self.oracle = oracle
        self.pendingBlocks = []
        self.knownBlocks = [genesis]
        self.transaction_count = transaction_count
        self.transaction_size = transaction_size

        self.v_connectionSpeed = self.addVariable("Mean Transit Time", Pyc.TVarType.t_float, connection_speed)
        self.v_lastBlock = self.addVariable("Last Block", Pyc.TVarType.t_string, genesis.hash)
        self.v_merit = self.addVariable("Merit", Pyc.TVarType.t_int, merit)
        self.v_address = self.addVariable("Address", Pyc.TVarType.t_string, address)

        self.r_appendedBlock = self.addReference("Appended Block")
        self.r_tokenHolder = self.addReference("Token Holder")
        self.r_tokenGenerated = self.addReference("Token Generated")
        self.r_meanTransitTimes = self.addReference("Mean Transit Times")

        self.addMessageBox("Oracle")
        self.addMessageBoxImport("Oracle", self.r_tokenHolder, "Token Holder")
        self.addMessageBoxImport("Oracle", self.r_tokenGenerated, "Token Generated")
        self.addMessageBoxExport("Oracle", self.v_address, "Address")
        self.addMessageBoxExport("Oracle", self.v_merit, "Merit")

        self.addMessageBox("Blocktree")
        self.addMessageBoxImport("Blocktree", self.r_appendedBlock, "Appended Block")
        self.addMessageBoxExport("Blocktree", self.v_lastBlock, "Last Block")

        self.processAutomaton = self.addAutomaton("Process Automaton")
        self.working = self.addState("Process Automaton", "Working", 0)
        self.claimToken = self.addState("Process Automaton", "Claim Token", 1)
        self.tokenHeld = self.addState("Process Automaton", "Token Held", 2)
        self.processAutomaton.setInitState(self.working)

        self.workingToClaim = self.working.addTransition("Working-to-Claim")
        self.workingToClaim.setCondition(lambda: self.r_tokenGenerated.value(0))
        self.workingToClaim.addTarget(self.claimToken, Pyc.TTransType.trans)

        self.claimToToken = self.claimToken.addTransition("Claim-to-Token")
        self.claimToToken.setCondition(lambda: self.r_tokenHolder.value(0) == self.v_address.value() and not self.r_tokenGenerated.value(0))
        self.claimToToken.addTarget(self.tokenHeld, Pyc.TTransType.trans)

        self.claimToWorking = self.claimToken.addTransition("Claim-to-Working")
        self.claimToWorking.setCondition(self.workingCondition)
        self.claimToWorking.addTarget(self.working, Pyc.TTransType.trans)

        self.tokenToWorking = self.tokenHeld.addTransition("Token-to-Working")
        self.tokenToWorking.addTarget(self.working, Pyc.TTransType.trans)

        self.tokenToWorking.addSensitiveMethod("Consume Token", self.consumeToken)
        self.claimToWorking.addSensitiveMethod("New Pending Block", self.newPendingBlock)

    def generate_block_properties(self):
        transaction_size = generateBoundedExponential(self.transaction_size)
        transaction_count = generateBoundedExponential(self.transaction_count)
        size = [self.oracle.v_meanBlockTime * transaction_size * (transaction_count), transaction_size, transaction_count]
        return size

    def consumeToken(self):
        properties = self.generate_block_properties()
        father = self.knownBlocks[len(self.knownBlocks) - 1]
        author = self.v_address.value()
        block = Block(father, author, properties[0], properties[1], properties[2])
        self.knownBlocks.append(block)
        self.v_lastBlock.setValue(block.hash)
        self.blocktree.blocks.update({block.hash: block})

        print("Block Created:", block.hash, file=open(filename, "at"))
        print("Block Depth:", block.depth, file=open(filename, "at"))
        print("Previous Block:", father.hash, file=open(filename, "at"))
        print("Size:", str(block.size), "KB", file=open(filename, "at"))
        print("Transaction Size:", str(block.transaction_size), "KB", file=open(filename, "at"))
        print("Number of Transactions:", str(block.transaction_count), file=open(filename, "at"))
        print("Block Interval:", block.timestamp - father.timestamp, file=open(filename, "at"))
        print(file=open(filename, "at"))

    def newPendingBlock(self):
        new_pending = self.blocktree.blocks[self.r_appendedBlock.value(0)]
        meanTransitTime = np.random.exponential(self.v_connectionSpeed.value() * new_pending.size)
        print(new_pending.depth, "      ", np.round(meanTransitTime, 3), file=open(transit_file, "at"))
        self.pendingBlocks.append(new_pending)
        for connection in self.connections:
            if connection.currentBlock is None:
                connection.currentBlock = new_pending
                connection.currentTransitTime = meanTransitTime
                return
        for connection in self.connections:
            if len(connection.idleQueue) == 0:
                connection.currentBlock = new_pending
                connection.currentTransitTime = meanTransitTime
                return
        for connection in self.connections:
            if smallest is 0:
                smallest = connection
            elif len(connection.idleQueue) < len(self.connections[smallest]):
                smallest = connection
        smallest.idleQueue.append(new_pending)
        smallest.transitTimes.append(meanTransitTime)

    def receiveBlock(self, block):
        self.knownBlocks.append(block)
        self.pendingBlocks.remove(block)

    def workingCondition(self):
        if self.r_appendedBlock.value(0) != self.v_lastBlock.value():
            for i in range(0, len(self.pendingBlocks)):
                if self.pendingBlocks[i].hash is self.r_appendedBlock.value(0):
                    return False
            for i in range(0, len(self.knownBlocks)):
                if self.knownBlocks[i].hash is self.r_appendedBlock.value(0):
                    return False
            return True
        return False


class ProcessConnection(Pyc.CComponent):
    def __init__(self, name, parent):
        Pyc.CComponent.__init__(self, name)

        self.parent = parent
        self.idleQueue = []
        self.transitTimes = []
        self.currentBlock = None
        self.currentTransitTime = 0

        self.connectionAutomaton = self.addAutomaton("Connection")
        self.idle = self.connectionAutomaton.addState("Idle", 0)
        self.transit = self.connectionAutomaton.addState("Transit", 1)
        self.arrived = self.connectionAutomaton.addState("Arrived", 2)
        self.connectionAutomaton.setInitState(self.idle)

        self.idleToTransit = self.idle.addTransition("Idle-to-Transit")
        self.idleToTransit.addTarget(self.transit, Pyc.TTransType.trans)
        self.idleToTransit.setCondition(lambda: self.currentBlock in parent.pendingBlocks)

        self.transitToArrived = self.transit.addTransition("Transit-to-Arrived")
        self.transitToArrived.addTarget(self.arrived, Pyc.TTransType.trans)
        self.transitToArrived.setCondition(lambda: time.time() - self.currentBlock.timestamp > self.currentTransitTime)

        self.arrivedToIdle = self.arrived.addTransition("Arrived-to-Idle")
        self.arrivedToIdle.addTarget(self.idle, Pyc.TTransType.trans)
        self.arrivedToIdle.setCondition(lambda: self.currentBlock.father in parent.knownBlocks)

        self.arrivedToIdle.addSensitiveMethod("Receive Block", self.receiveBlock)

    def receiveBlock(self):
        self.parent.receiveBlock(self.currentBlock)
        if len(self.idleQueue) > 0:
            self.currentBlock = self.idleQueue.pop(0)
            self.currentTransitTime = self.transitTimes.pop(0)
        else:
            self.currentBlock = None
            self.currentTransitTime = None


'''
Block Tree class represent the collection of blocks in the network.
Uses depth values to identify the ordering of blocks.
'''
class Blocktree(Pyc.CComponent):
    def __init__(self, name, genesis):
        Pyc.CComponent.__init__(self, name)
        self.blocks = {genesis.hash: genesis}

        self.v_appendedBlock = self.addVariable("Appended Block", Pyc.TVarType.t_string, genesis.hash)
        self.r_lastBlock = self.addReference("Last Block")
        self.r_selection = self.addReference("Selected Process")

        self.addMessageBox("Process")
        self.addMessageBoxImport("Process", self.r_lastBlock, "Last Block")
        self.addMessageBoxExport("Process", self.v_appendedBlock, "Appended Block")

        self.addMessageBox("System Oracle")
        self.addMessageBoxImport("System Oracle", self.r_selection, "Token Holder")

        self.r_lastBlock.addSensitiveMethod("Append Block", self.appendBlock)

    def appendBlock(self):
        self.v_appendedBlock.setValue(self.r_lastBlock.value(int(self.r_selection.value(0)) - 1))


'''
Oracle class represents the abstract oracle entity.
Randomly selects the next winning process based on their merit.
'''
class Oracle(Pyc.CComponent):

    def __init__(self, name, total_merit, blockInterval):
        Pyc.CComponent.__init__(self, name)

        self.merits = {}
        self.transitTimes = {}
        self.last_time = time.time()
        self.total_merit = total_merit

        self.blockInterval = blockInterval

        self.v_tokenHolder = self.addVariable("Token Holder", Pyc.TVarType.t_string, "1")
        self.v_tokenGenerated = self.addVariable("Token Generated", Pyc.TVarType.t_bool, False)
        self.v_meanBlockTime = generateBoundedExponential(self.blockInterval)

        self.addMessageBox("Process")
        self.addMessageBoxExport("Process", self.v_tokenHolder, "Token Holder")
        self.addMessageBoxExport("Process", self.v_tokenGenerated, "Token Generated")

        self.addMessageBox("Blocktree")
        self.addMessageBoxExport("Blocktree", self.v_tokenHolder, "Token Holder")

        self.processAutomaton = self.addAutomaton("Oracle Automaton")
        self.waiting = self.addState("Oracle Automaton", "Waiting", 0)
        self.tokenGenerated = self.addState("Oracle Automaton", "Token Generated", 1)
        self.processAutomaton.setInitState(self.waiting)

        self.waitingToGenerated = self.waiting.addTransition("Waiting-to-Generated")
        self.waitingToGenerated.setCondition(lambda: time.time() - self.last_time > self.v_meanBlockTime and not self.v_tokenGenerated.value())
        self.waitingToGenerated.addTarget(self.tokenGenerated)

        self.generatedToWaiting = self.tokenGenerated.addTransition("Generated-to-Waiting")
        self.generatedToWaiting.addTarget(self.waiting)

        self.waitingToGenerated.addSensitiveMethod("Generate Token", self.generate, 0)
        self.generatedToWaiting.addSensitiveMethod("Select Process", self.selectProcess, 0)


    def addProcesses(self, processes):
        for i in range(0, len(processes)):
            normalised_merit = processes[i].v_merit.value() / self.total_merit
            self.merits.update({processes[i].v_address.value(): normalised_merit})
            self.transitTimes.update({processes[i].v_address.value(): processes[i].v_connectionSpeed.value()})

    '''
    Oracle Method to choose the next process to generate the latest block.
    Generates a token and sets the token holder to the chosen process' address.
    Once complete, the last block time is set to the current time to send the oracle back into a waiting state.
    '''
    def selectProcess(self):
        choice = np.random.choice(list(self.merits.keys()), 1, p=list(self.merits.values()))
        self.v_meanBlockTime = generateBoundedExponential(self.blockInterval)
        self.v_tokenHolder.setValue(choice[0])
        self.v_tokenGenerated.setValue(False)
        self.last_time = time.time()

    def generate(self):
        self.v_tokenGenerated.setValue(True)

'''
Simulator class represents the implemented simulator system.
Creates and connects the various components outlined above.
'''
class Simulator(Pyc.CSystem):
    def __init__(self, name, process_count, transaction_count, transaction_size, connection_speed, blockInterval):
        Pyc.CSystem.__init__(self, name)

        genesis = Block()
        self.blocktree = Blocktree("Blocktree", genesis)

        merits = []
        for i in range(0, process_count):
            merits.append(np.random.randint(1,10))

        self.oracle = Oracle("System Oracle", sum(merits), blockInterval)
        self.connect(self.blocktree, "System Oracle", self.oracle, "Blocktree")
        self.processes = []

        for i in range(0, process_count):
            self.processes.append(Process("Process " + str(i + 1), str(i + 1), merits[i], self.blocktree, genesis, self.oracle, transaction_count, transaction_size, connection_speed))
            self.connect(self.oracle, "Process", self.processes[i], "Oracle")
            self.connect(self.processes[i], "Blocktree", self.blocktree, "Process")
            for j in range(0, 5):
                self.processes[i].connections.append(ProcessConnection("Process" + str(i) + "Connection" + str(j), self.processes[i]))

        self.oracle.addProcesses(self.processes)

    '''
    Functions to compute the values of the three indicators specified below:
    '''
    def consensusFunction(self):
        yesCount = 0
        counter = 0
        agree = 0
        for i in range(0, len(self.processes)):
            if set(self.processes[i].knownBlocks) == set(self.blocktree.blocks.values()):
                agree += 1
        if agree == len(self.processes):
            yesCount += 1
        counter += 1
        return yesCount / counter

    def consistencyFunction(self):
        agree = 0
        for i in range(0, len(self.processes)):
            if set(self.processes[i].knownBlocks) == set(self.blocktree.blocks.values()):
                agree += 1
        return agree / len(self.processes)

    def delayFunction(self):
        differences = []
        for i in range(0, len(self.processes)):
            differences.append(len(self.blocktree.blocks) - len(self.processes[i].knownBlocks))
        return max(differences)

    def blockSizeCalculator(self):
        block_size = 0
        counts = 0
        transaction_size = 0
        for i in self.blocktree.blocks.keys():
            block_size += self.blocktree.blocks[i].size
            counts += self.blocktree.blocks[i].transaction_count
            transaction_size += self.blocktree.blocks[i].transaction_size
        return [block_size / len(self.blocktree.blocks), counts / len(self.blocktree.blocks), transaction_size / len(self.blocktree.blocks)]


if __name__ == '__main__':

    """
    Establishing the parameters to be used by the simulator.
    The process count refers to the number of nodes/miners in the system.
    """
    process_count = 100
    block_interval = [0.98, 0.81, 1.23]
    transaction_count = [1650, 1300, 2000]
    transaction_size = [0.64, 0.41, 0.75]
    connection_speed = 0.08/30

    simulator = Simulator("Simulator", process_count, transaction_count, transaction_size, connection_speed, block_interval)
    simulator.loadParameters("Simulator.xml")
    simulator.addInstants(0, simulator.tMax(), 60)
    """
    Defining the system indicators used to quantify the performance of the model.
    1) Consensus Probability - The probability that all miners agree on the absolute blockchain
    2) Consistency Rate - The proportion of miners which agree on the absolute blockchain
    3) Worst Process Delay - The average difference between the absolute chain and the most delayed process
    """
    consensusProbability = simulator.addIndicator("Consensus Probability", simulator.consensusFunction)
    consensusProbability.setRestitutions(Pyc.TIndicatorType.mean_values)
    consistencyRate = simulator.addIndicator("Consistency Rate", simulator.consistencyFunction)
    consistencyRate.setRestitutions(Pyc.TIndicatorType.mean_values)
    worstDelay = simulator.addIndicator("Worst Delay", simulator.delayFunction)
    worstDelay.setRestitutions(Pyc.TIndicatorType.mean_values)

    """
    Running the simulation, recording its execution time and the results of the indicators.
    The result of the simulation is dumped into a text file with the current timestamp.
    """
    print("Bitcoin Simulation Run:\n", file=open(filename, "wt"))
    startTime = time.time()
    simulator.simulate()
    endTime = time.time()
    timeTaken = endTime - startTime

    meanConsensus = list(consensusProbability.means())[0]
    meanConsistency = list(consistencyRate.means())[0]
    meanDelay = list(worstDelay.means())[0]
    blockSize = simulator.blockSizeCalculator()

    print("Time taken:", round(timeTaken, 3), "seconds.\n", file=open(filename, "at"))
    print("Network Parameters:", file=open(filename, "at"))
    print("Number of Nodes:", process_count, file=open(filename, "at"))
    print(file=open(filename, "at"))
    print("\nIndicators:", file=open(filename, "at"))

    print("Mean Consensus Probability:", round(meanConsensus,3), file=open(filename, "at"))
    print("Mean Consistency:", round(meanConsistency, 3), file=open(filename, "at"))
    print("Worst Process Delay:", round(meanDelay, 3), file=open(filename, "at"))
    print("Block Size:", round(blockSize[0], 3), "KB", file=open(filename, "at"))
    print("Transaction Size:", round(blockSize[2], 3), "KB", file=open(filename, "at"))
    print("Transaction Count:", round(blockSize[1], 3), file=open(filename, "at"))
