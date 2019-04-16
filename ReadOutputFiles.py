import os
import numpy as np

directory = "./100 processes/"

meanConsensus = []
meanConsistency = []
meanDelay = []

for filename in os.listdir(directory + "0.1"):
    f = open(directory + "0.1/" + filename, "r", errors='ignore', encoding='cp1252')

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanConsensus.append(float(line[:5]))

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanConsistency.append(float(line[:5]))

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanDelay.append(float(line[:5]))

    f.close()

print(round(np.mean(meanConsensus), 3))
print(round(np.mean(meanConsistency), 3))
print(round(np.mean(meanDelay), 3))
print()

meanConsensus = []
meanConsistency = []
meanDelay = []

for filename in os.listdir(directory + "0.2"):
    f = open(directory + "0.2/" + filename, "r", errors='ignore', encoding='cp1252')

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanConsensus.append(float(line[:5]))

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanConsistency.append(float(line[:5]))

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanDelay.append(float(line[:5]))

    f.close()

print(round(np.mean(meanConsensus), 3))
print(round(np.mean(meanConsistency), 3))
print(round(np.mean(meanDelay), 3))
print()
meanConsensus = []
meanConsistency = []
meanDelay = []

for filename in os.listdir(directory + "0.5"):
    f = open(directory + "0.5/" + filename, "r", errors='ignore', encoding='cp1252')

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanConsensus.append(float(line[:5]))

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanConsistency.append(float(line[:5]))

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanDelay.append(float(line[:5]))

    f.close()

print(round(np.mean(meanConsensus), 3))
print(round(np.mean(meanConsistency), 3))
print(round(np.mean(meanDelay), 3))
print()
meanConsensus = []
meanConsistency = []
meanDelay = []

for filename in os.listdir(directory + "0.7"):
    f = open(directory + "0.7/" + filename, "r", errors='ignore', encoding='cp1252')

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanConsensus.append(float(line[:5]))

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanConsistency.append(float(line[:5]))

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanDelay.append(float(line[:5]))

    f.close()

print(round(np.mean(meanConsensus), 3))
print(round(np.mean(meanConsistency), 3))
print(round(np.mean(meanDelay), 3))
print()
meanConsensus = []
meanConsistency = []
meanDelay = []

for filename in os.listdir(directory + "0.99"):
    f = open(directory + "0.99/" + filename, "r", errors='ignore', encoding='cp1252')

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanConsensus.append(float(line[:5]))

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanConsistency.append(float(line[:5]))

    line = f.readline()
    if any(char.isdigit() for char in line[:5]):
        meanDelay.append(float(line[:5]))

    f.close()

print(round(np.mean(meanConsensus), 3))
print(round(np.mean(meanConsistency), 3))
print(round(np.mean(meanDelay), 3))