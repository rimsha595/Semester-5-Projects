from flask import Flask, jsonify, request, render_template, send_file
from flask_cors import CORS
import threading, time, random, os, io, csv
from werkzeug.utils import secure_filename
from fpdf import FPDF

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

COLOR_PALETTE = [
    "#1E90FF",  # DodgerBlue
    "#32CD32",  # LimeGreen
    "#FF4500",  # OrangeRed
    "#FFD700",  # Gold
    "#FF69B4",  # HotPink
    "#00CED1",  # DarkTurquoise
    "#FF8C00",  # DarkOrange
    "#9400D3"   # DarkViolet
]

# ---------------- Global File Colors ----------------
FILE_COLORS = {}
def get_color_for_file(filename):
    if filename not in FILE_COLORS:
        FILE_COLORS[filename] = random.choice(COLOR_PALETTE)
    return FILE_COLORS[filename]

# ---------------- Global PID Counter ----------------
NEXT_PID = 1
def generate_pid():
    global NEXT_PID
    pid = f"P{NEXT_PID}"
    NEXT_PID += 1
    return pid

# ---------------- Process Class ----------------
class Process:
    def __init__(self, pid, burst, arrival=0, priority=1, filename=None, color=None):
        self.pid = str(pid)
        self.filename = filename
        self.burst = int(burst)
        self.remaining = int(burst)
        self.arrival = int(arrival)
        self.priority = int(priority)
        self.state = "New"
        self.pc = 0
        self.sp = 0
        self.waiting_time = 0
        self.turnaround_time = 0
        self.io_required = random.choice([True, False])
        self.io_time = 3
        self.color = color or random.choice(COLOR_PALETTE)

    def to_dict(self):
        return self.__dict__

# ---------------- Simulation Class ----------------
class Simulation:
    def __init__(self):
        self.lock = threading.Lock()
        self.process_list = []
        self.ready_queue = []
        self.blocked_queue = []
        self.resources = {"CPU": True, "I/O": True, "Printer": True}
        self.time_quantum = 2
        self.time_elapsed = 0
        self.gantt = []
        self.current_process = None
        self.remaining_quantum = 0
        self.auto_thread = None
        self.auto_event = threading.Event()
        self.next_arrival_time = 0
        self.history = []
        self.cpu_busy_time = 0
        self.completed_count = 0

    def add_process(self, pid, burst, arrival=None, priority=1, filename=None, color=None):
        with self.lock:
            if arrival is None:
                arrival = self.next_arrival_time
                self.next_arrival_time += 1
            p = Process(pid, burst, arrival, priority, filename, color)
            self.process_list.append(p)
            self.process_list.sort(key=lambda x: (x.arrival, -x.priority))
            if p.arrival <= self.time_elapsed:
                p.state = "Ready"
                self.ready_queue.append(p)

    def step(self):
        with self.lock:
            for p in self.process_list:
                if p.state == "New" and p.arrival <= self.time_elapsed:
                    p.state = "Ready"
                    self.ready_queue.append(p)

            for p in list(self.blocked_queue):
                p.io_time -= 1
                if p.io_time <= 0:
                    p.state = "Ready"
                    p.io_time = 3
                    self.blocked_queue.remove(p)
                    self.ready_queue.append(p)

            if not self.current_process and self.ready_queue:
                self.current_process = self.ready_queue.pop(0)
                self.current_process.state = "Running"
                self.remaining_quantum = self.time_quantum
                self.resources["CPU"] = False

            cpu_used = False
            if self.current_process:
                self.current_process.pc += 1
                self.current_process.sp += 1
                self.current_process.remaining -= 1
                self.remaining_quantum -= 1
                cpu_used = True

                if self.current_process.io_required and random.random() < 0.2:
                    self.current_process.state = "Blocked"
                    self.blocked_queue.append(self.current_process)
                    self.resources["CPU"] = True
                    self.gantt.append({
                        "time": self.time_elapsed,
                        "pid": self.current_process.pid,
                        "filename": self.current_process.filename,
                        "color": self.current_process.color
                    })
                    self.current_process = None
                else:
                    self.gantt.append({
                        "time": self.time_elapsed,
                        "pid": self.current_process.pid,
                        "filename": self.current_process.filename,
                        "color": self.current_process.color
                    })
                    if self.current_process.remaining <= 0:
                        self.current_process.state = "Terminated"
                        self.current_process.turnaround_time = self.time_elapsed - self.current_process.arrival + 1
                        self.current_process.waiting_time = self.current_process.turnaround_time - self.current_process.burst
                        self.resources["CPU"] = True
                        self.completed_count += 1
                        self.current_process = None
                    elif self.remaining_quantum <= 0:
                        self.current_process.state = "Ready"
                        self.ready_queue.append(self.current_process)
                        self.resources["CPU"] = True
                        self.current_process = None
            else:
                self.gantt.append({"time": self.time_elapsed, "pid": "Idle", "color": "#ccc"})

            if cpu_used:
                self.cpu_busy_time += 1

            snapshot = {
                "time": self.time_elapsed,
                "current": self.current_process.pid if self.current_process else "Idle",
                "state": self.current_process.state if self.current_process else "Idle",
                "pc": self.current_process.pc if self.current_process else 0,
                "sp": self.current_process.sp if self.current_process else 0,
                "ready_queue": [p.pid for p in self.ready_queue],
                "blocked_queue": [p.pid for p in self.blocked_queue],
                "cpu_util": self.get_cpu_utilization(),
                "throughput": self.get_throughput()
            }
            self.history.append(snapshot)
            self.time_elapsed += 1

            if self.auto_thread and self.auto_thread.is_alive():
                all_done = (not self.current_process and not self.ready_queue and not self.blocked_queue)
                if all_done:
                    self.stop_auto()

    def get_state(self):
        with self.lock:
            return {
                "time_elapsed": self.time_elapsed,
                "process_list": [p.to_dict() for p in self.process_list],
                "ready_queue": [p.pid for p in self.ready_queue],
                "blocked_queue": [p.pid for p in self.blocked_queue],
                "resources": self.resources,
                "gantt": self.gantt[-200:],
                "current": self.current_process.pid if self.current_process else None,
                "avg_wt": self._compute_avg("waiting_time"),
                "avg_tat": self._compute_avg("turnaround_time"),
                "cpu_util": self.get_cpu_utilization(),
                "throughput": self.get_throughput()
            }

    def _compute_avg(self, field):
        vals = [getattr(p, field) for p in self.process_list if getattr(p, field) is not None and p.state=="Terminated"]
        return sum(vals)/len(vals) if vals else None

    def get_cpu_utilization(self):
        return round((self.cpu_busy_time / self.time_elapsed * 100), 2) if self.time_elapsed > 0 else 0

    def get_throughput(self):
        return round((self.completed_count / self.time_elapsed), 2) if self.time_elapsed > 0 else 0

    def start_auto(self, interval_ms=500):
        if self.auto_thread and self.auto_thread.is_alive(): return False
        self.auto_event.clear()
        def runner():
            while not self.auto_event.is_set():
                self.step()
                time.sleep(max(interval_ms/1000, 0.05))
        self.auto_thread = threading.Thread(target=runner, daemon=True)
        self.auto_thread.start()
        return True

    def stop_auto(self):
        if self.auto_thread and self.auto_thread.is_alive():
            self.auto_event.set()
            self.auto_thread.join(timeout=1)
            return True
        return False

