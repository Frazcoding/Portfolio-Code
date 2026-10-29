const boatParts = {};
const water = new THREE.Mesh(new THREE.PlaneGeometry(24, 18),
  new THREE.MeshStandardMaterial({color: 0x20566b, roughness: .48, metalness: .18}));
water.rotation.x = -Math.PI/2;
water.position.y = -1.6;
scene.add(water);
new THREE.GLTFLoader().load("uniboat_cooling.glb", (gltf) => {
  gltf.scene.traverse((object) => {
    if (object.isMesh) {
      boatParts[object.name] = object;
      object.castShadow = true;
      object.receiveShadow = true;
    }
  });
  scene.add(gltf.scene);
  for (const name of ["BatteryPack", "DriveMotor", "SiC_Inverter", "RefrigerantPump", "SeawaterCondenser"]) {
    if (boatParts[name]) boatParts[name].material = boatParts[name].material.clone();
  }
  if (!["BatteryPack", "BatteryColdPlate", "DriveMotor", "SiC_Inverter", "RefrigerantPump", "Accumulator", "SeawaterCondenser"].every(name => boatParts[name])) {
    document.getElementById("modelStatus").textContent = "Boat model is missing named cooling parts";
  }
  update3D(currentScenario.series, k);
}, undefined, (error) => {
  console.error("Could not load uniboat_cooling.glb", error);
  document.getElementById("modelStatus").textContent = "3D model unavailable · open with run_viewer.cmd";
});
camera.position.set(11, 8, 11);
controls.target.set(0, .2, 0);
controls.update();
addTag("Battery + cold plate", () => new THREE.Vector3(-2.05, 2.45, -.62), (d, i) => `${d.q_batt[i].toFixed(2)} kW · ${d.t_batt[i].toFixed(1)} °C`);
addTag("Motor jacket", () => new THREE.Vector3(2.55, 2.45, -.5), (d, i) => `${d.q_mot[i].toFixed(2)} kW`);
addTag("SiC inverter", () => new THREE.Vector3(.65, 2.3, .76), (d, i) => `${d.q_inv[i].toFixed(2)} kW · ${d.t_inv[i].toFixed(1)} °C`);
addTag("Two-phase pump", () => new THREE.Vector3(-2.25, 2.3, .82), (d, i) => `${d.m_dot[i].toFixed(1)} g/s · ${d.p_pump[i].toFixed(1)} W`);
addTag("Seawater condenser", () => new THREE.Vector3(1.0, 2.6, -1.18), (d, i) => `${d.q_tot[i].toFixed(2)} kW · x=${d.x_exit[i].toFixed(2)}`);
