const hydrogenParts = {};
let windFocus = new URLSearchParams(location.search).get("view") === "wind";
const defaultWindFocus = windFocus;
function setWindVisible(visible) {
  windFocus = visible;
  for (const [name, part] of Object.entries(hydrogenParts)) {
    if (name.startsWith("Wind_")) part.visible = visible;
  }
  if (tagsList.length === 4) {
    tagsList.forEach((tag, index) => tag.el.style.display = visible && index < 3 ? "none" : "");
  }
}
const base = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1300),
  new THREE.MeshStandardMaterial({color: 0xa8b6ae, roughness: .95}));
base.rotation.x = -Math.PI/2;
base.position.y = -1.15;
scene.add(base);
new THREE.GLTFLoader().load("hydrogen_microgrid.glb", (gltf) => {
  gltf.scene.traverse((object) => {
    if (object.isMesh) {
      hydrogenParts[object.name] = object;
      object.castShadow = true;
      object.receiveShadow = true;
      if (object.name.startsWith("PEM_") && object.name.endsWith("_Container") ||
          object.name.startsWith("H2_Tank_") || object.name.startsWith("Ferry_H2Tank_") ||
          object.name.startsWith("Wind_") && object.name.endsWith("_Nacelle")) {
        object.material = object.material.clone();
      }
    }
  });
  scene.add(gltf.scene);
  setWindVisible(windFocus);
  if (!["PEM_1_Container", "PEM_4_Container", "H2_Tank_1", "H2_Tank_10", "Ferry_Hull", "Wind_1_Tower"].every(name => hydrogenParts[name])) {
    document.getElementById("modelStatus").textContent = "Hydrogen model is missing named simulation parts";
  }
  update3D(currentScenario.series, k);
}, undefined, (error) => {
  console.error("Could not load hydrogen_microgrid.glb", error);
  document.getElementById("modelStatus").textContent = "3D model unavailable · open with run_viewer.cmd";
});

camera.position.set(190, 135, 220);
controls.target.set(40, 4, 35);
if (windFocus) {
  camera.position.set(760, 310, 500);
  controls.target.set(0, 90, -400);
}
controls.update();
const toolsBar = document.getElementById("resetView").parentElement;
for (const [label, pos, target] of [
  ["Plant", [45, 42, 52], [-12, 2, -2]],
  ["Ferry", [205, 95, 160], [92, 5, 75]],
  ["Wind", [760, 310, 500], [0, 90, -400]]
]) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.title = `Focus ${label.toLowerCase()} at model scale`;
  button.addEventListener("click", () => {
    camera.position.set(...pos);
    controls.target.set(...target);
    setWindVisible(label === "Wind");
    controls.update();
  });
  toolsBar.insertBefore(button, document.getElementById("resetView"));
}
document.getElementById("resetView").addEventListener("click", () => setWindVisible(defaultWindFocus));
addTag("4 × 2 MW PEM bank", () => new THREE.Vector3(-27, 5, 2), (d, i) => d.p_ely ? `${d.p_ely[i].toFixed(1)} / 8.0 MW` : "Idle during bunkering");
addTag("Nominal 350 bar terminal buffer", () => new THREE.Vector3(4, 5, -13), (d, i) => `${(d.h2_tank ? d.h2_tank[i] : d.h2_term[i]).toFixed(0)} kg H₂`);
addTag("Hypothetical hydrogen ferry", () => new THREE.Vector3(92, 18, 75), (d, i) => d.h2_bunkered ? `${d.h2_bunkered[i].toFixed(0)} / 1200 kg loaded` : "Stornoway–Ullapool hull analogue");
addTag("3 × 6.2 MW wind analogues", () => new THREE.Vector3(0, 210, -400), (d, i) => d.wind ? `${d.wind[i].toFixed(1)} MW generated` : "Remote generation");
setWindVisible(windFocus);