# ---------------- Initialize Simulation ----------------
sim = Simulation()

# ---------------- Routes ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/state")
def state():
    return jsonify(sim.get_state())

@app.route("/history")
def history():
    return jsonify(sim.history[-500:])

@app.route("/add", methods=["POST"])
def add_process():
    data = request.json or {}
    burst = int(data.get("burst",0))
    arrival = int(data.get("arrival")) if "arrival" in data else None
    priority = int(data.get("priority",1))
    filename = data.get("file")  # optional filename
    color = get_color_for_file(filename) if filename else None
    if not burst: return jsonify({"ok":False,"error":"burst required"})
    pid = generate_pid()               # Use sequential PID
    sim.add_process(pid, burst, arrival, priority, filename, color)
    return jsonify({"ok":True, "pid": pid})

@app.route("/step", methods=["POST"])
def step_route():
    sim.step()
    return jsonify(sim.get_state())

@app.route("/auto", methods=["POST"])
def auto():
    data = request.json or {}
    action = data.get("action")
    interval = int(data.get("interval",500))
    if action=="start": sim.start_auto(interval_ms=interval); return jsonify({"ok":True,"status":"started"})
    if action=="stop": sim.stop_auto(); return jsonify({"ok":True,"status":"stopped"})
    return jsonify({"ok":False,"error":"invalid action"}),400

@app.route("/upload", methods=["POST"])
def upload_process():
    if "file" not in request.files: return jsonify({"error":"No file uploaded"}),400
    file = request.files["file"]
    if not file.filename: return jsonify({"error":"No file selected"}),400

    os.makedirs("uploads", exist_ok=True)
    filename = secure_filename(file.filename)
    file.save(os.path.join("uploads", filename))

    pid = generate_pid()               # sequential PID: P1, P2, P3...
    burst = random.randint(2,10)
    priority = random.randint(1,5)
    color = get_color_for_file(filename)
    sim.add_process(pid, burst, arrival=None, priority=priority, filename=filename, color=color)

    return jsonify({"ok":True,"pid":pid,"burst":burst,"priority":priority,"file":filename,"color":color})

# ---------------- Run App ----------------
if __name__=="__main__":
    app.run(debug=True, port=5000)
