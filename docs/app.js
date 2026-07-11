// ---- 1. Basic Three.js setup ----
const container = document.getElementById('canvas-container');

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(
  75,
  container.clientWidth / container.clientHeight,
  0.1,
  1000
);
camera.position.z = 3;

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(container.clientWidth, container.clientHeight);
container.appendChild(renderer.domElement);

// ---- 2. Create the avatar shape (an icosahedron = spiky-able sphere) ----
const geometry = new THREE.IcosahedronGeometry(1, 1); // radius 1, detail 1
const material = new THREE.MeshStandardMaterial({
  color: 0x7f5af0,
  flatShading: true,
  metalness: 0.3,
  roughness: 0.4
});
const avatar = new THREE.Mesh(geometry, material);
scene.add(avatar);

// ---- 3. Lighting (without light, MeshStandardMaterial looks black) ----
const light1 = new THREE.DirectionalLight(0xffffff, 1);
light1.position.set(5, 5, 5);
scene.add(light1);

const light2 = new THREE.AmbientLight(0x404040, 1.5);
scene.add(light2);

// ---- 4. Animation loop ----
let avatarSpinSpeed = 0.005;

function animate() {
  requestAnimationFrame(animate);

  avatar.rotation.x += avatarSpinSpeed * 0.6;
  avatar.rotation.y += avatarSpinSpeed;

  renderer.render(scene, camera);
}
animate();

// ---- 5. Handle window resize ----
window.addEventListener('resize', () => {
  camera.aspect = container.clientWidth / container.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(container.clientWidth, container.clientHeight);
});

// ---- 6. Connect to backend + morph avatar ----
const textInput = document.getElementById('text-input');
const analyzeBtn = document.getElementById('analyze-btn');
const statusText = document.getElementById('status-text');

const BACKEND_URL = "https://internet-mirror-lzux.vercel.app/analyze";

analyzeBtn.addEventListener('click', async () => {
  const text = textInput.value;

  if (!text.trim()) {
    statusText.textContent = "Please paste some reviews first.";
    return;
  }

  analyzeBtn.disabled = true;
  statusText.textContent = "Analyzing...";

  try {
    const response = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    const vector = data.personality_vector;

    statusText.textContent =
      `Joy: ${vector.joy} | Anger: ${vector.anger} | Reviews analyzed: ${vector.chunks_analyzed}`;

    morphAvatar(vector);
    renderResults(vector, data.raw_results);   // NEW

  } catch (err) {
    statusText.textContent = "Error connecting to backend. Is app.py running?";
    console.error(err);
  } finally {
    analyzeBtn.disabled = false;
  }
});

// ---- NEW: render review cards with sentiment + auto-response ----
function renderResults(vector, results) {
  const summaryEl = document.getElementById('results-summary');
  const listEl = document.getElementById('results-list');

  const positiveCount = results.filter(r => r.label === "POSITIVE").length;
  const negativeCount = results.filter(r => r.label === "NEGATIVE").length;

  summaryEl.textContent =
    `${results.length} reviews analyzed — ${positiveCount} positive, ${negativeCount} negative.`;

  listEl.innerHTML = "";

  results.forEach(r => {
    const card = document.createElement('div');
    card.className = `review-card ${r.label.toLowerCase()}`;

    card.innerHTML = `
      <div class="review-text">"${escapeHtml(r.text)}"</div>
      <div class="review-meta">${r.label} · confidence ${r.score}</div>
      <div class="review-response-label">Suggested reply</div>
      <div class="review-response">${escapeHtml(r.response)}</div>
    `;

    listEl.appendChild(card);
  });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
// ---- end new section ----
// ---- 7. Morph function: maps personality vector -> avatar appearance ----
function morphAvatar(vector) {
  // Color: blend from calm blue (low anger) to angry red (high anger)
  const calmColor = new THREE.Color(0x2cb67d);   // green-ish calm
  const angryColor = new THREE.Color(0xff3b3b);  // red angry
  const mixedColor = calmColor.clone().lerp(angryColor, vector.anger);
  avatar.material.color = mixedColor;

  // Spikiness: rebuild geometry with more/less displacement based on anger
  const detail = 1;
  const newGeometry = new THREE.IcosahedronGeometry(1, detail);
  const posAttr = newGeometry.attributes.position;

  for (let i = 0; i < posAttr.count; i++) {
    const x = posAttr.getX(i);
    const y = posAttr.getY(i);
    const z = posAttr.getZ(i);
    const vertex = new THREE.Vector3(x, y, z);

    // Push vertices outward randomly, scaled by anger score
    const spike = 1 + (Math.random() * vector.anger * 0.6);
    vertex.multiplyScalar(spike);

    posAttr.setXYZ(i, vertex.x, vertex.y, vertex.z);
  }
  newGeometry.computeVertexNormals();

  avatar.geometry.dispose();
  avatar.geometry = newGeometry;

  // Rotation speed: joy makes it spin faster
  avatarSpinSpeed = 0.003 + (vector.joy * 0.02);
}