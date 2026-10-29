const wlcMeshes = [];
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(110, 90),
  new THREE.MeshStandardMaterial({color: 0xaeb8b8, roughness: 0.95})
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.1;
scene.add(ground);
const grid = new THREE.GridHelper(100, 20, 0x809294, 0x9eaaab);
grid.position.y = -0.02;
scene.add(grid);

new THREE.GLTFLoader().load("wlc_office.glb", (gltf) => {
  gltf.scene.traverse((obj) => {
    if (obj.isMesh) {
      wlcMeshes.push(obj);
      obj.castShadow = true;
      obj.receiveShadow = true;
    }
  });
  scene.add(gltf.scene);
  if (!["GroundSlab", "RoofSlab", "BaselineBoiler"].every(name => wlcMeshes.some(mesh => mesh.name === name))) {
    document.getElementById("modelStatus").textContent = "Office model is missing named components";
  }
  update3D(currentScenario.series, k);
}, undefined, (error) => {
  console.error("Could not load wlc_office.glb", error);
  document.getElementById("modelStatus").textContent = "3D model unavailable · open with run_viewer.cmd";
});

camera.position.set(87, 64, 86);
controls.target.set(0, 10, 0);
controls.update();
addTag("50 × 30 m floorplate", () => new THREE.Vector3(-21, 21, 11), (d, i) =>
  `5 × 3.8 m · 7,500 m² GIA`);
addTag("Thermal plant", () => new THREE.Vector3(1, 23, -8), (d, i) =>
  `${d.plant_capacity[i].toFixed(1)} kW · ${currentScenario.heatingFuel === 'gas' ? 'gas heat / R410A cooling' : currentScenario.refrigerant}`);
addTag("Whole-life carbon", () => new THREE.Vector3(0, 8, 15), (d, i) =>
  `${d.cumul_carbon[i].toFixed(0)} t to year ${d.t[i]}`);
