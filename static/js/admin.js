let activityChart;
let securityChart;

function getRandom(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

// ---------------- INIT CHARTS ----------------
function initCharts() {

    const labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

    // ACTIVITY CHART (LINE)
    const ctx1 = document.getElementById("activityChart");

    if (ctx1) {
        activityChart = new Chart(ctx1, {
            type: "line",
            data: {
                labels: labels,
                datasets: [{
                    label: "System Activity",
                    data: [60, 70, 80, 90, 100, 85, 95],
                    borderColor: "#0ea5e9",
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // SECURITY CHART (BAR)
    const ctx2 = document.getElementById("securityChart");

    if (ctx2) {
        securityChart = new Chart(ctx2, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Security Events",
                    data: [2, 1, 3, 0, 2, 4, 1],
                    backgroundColor: "#ef4444"
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

// ---------------- UPDATE KPI CARDS ----------------
function updateKPIs() {

    document.getElementById("total_users").innerText = getRandom(120, 150);
    document.getElementById("active_users").innerText = getRandom(80, 120);
    document.getElementById("failed_logins").innerText = getRandom(0, 10);
    document.getElementById("security_alerts").innerText = getRandom(0, 5);
}

// ---------------- LIVE CHART UPDATE ----------------
function updateCharts() {

    if (activityChart) {
        activityChart.data.datasets[0].data =
            Array.from({ length: 7 }, () => getRandom(50, 120));
        activityChart.update();
    }

    if (securityChart) {
        securityChart.data.datasets[0].data =
            Array.from({ length: 7 }, () => getRandom(0, 6));
        securityChart.update();
    }
}

// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", function () {

    initCharts();
    updateKPIs();

    setInterval(updateKPIs, 4000);
    setInterval(updateCharts, 5000);
});