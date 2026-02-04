async function loadAll() {
  const logs = await (await fetch("/api/logs")).json();
  const clips = await (await fetch("/api/clips")).json();
  const stats = await (await fetch("/api/stats")).json();

  const tbody = document.querySelector("#logTable tbody");
  tbody.innerHTML = "";

  logs.reverse().forEach(l => {
    tbody.innerHTML += `<tr>
      <td>${l.timestamp}</td>
      <td>${l.class}</td>
      <td>${parseFloat(l.confidence).toFixed(2)}</td>
      <td><button onclick="play('${l.clip}')">▶</button></td>
    </tr>`;
  });

  const clipBox = document.getElementById("clips");
  clipBox.innerHTML = "";
  clips.forEach(c => {
    clipBox.innerHTML += `
      <div>
        ${c}
        <button onclick="play('${c}')">▶</button>
        <button onclick="delClip('${c}')">🗑️</button>
      </div>`;
  });

  const statsBox = document.getElementById("stats");
  statsBox.innerHTML = "";
  Object.entries(stats).forEach(([k,v]) => {
    statsBox.innerHTML += `<div class="stat">${k}: ${v}</div>`;
  });
}

function play(name) {
  const v = document.getElementById("player");
  v.src = "/clips/" + name;
  v.play();
}

async function delClip(name) {
  if (!confirm("Delete clip?")) return;
  await fetch("/api/delete_clip", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({name})
  });
  loadAll();
}

loadAll();
setInterval(loadAll, 5000);
