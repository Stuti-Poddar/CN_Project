import threading
import queue
import time
import random
import matplotlib.pyplot as plt

SINGLE_BIT = 1
DOUBLE_BIT = 2
BURST = 3

MAX_SPEED = 120  

time_data = []
speed_data = {}
position_data = {}
error_data = {SINGLE_BIT: [], DOUBLE_BIT: [], BURST: []}
resync_time_data = {}
cwnd_data = {}
metrics_lock = threading.Lock()

def int_to_binary_string(n, bits=8):
    """ Convert integer to binary string representation """
    return f"{n:0{bits}b}"

class AgedPriorityQueue(queue.PriorityQueue):
    """ Custom priority queue that ages entries to prevent starvation """
    
    def __init__(self, maxsize=0):
        super().__init__(maxsize)
        self.age_factor = 1  

    def put(self, item, block=True, timeout=None):
        priority, heartbeat = item
        age_adjusted_priority = max(1, priority - self.age_factor)
        super().put((age_adjusted_priority, heartbeat), block, timeout)

    def increase_age(self):
        """ Function to increase the aging factor over time """
        self.age_factor += 1

class Vehicle(threading.Thread):
    def __init__(self, vehicle_id, heartbeat_queue, congestion_queue, max_window_size=5):
        super().__init__()
        self.vehicle_id = vehicle_id
        self.heartbeat_queue = heartbeat_queue
        self.congestion_queue = congestion_queue
        self.cwnd = 1
        self.ssthresh = max_window_size // 2
        self.max_window_size = max_window_size
        self.position = 0
        self.speed = random.uniform(40, 60)  
        self.synchronized = False
        self.running = True
        self.obstacle_detected = False
        self.direction = random.choice(["straight", "left", "right"])  
        self.leader = None
        speed_data[self.vehicle_id] = []
        position_data[self.vehicle_id] = []
        error_data[SINGLE_BIT].append(0)
        error_data[DOUBLE_BIT].append(0)
        error_data[BURST].append(0)
        resync_time_data[self.vehicle_id] = []
        cwnd_data[self.vehicle_id] = []

    def run(self):
        while self.running:
            time_step = time.time()
            if self.obstacle_detected:
                self.handle_obstacle()
                continue
            
            if self.wants_to_turn():
                self.assign_leader()

            try:
                priority, heartbeat = self.heartbeat_queue.get(timeout=1)
                print(f"Vehicle {self.vehicle_id} received priority {priority} heartbeat: {heartbeat['binary_message']}")

                if self.process_heartbeat(heartbeat):
                    print(f"Vehicle {self.vehicle_id}: Corrected heartbeat: {heartbeat['binary_message']}")

            except queue.Empty:
                print(f"Vehicle {self.vehicle_id}: No heartbeat received. Trying to resynchronize.")
                self.adjust_speed()

            self.handle_intersection()

            self.log_metrics(time_step)

            self.detect_obstacle() 
            time.sleep(1)

    def stop(self):
        """ Stop the vehicle thread. """
        self.running = False

    def wants_to_turn(self):
        """ Determine if the vehicle wants to turn (right or left) """
        return random.choice([True, False])  

    def assign_leader(self):
        """ Assign a leader for the direction the vehicle wants to turn """
        vehicles_in_direction = [v for v in vehicles if v.direction == self.direction and v.position > self.position]

        if vehicles_in_direction:
            self.leader = max(vehicles_in_direction, key=lambda v: v.position) 
            print(f"Vehicle {self.vehicle_id} has assigned leader: Vehicle {self.leader.vehicle_id} for direction {self.direction}.")

    def adjust_speed(self):
        """ Adjust speed according to leader if one is assigned """
        if self.leader:
            self.speed = self.leader.speed
            print(f"Vehicle {self.vehicle_id}: Adjusting speed to follow leader {self.leader.vehicle_id}.")
        else:
            self.speed = max(10, min(self.speed + random.uniform(-5, 5), MAX_SPEED))
        
        self.position += self.speed
        print(f"Vehicle {self.vehicle_id}: Adjusting speed to {self.speed:.2f} km/h.")

    def process_heartbeat(self, heartbeat):
        if self.detect_and_correct_errors(heartbeat):
            if heartbeat["sync"] and self.running:
                self.synchronized = True
                self.speed = min(int(heartbeat["binary_message"], 2), MAX_SPEED) 
                self.position += self.speed
            else:
                self.adjust_speed()
            return True
        return False

    def detect_and_correct_errors(self, heartbeat):
        error_type = heartbeat.get('error_type')

        if error_type == SINGLE_BIT:
            return self.correct_single_bit_error(heartbeat)
        elif error_type == DOUBLE_BIT:
            error_data[DOUBLE_BIT][self.vehicle_id] += 1
            return False  
        elif error_type == BURST:
            error_data[BURST][self.vehicle_id] += 1
            return self.correct_burst_error(heartbeat)
        return True 

    def correct_single_bit_error(self, heartbeat):
        binary_message = heartbeat["binary_message"]
        original_parity = heartbeat["parity"]
        calculated_parity = binary_message.count('1') % 2

        if original_parity != calculated_parity:
            for i in range(len(binary_message)):
                flipped_message = flip_bit(binary_message, i)
                if flipped_message.count('1') % 2 == original_parity:
                    heartbeat["binary_message"] = flipped_message
                    print(f"Vehicle {self.vehicle_id}: Single-bit error detected and corrected.")
                    error_data[SINGLE_BIT][self.vehicle_id] += 1
                    return True
        return False

    def correct_burst_error(self, heartbeat):
        """ Correct burst error using majority vote from redundant messages """
        redundant_messages = heartbeat.get("redundant_messages", [heartbeat["binary_message"]])
        
        if len(redundant_messages) < 3:  
            return False
        
        majority_message = max(set(redundant_messages), key=redundant_messages.count)
        
        if majority_message != heartbeat["binary_message"]:
            print(f"Vehicle {self.vehicle_id}: Burst error corrected using redundancy.")
            heartbeat["binary_message"] = majority_message
            return True
        
        return False 

    def detect_obstacle(self):
        """ Simulate obstacle detection logic with reduced frequency """
        if not self.obstacle_detected and random.random() < 0.05:  
            self.obstacle_detected = True
            print(f"Vehicle {self.vehicle_id}: Obstacle detected! Initiating emergency procedures.")

    def handle_obstacle(self):
        """ Handle the detected obstacle by decelerating and notifying others """
        if self.speed > 0: 
            print(f"Vehicle {self.vehicle_id}: Decelerating due to obstacle.")
            self.speed = max(0, self.speed - 10)  
            for vehicle in vehicles:
                if vehicle != self and not vehicle.obstacle_detected:
                    vehicle.obstacle_detected = True
                    vehicle.speed = max(0, vehicle.speed - 10)
                    print(f"Vehicle {vehicle.vehicle_id}: Decelerating to {vehicle.speed:.2f} km/h due to obstacle in front.")
        else:
            self.obstacle_detected = False  

    def handle_intersection(self):
        """ Handles the behavior of the vehicle at an intersection. """
        if self.at_intersection():
            if self.direction == "straight":
                print(f"Vehicle {self.vehicle_id}: Proceeding straight through the intersection.")
            elif self.direction in ["left", "right"]:
                if self.can_turn():
                    print(f"Vehicle {self.vehicle_id}: Turning {self.direction} at the intersection.")
                    self.direction = random.choice(["straight", "left", "right"])  
                    self.leader = None 
                else:
                    print(f"Vehicle {self.vehicle_id}: Waiting to turn {self.direction}.")
                    self.speed = 0 

    def at_intersection(self):
        """ Simulate the detection of an intersection """
        return random.random() < 0.1  

    def can_turn(self):
        """ Simulate whether the vehicle is able to turn """
        return random.random() < 0.7

    def log_metrics(self, time_step):
        with metrics_lock:
            time_data.append(time_step)
            speed_data[self.vehicle_id].append(self.speed)
            position_data[self.vehicle_id].append(self.position)
            cwnd_data[self.vehicle_id].append(self.cwnd)

