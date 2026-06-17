// =====================================================
//  GLOBAL VARIABLES
// =====================================================
const uploadBtn = document.getElementById("uploadBtn");
const fileInput = document.getElementById("fileInput");
const autoBtn = document.getElementById("autoBtn");
const stepBtn = document.getElementById("stepBtn");
const intervalInput = document.getElementById("interval");
const csvBtn = document.getElementById("csvBtnHistory");
const pdfBtn = document.getElementById("pdfBtnHistory");
const procSound = document.getElementById("procSwitchSound");

let loading = false;
let pieChart = null;
let lastCurrent = null;
let rotationAngle = 0;
let rotationSpeed = 0.03;
let cpuRunning = false;
let allowRotation = false;

// =====================================================
//  NOTIFICATION POPUP (WITH FADE + SLIDE)
// =====================================================
function notify(msg, type = "info") {
    const box = document.createElement("div");
    box.className = `toast toast-${type}`;
    box.innerText = msg;

    Object.assign(box.style, {
        position: "fixed",
        bottom: "20px",
        right: "20px",
        background: type === "error" ? "#ff4d4d" : "#0077cc",
        color: "white",
        padding: "12px 18px",
        borderRadius: "8px",
        fontWeight: "600",
        fontSize: "14px",
        boxShadow: "0 6px 16px rgba(0,0,0,0.25)",
        zIndex: 9999,
        opacity: 0,
        transform: "translateX(50px)",
        transition: "all 0.4s ease",
    });

    document.body.appendChild(box);
    requestAnimationFrame(() => {
        box.style.opacity = 1;
        box.style.transform = "translateX(0)";
    });
    setTimeout(() => {
        box.style.opacity = 0;
        box.style.transform = "translateX(50px)";
        setTimeout(() => box.remove(), 400);
    }, 2500);
}

// =====================================================
//  FILE UPLOAD
// =====================================================
uploadBtn.addEventListener("click", async () => {
    const file = fileInput.files[0];
    if (!file) return notify("Select a file first", "error");

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/upload", { method: "POST", body: formData });
        const data = await res.json();
        if (!data.ok) return notify(data.error || "Upload failed", "error");
        notify("Process Uploaded Successfully!", "info");
        loadState();
    } catch {
        notify("Upload error", "error");
    }
});

// =====================================================
//  STEP BUTTON
// =====================================================
stepBtn.addEventListener("click", async () => {
    await fetch("/step", { method: "POST" });
    loadState();
});

// =====================================================
//  AUTO MODE
// =====================================================
autoBtn.addEventListener("click", async () => {
    const mode = autoBtn.dataset.mode;
    const interval = intervalInput.value || 500;

    try {
        const res = await fetch("/auto", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: mode, interval }),
        });
        const data = await res.json();

        if (!data.ok) return notify(data.error || "Action failed", "error");

        if (mode === "start") {
            autoBtn.innerText = "Stop Auto";
            autoBtn.dataset.mode = "stop";
            allowRotation = true;
            notify("Auto mode started", "info");
            loadState();
            showPage(2);
        } else {
            autoBtn.innerText = "Start Auto";
            autoBtn.dataset.mode = "start";
            allowRotation = false;
            notify("Auto mode stopped", "error");
        }
    } catch (err) {
        console.error(err);
        notify("Auto mode request failed", "error");
    }
});

// =====================================================
//  CSV / PDF EXPORT
// =====================================================
csvBtn.addEventListener("click", () => window.open("/export/csv", "_blank"));
pdfBtn.addEventListener("click", () => window.open("/export/pdf", "_blank"));

// =====================================================
//  LOAD STATE
// =====================================================
async function loadState() {
    if (loading) return;
    loading = true;

    try {
        const res = await fetch("/state");
        const data = await res.json();

        updateProcessTable(data.process_list);
        updateCPU(data.current);
        updateQueues(data.ready_queue, data.blocked_queue, data.process_list);
        updatePieChart(data.gantt);
        updateMetrics(data.cpu_util, data.throughput);
        await loadHistory();

        const finished =
            (!data.current || data.current === "Idle") &&
            data.ready_queue.length === 0 &&
            data.blocked_queue.length === 0;

        if (finished) {
            allowRotation = false;
            cpuRunning = false;
            rotationAngle = 0;
            if (pieChart) {
                pieChart.options.rotation = 0;
                pieChart.update("none");
            }
            autoBtn.innerText = "Start Auto";
            autoBtn.dataset.mode = "start";
        } else {
            cpuRunning = data.current && data.current !== "Idle";
            allowRotation = cpuRunning;
        }
    } catch (err) {
        console.error("State error:", err);
    }

    loading = false;
}

