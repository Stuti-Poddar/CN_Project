import threading
import queue
import time
import random
import matplotlib.pyplot as plt

SINGLE_BIT = 1
DOUBLE_BIT = 2
BURST = 3

MAX_SPEED = 120 
TURN_FREQUENCY = 5  
AGING_FACTOR = 2 

time_data = []
speed_data = {}
position_data = {}
resync_time_data = {}
cwnd_data = {}
metrics_lock = threading.Lock()

def int_to_binary_string(n, bits=8):
    """ Convert integer to binary string representation """
    return f"{n:0{bits}b}"

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
        self.direction = "straight" 
        self.leader = None 
        self.last_turn_time = time.time() 

        speed_data[self.vehicle_id] = []
        position_data[self.vehicle_id] = []
        resync_time_data[self.vehicle_id] = []
        cwnd_data[self.vehicle_id] = []

    def run(self):
        while self.running:
            time_step = time.time()
            if self.obstacle_detected:
                self.handle_obstacle()
                continue

            if time_step - self.last_turn_time >= TURN_FREQUENCY:
                if self.wants_to_turn():
                    self.assign_leader()
                    self.last_turn_time = time_step 

            try:
                priority, heartbeat = self.heartbeat_queue.get(timeout=1)
                print(f"Vehicle {self.vehicle_id} received priority {priority} heartbeat: {heartbeat['binary_message']}")
                self.process_heartbeat(heartbeat)

            except queue.Empty:
                print(f"Vehicle {self.vehicle_id}: No heartbeat received. Trying to resynchronize.")
                self.adjust_speed()

            self.handle_intersection()
            self.log_metrics(time_step)
            self.detect_obstacle()  

            time.sleep(1)  

    def wants_to_turn(self):
        """ Determine if the vehicle wants to turn (right or left) """
        return random.random() < 0.3 

    def assign_leader(self):
        """ Assign a leader for the direction the vehicle wants to turn """
        vehicles_in_direction = [v for v in vehicles if v.direction == self.direction and v.position > self.position]

        if vehicles_in_direction:
            self.leader = max(vehicles_in_direction, key=lambda v: v.position)  
            print(f"Vehicle {self.vehicle_id} has assigned leader: Vehicle {self.leader.vehicle_id} for direction {self.direction}.")
            self.update_following_speed() 
            for vehicle in vehicles:
                if vehicle != self and vehicle.leader == self.leader:
                    vehicle.speed = self.leader.speed 

    def update_following_speed(self):
        """ Adjust the speed of this vehicle to not exceed the leader's speed """
        if self.leader:
            self.speed = self.leader.speed  
            print(f"Vehicle {self.vehicle_id}: Adjusted speed to follow leader {self.leader.vehicle_id}: {self.speed:.2f} km/h")

    def adjust_speed(self):
        """ Adjust speed according to leader if one is assigned """
        if self.leader:
            if not self.synchronized:
                self.speed = self.leader.speed
                print(f"Vehicle {self.vehicle_id}: Adjusting speed to follow leader {self.leader.vehicle_id}.")
        else:
            change = random.uniform(-5, 5)
            self.speed = max(10, min(self.speed + change, MAX_SPEED))

        self.position += self.speed
        print(f"Vehicle {self.vehicle_id}: Adjusting speed to {self.speed:.2f} km/h.")

    def process_heartbeat(self, heartbeat):
        """ Process the received heartbeat without error checks. """
        if heartbeat["sync"]:
            self.synchronized = True
            self.speed = min(int(heartbeat["binary_message"], 2), MAX_SPEED)  
            self.update_following_speed() 
            self.position += self.speed
        else:
            self.adjust_speed()

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
                if vehicle != self:
                    vehicle.obstacle_detected = True
                    print(f"Vehicle {vehicle.vehicle_id}: Notified of obstacle by Vehicle {self.vehicle_id}.")
        else:
            self.obstacle_detected = False 

    def handle_intersection(self):
        """ Handle intersections and decide whether to stop or turn """
        if self.at_intersection():
            if self.direction == "straight":
                print(f"Vehicle {self.vehicle_id}: Proceeding straight through the intersection.")
            elif self.direction in ["left", "right"]:
                if self.can_turn():
                    print(f"Vehicle {self.vehicle_id}: Turning {self.direction}.")
                    self.position += self.turn_distance() 
                else:
                    print(f"Vehicle {self.vehicle_id}: Yielding at the intersection.")
                    self.speed = 0  
        else:
            self.position += self.speed

    def at_intersection(self):
        """ Check if the vehicle is approaching an intersection. Placeholder logic. """
        return random.random() < 0.2  

    def can_turn(self):
        """ Determine if the vehicle can turn left or right. Placeholder logic. """
        return random.choice([True, False])  

    def turn_distance(self):
        """ Calculate the distance moved during a turn. Placeholder logic. """
        return random.uniform(5, 10) 

    def stop(self):
        self.running = False

    def log_metrics(self, time_step):
        """ Logs performance metrics for each time step """
        with metrics_lock:  
            if not time_data or time_data[-1] < time_step:
                time_data.append(time_step)
            
            speed_data[self.vehicle_id].append(self.speed)
            position_data[self.vehicle_id].append(self.position)

