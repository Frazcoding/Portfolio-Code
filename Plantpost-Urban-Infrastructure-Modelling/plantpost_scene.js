// The physical asset is authored in Blender and measured in metres.
const plantpostParts = {};
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(12, 12),
  new THREE.MeshStandardMaterial({color: 0xb4bdba, roughness: 0.95})
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.06;
scene.add(ground);
const grid = new THREE.GridHelper(8, 16, 0x829391, 0x9facaa);
grid.position.y = -0.005;
scene.add(grid);

const streetLight = new THREE.SpotLight(0xffe8a7, 0, 9, Math.PI / 3, 0.5);
streetLight.position.set(0, 4.24, 0);
streetLight.target.position.set(1.2, 0, 0);
scene.add(streetLight, streetLight.target);

new THREE.GLTFLoader().load("plantpost.glb", (gltf) => {
  gltf.scene.traverse((object) => {
    if (object.isMesh) {
      plantpostParts[object.name] = object;
      object.castShadow = true;
      object.receiveShadow = true;
    }
  });
  scene.add(gltf.scene);
  if (!["ReservoirWater", "Luminaire", "PVCanopy"].every(name => plantpostParts[name])) {
    document.getElementById("modelStatus").textContent = "Plantpost model part names do not match simulation bindings";
  }
  update3D(currentScenario.series, k);
}, undefined, (error) => {
  console.error("Could not load plantpost.glb", error);
  document.getElementById("modelStatus").textContent = "3D model unavailable · open with run_viewer.cmd";
});

camera.position.set(5, 5.1, 6.1);
controls.target.set(0, 2.2, 0);
controls.update();
addTag("2 m PV canopy", () => new THREE.Vector3(0, 4.7, 0), (d, i) =>
  d.p_pv ? `${d.p_pv[i].toFixed(0)} W` : "Output unavailable");
addTag("47.1 W luminaire", () => new THREE.Vector3(0.8, 4.25, 0), (d, i) =>
  `${(d.p_light ? d.p_light[i] : d.light_state ? d.light_state[i] : 0).toFixed(1)} W`);
addTag("Four planter tiers", () => new THREE.Vector3(0.7, 3.0, 0), (d, i) =>
  `VPD ${(d.vpd_val ? d.vpd_val[i] : d.vpd ? d.vpd[i] : 0).toFixed(2)} kPa`);
addTag("150 L reservoir", () => new THREE.Vector3(0.5, 0.85, 0), (d, i) =>
  `${d.v_tank[i].toFixed(1)} L · SoC ${d.soc[i].toFixed(0)}%`);
