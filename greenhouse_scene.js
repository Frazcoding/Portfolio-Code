// Blender-authored geometry. Blender Z-up becomes Three.js Y-up in glTF.
const greenhouseParts = {};
const loader = new THREE.GLTFLoader();
loader.load("greenhouse.glb", (gltf) => {
  gltf.scene.traverse((object) => {
    if (object.isMesh) {
      greenhouseParts[object.name] = object;
      object.castShadow = true;
      object.receiveShadow = true;
    }
  });
  scene.add(gltf.scene);
  if (!greenhouseParts.ThermalScreen || !greenhouseParts.BufferTank) {
    document.getElementById("modelStatus").textContent = "Model part names do not match simulation bindings";
  }
  update3D(currentScenario.series, k);
}, undefined, (error) => {
  console.error("Could not load greenhouse.glb", error);
  document.getElementById("modelStatus").textContent = "3D model unavailable · open with run_viewer.cmd";
});

camera.position.set(35, 22, 35);
controls.target.set(6, 3, 0);
controls.update();

addTag("Venlo Greenhouse", () => new THREE.Vector3(0, 6.5, 0), (d, i) =>
  d.t_in ? `${d.t_in[i].toFixed(1)} °C canopy` : "Indoor temperature unavailable");
addTag("Thermal Screen", () => new THREE.Vector3(0, 5.1, 0), (d, i) =>
  d.screen_pos ? `${d.screen_pos[i]}% closed` : "Screen state unavailable");
addTag("Two-Stage R-717", () => new THREE.Vector3(22, 3.6, -4.5), (d, i) =>
  `${d.p_comp[i].toFixed(1)} kWe · COP ${d.cop[i].toFixed(2)}`);
addTag("1.5 m³ Buffer", () => new THREE.Vector3(22, 2.7, 5.5), (d, i) =>
  d.t_buf ? `${d.t_buf[i].toFixed(1)} °C storage` : "Tank temperature unavailable");