// =====================================================
//  PIE CHART UPDATE
// =====================================================
function updatePieChart(gantt) {
    const ctx = document.getElementById("cpuPieChart").getContext("2d");
    const counts = {};
    const colors = {};
    const filenames = {};

    gantt.forEach(x => {
        if(x.pid === "Idle") return;
        if(!counts[x.pid]) {
            counts[x.pid] = 0;
            colors[x.pid] = x.color || "#ccc";
            filenames[x.pid] = x.filename || "";
        }
        counts[x.pid] += 1;
    });

    const labels = Object.keys(counts).map(pid => `${pid} - ${filenames[pid]}`);
    const values = Object.keys(counts).map(pid => counts[pid]);
    const backgroundColors = Object.keys(counts).map(pid => colors[pid]);

    if (!pieChart) {
        pieChart = new Chart(ctx, {
            type: "doughnut",
            data: { labels, datasets: [{ data: values, backgroundColor: backgroundColors, borderColor: "#fff", borderWidth: 3 }] },
            options: {
                responsive: true,
                cutout: "40%",
                rotation: rotationAngle,
                animation: { animateRotate: false, animateScale: false },
                plugins: {
                    legend: { position: "bottom", labels: { font: { size: 14, weight: "bold" } } },
                    title: { display: true, text: "CPU Time Distribution Per Process", font: { size: 15, weight: "bold" }, padding: 20 },
                    datalabels: { 
                        color: "#fff", 
                        font: { weight: "bold", size: 14 }, 
                        formatter: (value, context) => {
                            const sum = context.chart.data.datasets[0].data.reduce((a,b)=>a+b,0);
                            return (value / sum * 100).toFixed(1) + "%";
                        }
                    }
                }
            },
            plugins: [ChartDataLabels]
        });
        return;
    }

    pieChart.data.labels = labels;
    pieChart.data.datasets[0].data = values;
    pieChart.data.datasets[0].backgroundColor = backgroundColors;
    pieChart.update("none");
}

// =====================================================
//  PIE ROTATION LOOP
// =====================================================
function animatePieRotation() {
    if (pieChart && allowRotation && cpuRunning) {
        rotationAngle += rotationSpeed;
        if (rotationAngle > Math.PI * 2) rotationAngle = 0;
        pieChart.options.rotation = rotationAngle;
        pieChart.update("none");
    }
    requestAnimationFrame(animatePieRotation);
}
requestAnimationFrame(animatePieRotation);

// =====================================================
//  PROCESS TABLE UPDATE
// =====================================================
function updateProcessTable(list) {
    const body = document.querySelector("#processTable tbody");
    const body2 = document.querySelector("#processTable2 tbody");
    body.innerHTML = "";
    body2.innerHTML = "";

    list.forEach(p => {
        const row =`
            <tr>
                <td>${p.pid}</td>
                <td>${p.filename || "-"}</td>
                <td>${p.burst}</td>
                <td>${p.arrival}</td>
                <td>${p.priority}</td>
                <td>${p.pc}</td>
                <td>${p.sp}</td>
                <td>${p.waiting_time}</td>
                <td>${p.turnaround_time}</td>
                <td>${p.state}</td>
            </tr>`;
        body.innerHTML += row;
        body2.innerHTML += row;
    });
}

// =====================================================
//  CPU UPDATE + SOUND
// =====================================================
function updateCPU(current) {
    const currEl = document.getElementById("current");
    currEl.innerText = current || "Idle";
    if (current && current !== lastCurrent) {
        procSound?.play().catch(() => {});
        currEl.classList.add("pulse");
        setTimeout(() => currEl.classList.remove("pulse"), 300);
    }
    lastCurrent = current;
}

// =====================================================
//  QUEUE UPDATE WITH ANIMATION
// =====================================================
function updateQueues(ready, blocked, processList) {
    const rq = document.getElementById("readyQueue");
    const bq = document.getElementById("blockedQueue");
    rq.innerHTML = "";
    bq.innerHTML = "";

    const procColors = {};
    processList.forEach(p => { procColors[p.pid] = p.color; });

    const renderQueue = (queue, container, block=false) => {
        queue.forEach(pid => {
            const box = document.createElement("span");
            box.className = "procBox" + (block ? " blockBox" : "");
            box.innerText = pid;
            box.style.background = procColors[pid] || "#ccc";
            container.appendChild(box);
            setTimeout(() => box.classList.add("show"), 50);
        });
    };

    renderQueue(ready, rq);
    renderQueue(blocked, bq, true);
}

// =====================================================
//  HISTORY UPDATE
// =====================================================
async function loadHistory() {
    const res = await fetch("/history");
    const history = await res.json();
    const body = document.querySelector("#historyTable tbody");
    body.innerHTML = "";
    history.forEach(h => {
        body.innerHTML += `<tr>
            <td>${h.time}</td>
            <td>${h.current}</td>
            <td>${h.state}</td>
            <td>${h.pc}</td>
            <td>${h.sp}</td>
            <td>${h.ready_queue.join(", ")}</td>
            <td>${h.blocked_queue.join(", ")}</td>
            <td>${h.cpu_util ?? 0}%</td>
            <td>${h.throughput ?? 0}</td>
        </tr>`;
    });
}

// =====================================================
//  METRICS UPDATE
// =====================================================
function updateMetrics(cpu, throughput) {
    document.getElementById("cpuUtil").innerText = cpu + "%";
    document.getElementById("throughput").innerText = throughput;
    const bar = document.getElementById("cpuProgress");
    if (bar) bar.style.background = cpu < 50 ? "#4caf50" : cpu < 80 ? "#ff9800" : "#f44336";
    if (bar) bar.style.width = cpu + "%";
}

// =====================================================
//  AUTO REFRESH
// =====================================================
setInterval(loadState, 500);
window.onload = () => loadState();
