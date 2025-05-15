window.onload = async () => {
    const table = document.getElementById("sessionTable").getElementsByTagName("tbody")[0];
    const res = await fetch("/sessions");
    const sessions = await res.json();

    sessions.forEach(session => {
        const row = document.createElement("tr");

        row.innerHTML = `
        <td>${session.seed_lot}</td>
        <td><code>${session.session_id}</code></td>
        <td>${formatTime(session.start_time)}</td>
        <td>${formatTime(session.end_time)}</td>
        <td>${session.accepted}</td>
        <td>${session.rejected}</td>
        <td>${session.sampled}</td>
      `;

        table.appendChild(row);
    });
};

function formatTime(timestamp) {
    if (!timestamp) return "-";
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}
