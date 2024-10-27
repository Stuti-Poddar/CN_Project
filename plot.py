import threading
import time
import random
import matplotlib.pyplot as plt

NUM_VEHICLES = 5
TIME_STEP = 1     
SIMULATION_TIME = 20  

time_data = []
throughput_data = [[] for _ in range(NUM_VEHICLES)]  
heartbeat_delivery_data = [[] for _ in range(NUM_VEHICLES)]  
error_correction_data = [[] for _ in range(NUM_VEHICLES)]  
packet_loss_data = [[] for _ in range(NUM_VEHICLES)]  
latency_data = [[] for _ in range(NUM_VEHICLES)]  # New latency data
metrics_lock = threading.Lock()

class Vehicle(threading.Thread):
    def __init__(self, vehicle_id):
        super().__init__()
        self.vehicle_id = vehicle_id
        self.running = True
        self.heartbeat_count = 0
        self.heartbeat_received = 0
        self.errors_detected = 0
        self.errors_corrected = 0
        self.base_throughput = random.randint(5, 10)
        self.packet_loss_count = 0  
    def run(self):
        while self.running:
            self.send_heartbeat()

            with metrics_lock:
                fluctuation = random.randint(-2, 2) 
                self.heartbeat_count += self.base_throughput + fluctuation
                throughput_data[self.vehicle_id].append(max(self.heartbeat_count, 0))

                heartbeat_delivery_ratio = (self.heartbeat_received / (self.heartbeat_count + 1e-6))
                heartbeat_delivery_data[self.vehicle_id].append(heartbeat_delivery_ratio)

                error_correction_ratio = (self.errors_corrected / (self.errors_detected + 1e-6))
                error_correction_data[self.vehicle_id].append(error_correction_ratio)

                dropped_messages = self.heartbeat_count - self.heartbeat_received
                self.packet_loss_count += dropped_messages
                packet_loss_ratio = self.packet_loss_count / (self.heartbeat_count + 1e-6) 
                packet_loss_data[self.vehicle_id].append(packet_loss_ratio)

                # Simulate latency as a random value influenced by throughput
                latency = random.uniform(0.1, 0.5) + (1.0 / (self.base_throughput + 1e-6))  # More throughput = less latency
                latency_data[self.vehicle_id].append(latency)

                current_time = len(throughput_data[self.vehicle_id]) * TIME_STEP
                if not time_data or current_time > time_data[-1]:
                    time_data.append(current_time)

            time.sleep(TIME_STEP)

    def send_heartbeat(self):
        """ Simulate sending a heartbeat with a chance of error. """
        self.heartbeat_count += 1
        if random.random() < 0.9:  
            self.heartbeat_received += 1
            
            if random.random() < 0.1: 
                self.errors_detected += 1
                if random.random() < 0.5:
                    self.errors_corrected += 1

    def stop(self):
        self.running = False

def run_simulation():
    """ Main simulation function to start the vehicles. """
    global vehicles
    vehicles = [Vehicle(vehicle_id=i) for i in range(NUM_VEHICLES)]

    for vehicle in vehicles:
        vehicle.start()

    time.sleep(SIMULATION_TIME)

    for vehicle in vehicles:
        vehicle.stop()
    for vehicle in vehicles:
        vehicle.join()

    plt.figure(figsize=(12, 12))

    # 1. Throughput vs Time
    plt.subplot(3, 2, 1)
    for i in range(NUM_VEHICLES):
        plt.plot(time_data, throughput_data[i], label=f'Vehicle {i}', marker='') 
    plt.xlabel('Time (s)')
    plt.ylabel('Throughput (Heartbeat Count)')
    plt.title('Throughput vs Time')
    plt.xlim(0, SIMULATION_TIME)
    plt.legend()
    plt.grid()

    # 2. Heartbeat Reception Ratio vs Time
    plt.subplot(3, 2, 2)
    for i in range(NUM_VEHICLES):
        plt.plot(time_data, heartbeat_delivery_data[i], label=f'Vehicle {i}', marker='')  
    plt.xlabel('Time (s)')
    plt.ylabel('Reception Ratio')
    plt.title('Heartbeat Reception Ratio vs Time')
    plt.xlim(0, SIMULATION_TIME)
    plt.legend()
    plt.grid()

    # 3. Error Correction Ratio vs Time
    plt.subplot(3, 2, 3)
    for i in range(NUM_VEHICLES):
        plt.plot(time_data, error_correction_data[i], label=f'Vehicle {i}', marker='')  
    plt.xlabel('Time (s)')
    plt.ylabel('Correction Ratio')
    plt.title('Error Correction Ratio vs Time')
    plt.xlim(0, SIMULATION_TIME)
    plt.legend()
    plt.grid()

    # 4. Packet delivery vs Number of Messages Sent
    plt.subplot(3, 2, 4)
    for i in range(NUM_VEHICLES):
        plt.plot(range(1, len(packet_loss_data[i]) + 1), packet_loss_data[i], label=f'Vehicle {i}', marker='')  
    plt.xlabel('Number of Messages Sent')
    plt.ylabel('Packet Delivery Ratio')
    plt.title('Packet Delivery vs Number of Messages Sent')
    plt.xlim(0, SIMULATION_TIME)
    plt.xticks(range(0, 11, 2))  
    plt.legend()
    plt.grid()

    # 5. Latency vs Time
    plt.subplot(3, 2, 5)
    for i in range(NUM_VEHICLES):
        plt.plot(time_data, latency_data[i], label=f'Vehicle {i}', marker='')  
    plt.xlabel('Time (s)')
    plt.ylabel('Latency (s)')
    plt.title('Heartbeat Latency vs Time')
    plt.xlim(0, SIMULATION_TIME)
    plt.legend()
    plt.grid()

    plt.tight_layout()  
    plt.show()

run_simulation()