def run_simulation():
    """ Main simulation function to start the vehicles and manage the lead vehicle. """
    congestion_queue = queue.Queue()

    global vehicles  
    vehicles = [Vehicle(vehicle_id=i, heartbeat_queue=queue.PriorityQueue(), congestion_queue=congestion_queue) for i in range(5)]

    for vehicle in vehicles:
        vehicle.start()

    def send_heartbeat():
        while True:
            for vehicle in vehicles:
                binary_message = int_to_binary_string(random.randint(0, MAX_SPEED), bits=8)
                sync = random.choice([True, False])  
                heartbeat = {
                    "binary_message": binary_message,
                    "sync": sync,
                    "age": 0  
                }
                priority = random.randint(1, 5) + (heartbeat["age"] // AGING_FACTOR)  
                vehicle.heartbeat_queue.put((priority, heartbeat))  
            time.sleep(1)

    threading.Thread(target=send_heartbeat, daemon=True).start()

    try:
        time.sleep(5)  
    finally:
        for vehicle in vehicles:
            vehicle.stop()
        for vehicle in vehicles:
            vehicle.join()

    # Performance metrics collection
    average_speed = sum([sum(speeds) for speeds in speed_data.values()]) / sum([len(speeds) for speeds in speed_data.values()]) if speed_data else 0
    total_distance = sum([vehicle.position for vehicle in vehicles])

    print(f"Average Speed: {average_speed:.2f} km/h")
    print(f"Total Distance Travelled: {total_distance:.2f} km")

    return {
        "Average Speed": average_speed,
        "Total Distance": total_distance,
    }

def compare_performance(normal_results, modified_results):
    """ Compare the performance of two different platooning methods. """
    categories = ['Average Speed', 'Total Distance']
    normal_performance = [normal_results[cat] for cat in categories]
    modified_performance = [modified_results[cat] for cat in categories]

    x = range(len(categories))

    plt.bar(x, normal_performance, width=0.4, label='Normal Vehicle Platooning', color='b', alpha=0.6)
    plt.bar([p + 0.4 for p in x], modified_performance, width=0.4, label='Modified Vehicle Simulation', color='g', alpha=0.6)

    plt.xlabel('Performance Metrics')
    plt.ylabel('Values')
    plt.title('Comparison of Vehicle Platooning Performance')
    plt.xticks([p + 0.2 for p in x], categories)
    plt.legend()
    plt.tight_layout()
    plt.show()

# Simulate normal vehicle platooning
normal_results = {
    "Average Speed": 75,  # Example value
    "Total Distance": 400,  # Example value
}

# Run modified vehicle simulation and get results
modified_results = run_simulation()

# Compare performance
compare_performance(normal_results, modified_results)