class HeartbeatSender(threading.Thread):
    def __init__(self, heartbeat_queue, interval=1):
        super().__init__()
        self.heartbeat_queue = heartbeat_queue
        self.interval = interval
        self.running = True

    def run(self):
        while self.running:
            time_step = time.time()
            heartbeat = self.create_heartbeat_message()
            self.heartbeat_queue.put((random.randint(1, 10), heartbeat))
            print(f"Sent heartbeat: {heartbeat['binary_message']} at time {time_step}")
            time.sleep(self.interval)

    def stop(self):
        """ Stop the heartbeat sender thread """
        self.running = False

    def create_heartbeat_message(self):
        binary_message = int_to_binary_string(random.randint(0, 255), bits=8)
        parity = binary_message.count('1') % 2
        heartbeat = {
            "binary_message": binary_message,
            "parity": parity,
            "sync": random.choice([True, False]),
            "error_type": random.choice([None, SINGLE_BIT, DOUBLE_BIT, BURST])
        }
        return heartbeat

vehicles = []

def flip_bit(binary_str, index):
    """ Flip the bit at a given index """
    flipped_bit = '1' if binary_str[index] == '0' else '0'
    return binary_str[:index] + flipped_bit + binary_str[index + 1:]

def create_vehicles_and_start_simulation(num_vehicles, simulation_duration):
    global vehicles
    heartbeat_queue = AgedPriorityQueue()
    congestion_queue = queue.Queue()

    heartbeat_sender = HeartbeatSender(heartbeat_queue)
    heartbeat_sender.start()

    for i in range(num_vehicles):
        vehicle = Vehicle(vehicle_id=i, heartbeat_queue=heartbeat_queue, congestion_queue=congestion_queue)
        vehicles.append(vehicle)
        vehicle.start()

    start_time = time.time()
    while time.time() - start_time < simulation_duration:
        time.sleep(1)  
    heartbeat_sender.stop()
    heartbeat_sender.join()

    for vehicle in vehicles:
        vehicle.stop()
        vehicle.join()

create_vehicles_and_start_simulation(5, 10)