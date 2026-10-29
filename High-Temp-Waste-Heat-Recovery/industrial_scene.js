const industrialParts = {};
const industrialMeshes = [];
const ground = new THREE.Mesh(new THREE.PlaneGeometry(32, 20),
  new THREE.MeshStandardMaterial({color: 0xbac1c1, roughness: .92}));
ground.rotation.x = -Math.PI/2;
ground.position.y = -.06;
scene.add(ground);
const grid = new THREE.GridHelper(30, 15, 0x829190, 0x9aacab);
grid.position.y = -.02;
scene.add(grid);
new THREE.GLTFLoader().load("industrial_hthp.glb", (gltf) => {
  gltf.scene.traverse((object) => {
    if (object.isMesh) {
      industrialParts[object.name] = object;
      industrialMeshes.push(object);
      object.castShadow = true;
      object.receiveShadow = true;
    }
  });
  scene.add(gltf.scene);
  for (const name of ["Dairy_CondenserHX_Frame", "Steam_CondenserHX_Frame"]) {
    if (industrialParts[name]) industrialParts[name].material = industrialParts[name].material.clone();
  }
  if (!["Dairy_CompressorHousing", "Dairy_SourceHX_Frame", "Steam_CompressorHousing", "Steam_Separator"].every(name => industrialParts[name])) {
    document.getElementById("modelStatus").textContent = "Industrial model is missing named simulation parts";
  }
  update3D(currentScenario.series, k);
}, undefined, (error) => {
  console.error("Could not load industrial_hthp.glb", error);
  document.getElementById("modelStatus").textContent = "3D model unavailable · open with run_viewer.cmd";
});
camera.position.set(25, 20, 23);
controls.target.set(0, 1, 0);
controls.update();
const activeZ = () => currentScenarioKey === "flue_gas_steam" ? -3 : 3;
addTag("Source heat exchanger", () => new THREE.Vector3(-6.7, 3.3, activeZ()), (d, i) => `${d.q_recov[i].toFixed(0)} kW recovered · ${d.t_src_out[i].toFixed(1)} °C out`);
addTag("Screw compressor package", () => new THREE.Vector3(-2.2, 3.0, activeZ()), (d, i) => `${d.w_comp[i].toFixed(0)} kWe`);
addTag("Process condenser", () => new THREE.Vector3(3.2, 3.3, activeZ()), (d, i) => `${d.q_deliv[i].toFixed(0)} kW at ${d.t_deliv[i].toFixed(1)} °C`);
