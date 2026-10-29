const rigParts = {};
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(12, 10),
  new THREE.MeshStandardMaterial({color: 0xb8c0c0, roughness: .93})
);
ground.rotation.x = -Math.PI/2;
ground.position.y = -.08;
scene.add(ground);
const grid = new THREE.GridHelper(12, 12, 0x819293, 0x9dabac);
grid.position.y = -.03;
scene.add(grid);
new THREE.GLTFLoader().load("heatpump_rig.glb", (gltf) => {
  gltf.scene.traverse((object) => {
    if (object.isMesh) {
      rigParts[object.name] = object;
      object.castShadow = true;
      object.receiveShadow = true;
    }
  });
  scene.add(gltf.scene);
  if (rigParts.Condenser_Frame) rigParts.Condenser_Frame.material = rigParts.Condenser_Frame.material.clone();
  if (rigParts.HP_Compressor) rigParts.HP_Compressor.material = rigParts.HP_Compressor.material.clone();
  if (!["LP_Compressor_A", "LP_Compressor_B", "HP_Compressor", "Flash_Economiser", "Condenser_Frame", "Evaporator_Frame"].every(name => rigParts[name])) {
    document.getElementById("modelStatus").textContent = "Rig model is missing named simulation parts";
  }
  update3D(currentScenario.series, k);
}, undefined, (error) => {
  console.error("Could not load heatpump_rig.glb", error);
  document.getElementById("modelStatus").textContent = "3D model unavailable · open with run_viewer.cmd";
});
camera.position.set(8, 6, 9);
controls.target.set(0, .9, 0);
controls.update();
addTag("LP scroll pair · 154 m³/h nominal", () => new THREE.Vector3(-2.3, 2.5, 1.1), (d, i) => `${d.p_e[i].toFixed(2)} bar suction`);
addTag("HP scroll · 77 m³/h nominal", () => new THREE.Vector3(.7, 2.3, 1.2), (d, i) => `${d.t_dis[i].toFixed(1)} °C discharge`);
addTag("Flash economiser", () => new THREE.Vector3(-.6, 3.3, -1.0), (d, i) => `${d.p_int[i].toFixed(2)} bar`);
addTag("Plate condenser", () => new THREE.Vector3(1.9, 2.4, -.7), (d, i) => `${d.q_cond[i].toFixed(1)} kWth`);
addTag("Evaporator", () => new THREE.Vector3(-2.2, 2.4, -.7), (d, i) => `${d.q_evap[i].toFixed(1)} kWth`);
