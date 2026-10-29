const retrofitParts = {};
const retrofitMeshes = [];
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(50, 42),
  new THREE.MeshStandardMaterial({color: 0xb4bdbe, roughness: .95})
);
ground.rotation.x = -Math.PI/2;
ground.position.y = -.33;
scene.add(ground);
const grid = new THREE.GridHelper(48, 24, 0x7f9192, 0x9daaaa);
grid.position.y = -.26;
scene.add(grid);

new THREE.GLTFLoader().load("retrofit_plant.glb", (gltf) => {
  gltf.scene.traverse((object) => {
    if (object.isMesh) {
      retrofitParts[object.name] = object;
      retrofitMeshes.push(object);
      object.castShadow = true;
      object.receiveShadow = true;
    }
  });
  scene.add(gltf.scene);
  if (!["TES_A_Shell", "TES_B_Shell", "Transformer", "ASHP85_A_Cabinet"].every(name => retrofitParts[name])) {
    document.getElementById("modelStatus").textContent = "Retrofit model is missing named simulation parts";
  }
  update3D(currentScenario.series, k);
}, undefined, (error) => {
  console.error("Could not load retrofit_plant.glb", error);
  document.getElementById("modelStatus").textContent = "3D model unavailable · open with run_viewer.cmd";
});

camera.position.set(32, 24, 34);
controls.target.set(0, 2, 0);
controls.update();
addTag("R290 ASHP bank", () => new THREE.Vector3(-3, 3.4, 7), (d, i) =>
  `${d.hp_th[i].toFixed(0)} kW dispatch / ${d.soc ? 170 : 305} kW installed`);
addTag("2 × 100 m³ TES", () => new THREE.Vector3(0, 6.1, -6), (d, i) =>
  d.soc ? `${d.soc[i].toFixed(1)}% thermal SoC` : "Bypassed · absent from direct scenario");
addTag("60 kWe connection", () => new THREE.Vector3(12, 3, -6), (d, i) =>
  `${d.p_grid[i].toFixed(1)} / 60.0 kWe`, "alert");
