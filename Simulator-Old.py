from Simulator_Utility import *

"""
Establishing the properties of the network.
The process count refers to the number of nodes/miners in the system.
Connection count refers to the number of automaton assigned to each connection to schedule block arrivals.
"""
process_count = 100
connection_count = 3
block_interval  = 1
transit_time = 0.99
transaction_count = [1650, 1300, 2000]
transaction_size = [0.64, 0.41, 0.75]
connection_speed = 0.027 / 600
genesis = Block()

filename = "./Arbitrary Runs/" + str(process_count) + " processes/" + str(transit_time) + "/Simulation_Bounded_" + str(time.time()) + ".txt"
transit_file = "Simulation_Transit_" + str(time.time()) + ".txt"

intervals = []
transits = []

'''
Process class represents the miners in a PoW blockchain network.
Their network power is depicted by their merit.
'''
class Process(Pyc.CComponent):
    def __init__(self, name, address, merit, blocktree, genesis, oracle):
        Pyc.CComponent.__init__(self, name)
        self.connections = []
        self.blocktree = blocktree
        self.oracle = oracle
        self.pendingBlocks = []
        self.knownBlocks = [genesis]
        self.leadingBlock = genesis

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
        tr_size = generateBoundedExponential(transaction_size)
        tr_count = generateBoundedExponential(transaction_count)
        size = [tr_size * (tr_count), tr_size, tr_count]
        return size

    def consumeToken(self):
        properties = self.generate_block_properties()
        father = self.leadingBlock
        author = self.v_address.value()
        block = Block(father, author, properties)
        self.leadingBlock = block
        self.knownBlocks.append(block)
        self.blocktree.updateBlocktree(block)

        '''
        printLine("\nBlock Created: " + block.hash, filename)
        printLine("Block Depth:" + str(block.depth), filename)
        printLine("Previous Block: " + father.hash, filename)
        printLine("Size: " + str(block.size) + "KB", filename)
        printLine("Transaction Size: " + str(block.transaction_size) + "KB", filename)
        printLine("Number of Transactions:" + str(block.transaction_count), filename)
        printLine("Block Interval:" + str(block.timestamp - father.timestamp), filename)
        '''

    def newPendingBlock(self):
        new_pending = self.blocktree.blocks[self.r_appendedBlock.value(0)]
        #meanTransitTime = np.random.exponential(self.v_connectionSpeed.value() * new_pending.size)
        meanTransitTime = np.random.exponential(transit_time)
        transits.append(meanTransitTime)
        #print(new_pending.depth, "      ", np.round(meanTransitTime, 3), file=open(transit_file, "at"))
        self.pendingBlocks.append(new_pending)
        for connection in self.connections:
            if connection.currentBlock is None:
                connection.currentBlock = new_pending
                connection.currentTransitTime = meanTransitTime
                return
        smallest = 0
        for connection in self.connections:
            if smallest is 0:
                smallest = connection
            elif len(connection.idleQueue) < len(smallest.idleQueue):
                smallest = connection
        smallest.idleQueue.append(new_pending)
        smallest.transitTimes.append(meanTransitTime)

    def receiveBlock(self, block):
        if block.depth > self.knownBlocks[-1].depth:
            self.leadingBlock = block
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
    def __init__(self, name):
        Pyc.CComponent.__init__(self, name)
        self.blocks = {genesis.hash: genesis}
        self.discarded_blocks = {}

        self.v_appendedBlock = self.addVariable("Appended Block", Pyc.TVarType.t_string, genesis.hash)
        self.r_lastBlock = self.addReference("Last Block")
        self.r_selection = self.addReference("Selected Process")

        self.addMessageBox("Process")
        self.addMessageBoxImport("Process", self.r_lastBlock, "Last Block")
        self.addMessageBoxExport("Process", self.v_appendedBlock, "Appended Block")

        self.addMessageBox("System Oracle")
        self.addMessageBoxImport("System Oracle", self.r_selection, "Token Holder")

    def updateBlocktree(self, block):
        if block.depth > list(self.blocks.values())[-1].depth:
            intervals.append(block.timestamp - list(self.blocks.values())[-1].timestamp)
            self.blocks.update({block.hash: block})
            self.v_appendedBlock.setValue(block.hash)
            print("[Block Accepted]: Creator ID:", block.process, "at depth:", block.depth)
        elif block.father == list(self.blocks.values())[-1].father and block.depth == list(self.blocks.values())[-1].depth :
            self.blocks.update({block.hash: block})
            self.v_appendedBlock.setValue(block.hash)
            print("[BLOCKCHAIN SPLIT]: Creator ID:", block.process, "at depth:", block.depth)
        else:
            print("[BLOCK REJECTED]: Creator Address:", block.process, "at depth:", block.depth)
            self.discarded_blocks.update({block.hash: block})



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
        self.v_meanBlockTime = np.random.exponential(block_interval)

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
        self.v_meanBlockTime = np.random.exponential(block_interval)
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

        merits = [1] * process_count

        self.oracle = Oracle("System Oracle", sum(merits))
        self.connect(self.blocktree, "System Oracle", self.oracle, "Blocktree")
        self.processes = []

        for i in range(0, process_count):
            self.processes.append(Process("Process " + str(i + 1), str(i + 1), merits[i], self.blocktree, genesis, self.oracle))
            self.connect(self.oracle, "Process", self.processes[i], "Oracle")
            self.connect(self.processes[i], "Blocktree", self.blocktree, "Process")
            for j in range(0, connection_count):
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
            if self.processes[i].knownBlocks[-1].depth == list(self.blocktree.blocks.values())[-1].depth:
                agree += 1
        if agree == len(self.processes):
            yesCount += 1
        counter += 1
        return yesCount / counter

    def consistencyFunction(self):
        agree = 0
        for i in range(0, len(self.processes)):
            if self.processes[i].knownBlocks[-1].depth == list(self.blocktree.blocks.values())[-1].depth:
                agree += 1
        return agree / len(self.processes)

    def delayFunction(self):
        differences = []
        for i in range(0, len(self.processes)):
            lastBlock = self.processes[i].knownBlocks[-1]
            differences.append(list(self.blocktree.blocks.values())[-1].depth - lastBlock.depth)
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
    #printLine("Bitcoin Simulation Run:\n", filename)
    startTime = time.time()

    if simulator.MPIRank() > 0:
        exit(0)

    simulator.simulate()
    endTime = time.time()
    timeTaken = endTime - startTime

    meanConsensus = list(consensusProbability.means())[0]
    meanConsistency = list(consistencyRate.means())[0]
    meanDelay = list(worstDelay.means())[0]
    blockSize = simulator.blockSizeCalculator()

    '''printLine(str(round(meanConsensus,3)), filename)
    printLine(str(round(meanConsistency, 3)), filename)
    printLine(str(round(meanDelay, 3)), filename)
    printLine(str(round(staleBlocks / len(simulator.blocktree.blocks.values()), 3)), filename)

    print("Time taken: " + str(round(timeTaken, 3)) + " seconds.\n")'''

    printLine("Time taken: " + str(round(timeTaken, 3)) + " seconds.\n", filename)
    printLine("Network Parameters:", filename)
    printLine("Number of Nodes: " + str(process_count), filename)
    printLine("Number of Connections/Node: " + str(connection_count), filename)
    printLine("Block Interval: " + str(np.mean(intervals)), filename)
    printLine("Block Transit: " + str(np.mean(transits)), filename)

    printLine("\nIndicators:",filename)
    printLine("Mean Consensus Probability: " + str(round(meanConsensus,3)),filename)
    printLine("Mean Consistency: " + str(round(meanConsistency, 3)),filename)
    printLine("Worst Process Delay: " + str(round(meanDelay, 3)), filename)
    printLine("Block Size: " +  str(round(blockSize[0], 3)) + "KB", filename)
    printLine("Transaction Size: " + str(round(blockSize[2], 3)) + "KB", filename)
    printLine("Transaction Count: " + str(round(blockSize[1], 3)) , filename)

    printLine("\nBlock Statistics:",filename)
    printLine("Total # of Blocks: " + str(len(simulator.blocktree.blocks.values()) + len(simulator.blocktree.discarded_blocks)), filename)
    printLine("# of Valid Blocks: " + str(list(simulator.blocktree.blocks.values())[-1].depth), filename)
    printLine("# of Orphaned Blocks: " + str(len(simulator.blocktree.blocks.values()) - list(simulator.blocktree.blocks.values())[-1].depth), filename)
    printLine("# of Invalid Blocks: " + str(len(simulator.blocktree.discarded_blocks)), filename)
