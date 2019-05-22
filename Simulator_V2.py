from Simulator_Utility import *

"""
Establishing the parameters to be used by the simulator.
The process count refers to the number of nodes/miners in the system.
"""
filename = "Arbitrary_Sim" + str(time.time()) + ".txt"
transit_file = "Arbitrary_Transit" + str(time.time()) + ".txt"
process_count = 1000
block_interval = [0, 0.81, 1.23]
transaction_count = [1650, 1300, 2000]
transaction_size = [0.64, 0.41, 0.75]
connection_speed = 0.08 / 6000
connection_count = 100
genesis = Block()

'''
Process class represents the miners in a PoW blockchain network.
Their network power is depicted by their merit.
'''
class Process(Pyc.CComponent):
    def __init__(self, name, address, merit, blocktree, oracle):
        Pyc.CComponent.__init__(self, name)
        self.connections = []
        self.connectedNodes = []
        self.pendingPort = 0
        self.blocktree = blocktree
        self.oracle = oracle
        self.pendingBlocks = []
        self.knownBlocks = {genesis.hash: genesis}

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

        self.addMessageBox("Inbound Connection")
        self.addMessageBox("Outbound Connection")
        self.addMessageBoxImport("Inbound Connection", self.r_appendedBlock, "Last Block")
        self.addMessageBoxExport("Outbound Connection", self.v_lastBlock, "Last Block")

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
        tr_size = generateBoundedExponential(transaction_size)
        tr_count = generateBoundedExponential(transaction_count)
        return [self.oracle.v_meanBlockTime * tr_size * tr_count, tr_size, tr_count]

    def consumeToken(self):
        properties = self.generate_block_properties()
        father = list(self.knownBlocks.values())[-1]
        author = self.v_address.value()
        block = Block(father, author, properties)
        self.knownBlocks.update({block.hash:block})
        self.v_lastBlock.setValue(block.hash)
        self.blocktree.blocks.update({block.hash: block})
        print(self.knownBlocks)

        print("Block Created:", block.hash, file=open(filename, "at"))
        print("Block Depth:", block.depth, file=open(filename, "at"))
        print("Previous Block:", father.hash, file=open(filename, "at"))
        print("Size:", str(block.size), "KB", file=open(filename, "at"))
        print("Transaction Size:", str(block.transaction_size), "KB", file=open(filename, "at"))
        print("Number of Transactions:", str(block.transaction_count), file=open(filename, "at"))
        print("Block Interval:", block.timestamp - father.timestamp, file=open(filename, "at"))
        print(file=open(filename, "at"))

    def newPendingBlock(self):
        print("Block Received", self.v_address.value())
        new_pending = self.blocktree.blocks[self.r_appendedBlock.value(self.pendingPort)]
        transit_time = np.random.exponential(connection_speed * new_pending.size)
        self.connections[self.pendingPort].newBlock(new_pending, transit_time)
        self.pendingBlocks.append(new_pending)

    def receiveBlock(self, block):
        self.knownBlocks.update({block.hash:block})
        self.pendingBlocks.remove(block)
        self.v_lastBlock.setValue(block.hash)

    def workingCondition(self):
        for connection in range(0, connection_count):
            if self.r_appendedBlock.value(connection) != self.v_lastBlock.value():
                for block in range(0, len(self.pendingBlocks)):
                    if self.pendingBlocks[block].hash is self.r_appendedBlock.value(connection):
                        return False
                for block in self.knownBlocks.keys():
                    if self.knownBlocks[block].hash is self.r_appendedBlock.value(connection):
                        return False
                self.pendingPort = connection
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
        self.arrivedToIdle.setCondition(lambda: self.currentBlock.father in parent.knownBlocks.values())
        self.arrivedToIdle.addSensitiveMethod("Receive Block", self.receiveBlock)

    def newBlock(self, new_block, transit_time):
        print(new_block.depth, "      ", np.round(transit_time, 3), file=open(transit_file, "at"))
        if self.currentBlock is None:
            self.currentBlock = new_block
            self.currentTransitTime = transit_time
        else:
            self.idleQueue.append(new_block)
            self.transitTimes.append(transit_time)

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
    def __init__(self, name):
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
    def __init__(self, name, total_merit):
        Pyc.CComponent.__init__(self, name)

        self.merits = {}
        self.transitTimes = {}
        self.last_time = time.time()
        self.total_merit = total_merit

        self.v_tokenHolder = self.addVariable("Token Holder", Pyc.TVarType.t_string, "1")
        self.v_tokenGenerated = self.addVariable("Token Generated", Pyc.TVarType.t_bool, False)
        self.v_meanBlockTime = generateBoundedExponential(block_interval)

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

    '''
    Oracle Method to choose the next process to generate the latest block.
    Generates a token and sets the token holder to the chosen process' address.
    Once complete, the last block time is set to the current time to send the oracle back into a waiting state.
    '''
    def selectProcess(self):
        choice = np.random.choice(list(self.merits.keys()), 1, p=list(self.merits.values()))
        self.v_meanBlockTime = generateBoundedExponential(block_interval)
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
    def __init__(self, name):
        Pyc.CSystem.__init__(self, name)
        self.blocktree = Blocktree("Blocktree")

        self.oracle = Oracle("System Oracle", process_count)
        self.connect(self.blocktree, "System Oracle", self.oracle, "Blocktree")
        self.processes = []

        for i in range(0, process_count):
            self.processes.append(Process("Process " + str(i + 1), str(i + 1), 1, self.blocktree, self.oracle))
            self.connect(self.oracle, "Process", self.processes[i], "Oracle")

            for j in range(0,connection_count):
                self.processes[i].connections.append(ProcessConnection("Process" + str(i) + "Connection" + str(j), self.processes[i]))

        for i in range(0, process_count):
            for j in np.random.choice([x for x in range(0, process_count) if x != i], 3, replace=False):
                self.connect(self.processes[i], "Outbound Connection", self.processes[j], "Inbound Connection")
                self.processes[i].connectedNodes.append(self.processes[j])

        self.oracle.addProcesses(self.processes)

    '''
    Functions to compute the values of the three indicators specified below:
    '''
    def consensusFunction(self):
        yesCount = 0
        counter = 0
        agree = 0
        for i in range(0, len(self.processes)):
            if list(self.processes[i].knownBlocks.values())[-1].depth == list(self.blocktree.blocks.values())[-1].depth:
                agree += 1
        if agree == len(self.processes):
            yesCount += 1
        counter += 1
        return yesCount / counter

    def consistencyFunction(self):
        agree = 0
        for i in range(0, len(self.processes)):
            if set(self.processes[i].knownBlocks.values()) == set(self.blocktree.blocks.values()):
                agree += 1
        return agree / len(self.processes)

    def delayFunction(self):
        differences = []
        for i in range(0, len(self.processes)):
            differences.append(len(self.blocktree.blocks) - len(self.processes[i].knownBlocks.values()))
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

    simulator = Simulator("Simulator")
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
    print("Ethereum Simulation Run:\n", file=open(filename, "wt"))
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
