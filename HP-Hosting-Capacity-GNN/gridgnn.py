"""GNN surrogate for low-voltage grid power flow, applied to heat-pump (HP) hosting capacity.

    python -m localml.gridgnn --net kerber_dorfnetz --generate 6000 --train --hosting

Pipeline: (1) random cold-winter-evening-peak scenarios on a pandapower network, solved with the full AC power
flow (ground truth); (2) an edge-aware message-passing network (GINEConv) learns bus voltage and branch loading
from the injections; (3) the trained surrogate is used for Monte-Carlo hosting capacity, validated against power
flow on a smaller sample.

Units
-----
Power in the scenario/feature layer is kW and kvar (demand positive in scenario arrays, injection = -demand in node
features). pandapower uses MW/MVar (converted /1000). Voltage in per unit (vm_pu, nominal 0.4 kV on the LV side).
Branch loading in percent of rated current (lines: max_i_ka; transformer: rated apparent power). Line r, x in ohm
(per-km value x length_km); transformer r, x are the short-circuit values referred to the LV side, in ohm.

Assumptions (all scenario parameters are *assumed typical values*, not measured data for this feeder)
-------------------------------------------------------------------------------------------------
| Item                         | Assumption                                                                   |
|------------------------------|------------------------------------------------------------------------------|
| Snapshot                     | Single cold-winter-evening peak (design day, about -10 degC ambient)         |
| Household base load          | P ~ U(0.5, 2.5) kW per household, independent; cos phi 0.95 inductive        |
| HP adoption                  | a ~ U(0, 1) per scenario; each household has an HP with probability a         |
| HP thermal design load       | Q_th ~ U(5, 12) kW (typical German single-family house, existing to           |
|                              | partly refurbished stock; roughly 40-100 W/m2 on 120-150 m2)                  |
| HP COP at -10 degC           | U(2.0, 3.0) (air-source units; EN 14511 A-10/W35 data-sheet range ~2.0-3.0)   |
| HP electrical demand         | P_el = Q_th / COP, i.e. about 1.7 - 6.0 kW, in addition to base load; cos phi |
|                              | 0.97 inductive (inverter-driven). No resistive back-up heater modelled        |
| Simultaneity                 | 1.0 at peak (every HP runs at full design load at the same time; conservative |
|                              | for a modulating HP, realistic only for the coldest hour)                      |
| Supply                       | Slack (ext_grid) at 1.0 pu, transformer tap at neutral, no OLTC / Q(U) control |
| Network                      | Balanced three-phase, symmetric positive-sequence power flow (pp.runpp)       |
| Violation limits             | Voltage: any bus < 0.94 pu (a stricter planning limit than the EN 50160 -10 %  |
|                              | = 0.90 pu, leaving margin for MV-side drop and unbalance). Overload: any line  |
|                              | or the transformer > 100 % loading                                            |
| Loads                        | Every pandapower load element gets its own household; P and Q are overwritten |
|                              | (the networks' original load values are ignored)                              |

Graph: nodes = buses; node features = [injected P kW, injected Q kvar, has_hp, base kW, is_slack, hops from slack,
km from slack, downstream demand kW, downstream demand kvar]. The last two are the sum of demand in the BFS subtree
below the bus (exact for radial feeders such as the Kerber networks; a BFS-tree approximation otherwise). They are
cheap, topology-only aggregates that give a 5-6 layer network access to the whole downstream load that sets the
voltage drop; set `use_downstream=False` to drop them. Edges = lines + 2-winding transformers (both directions
for message passing); edge features = [r ohm, x ohm, max_i_ka (transformer: rated LV current), length_km,
is_trafo]. Node head -> vm_pu; edge head on [h_u, h_v, edge_attr], averaged over both orientations -> loading %.

Limitations: synthetic benchmark feeder (Kerber 2011 Dorfnetz), not the user's own network; peak-only snapshot (no
time series, diversity or thermal storage); no PV, batteries or EV; balanced three-phase power flow (no unbalance
or neutral); no tap changer or voltage control; surrogate is only valid for the trained topology and load ranges
(it does not generalise to other networks or outages without retraining).
"""

from localml.gpu import DEVICE, gpu_lock, outputs  # noqa: I001  (import first: sets up DLL paths)

import argparse
import json
import math
import time
from multiprocessing import Pool
from pathlib import Path

import networkx as nx
import numpy as np
import pandapower as pp
import pandapower.networks as pn
import torch
import torch.nn as nn
from torch_geometric.nn import GINEConv

V_LIMIT = 0.94  # pu, voltage violation threshold
LOAD_LIMIT = 100.0  # %, branch overload threshold
TAN_BASE = math.tan(math.acos(0.95))
TAN_HP = math.tan(math.acos(0.97))
BASE_RANGE = (0.5, 2.5)  # kW
QTH_RANGE = (5.0, 12.0)  # kW thermal
COP_RANGE = (2.0, 3.0)

NETS = {
    "kerber_dorfnetz": pn.create_kerber_dorfnetz,
    "mv_oberrhein": pn.mv_oberrhein,
}


def out_dir() -> Path:
    return outputs("gridgnn")


def get_net(name: str):
    if name not in NETS:
        raise ValueError(f"unknown net {name!r}; choose from {sorted(NETS)}")
    return NETS[name]()


# --------------------------------------------------------------------------------------------- graph
_GRAPH_CACHE: dict = {}


def build_graph(net_name: str) -> dict:
    """Static topology tensors/arrays for a network (cached)."""
    if net_name in _GRAPH_CACHE:
        return _GRAPH_CACHE[net_name]
    net = get_net(net_name)
    bus_ids = list(net.bus.index)
    pos = {b: i for i, b in enumerate(bus_ids)}
    nb = len(bus_ids)

    lines = net.line[net.line.in_service]
    trafos = net.trafo[net.trafo.in_service]
    ei, ea, line_idx = [], [], []
    for i, r in lines.iterrows():
        ei.append((pos[r.from_bus], pos[r.to_bus]))
        L = r.length_km
        ea.append([r.r_ohm_per_km * L / r.parallel, r.x_ohm_per_km * L / r.parallel,
                   r.max_i_ka * r.parallel * r.df, L, 0.0])
        line_idx.append(i)
    trafo_idx = []
    for i, r in trafos.iterrows():
        ei.append((pos[r.hv_bus], pos[r.lv_bus]))
        zb = r.vn_lv_kv**2 / r.sn_mva  # ohm on LV side
        z, rr = r.vk_percent / 100 * zb, r.vkr_percent / 100 * zb
        xx = math.sqrt(max(z * z - rr * rr, 0.0))
        i_rated = r.sn_mva / (math.sqrt(3) * r.vn_lv_kv)  # kA
        ea.append([rr / r.parallel, xx / r.parallel, i_rated * r.parallel, 0.0, 1.0])
        trafo_idx.append(i)
    ei = np.array(ei, dtype=np.int64).T
    ea = np.array(ea, dtype=np.float32)
    n_line = len(line_idx)

    G = nx.Graph()
    G.add_nodes_from(range(nb))
    for k, (u, v) in enumerate(ei.T):
        G.add_edge(int(u), int(v), km=float(ea[k, 3]))
    slack = np.zeros(nb, dtype=bool)
    for b in net.ext_grid.bus:
        slack[pos[b]] = True
    src = list(np.flatnonzero(slack))
    hops = np.zeros(nb, dtype=np.float32)
    km = np.zeros(nb, dtype=np.float32)
    for s in src:
        pass
    h = nx.multi_source_dijkstra_path_length(G, src, weight=lambda u, v, d: 1.0)
    k_ = nx.multi_source_dijkstra_path_length(G, src, weight="km")
    for b in range(nb):
        hops[b] = h.get(b, 0.0)
        km[b] = k_.get(b, 0.0)

    # BFS tree -> descendant matrix D[i, j] = 1 if j is in subtree of i (incl. i)
    D = np.eye(nb, dtype=np.float32)
    order, parent, seen = [], {}, set(src)
    frontier = list(src)
    while frontier:
        nxt = []
        for u in frontier:
            order.append(u)
            for v in G.neighbors(u):
                if v not in seen:
                    seen.add(v)
                    parent[v] = u
                    nxt.append(v)
        frontier = nxt
    for v in reversed(order):
        if v in parent:
            D[parent[v]] = np.maximum(D[parent[v]], D[v])

    load_bus = np.array([pos[b] for b in net.load.bus], dtype=np.int64)
    M = np.zeros((len(load_bus), nb), dtype=np.float32)  # load -> bus aggregation
    M[np.arange(len(load_bus)), load_bus] = 1.0

    g = dict(nb=nb, n_edges=ei.shape[1], n_line=n_line, edge_index=ei, edge_attr=ea, slack=slack, hops=hops,
             km=km, D=D, M=M, n_loads=len(load_bus), line_idx=line_idx, trafo_idx=trafo_idx)
    _GRAPH_CACHE[net_name] = g
    return g


# ------------------------------------------------------------------------------------------ scenarios
def sample_scenarios(net_name: str, n: int, seed: int = 0, adoption=None) -> dict:
    """Random peak scenarios. adoption: None -> a ~ U(0,1) per scenario; float -> fixed; array -> per scenario.
    Returns per-load arrays in kW (base_kw, hp_kw) and has_hp (0/1), shape (n, n_loads)."""
    L = build_graph(net_name)["n_loads"]
    rng = np.random.default_rng(seed)
    if adoption is None:
        a = rng.uniform(0, 1, n)
    else:
        a = np.broadcast_to(np.asarray(adoption, dtype=float), (n,)).copy()
    base = rng.uniform(*BASE_RANGE, (n, L))
    has = (rng.uniform(0, 1, (n, L)) < a[:, None]).astype(np.float32)
    hp = rng.uniform(*QTH_RANGE, (n, L)) / rng.uniform(*COP_RANGE, (n, L)) * has
    return dict(base_kw=base.astype(np.float32), hp_kw=hp.astype(np.float32), has_hp=has,
                adoption=a.astype(np.float32))


def _pq_kw(sc: dict):
    p = sc["base_kw"] + sc["hp_kw"]
    q = sc["base_kw"] * TAN_BASE + sc["hp_kw"] * TAN_HP
    return p, q


_W: dict = {}


def _worker_init(net_name):
    _W["net"] = get_net(net_name)
    _W["g"] = build_graph(net_name)


def _solve_chunk(args):
    p_kw, q_kw = args
    net, g = _W["net"], _W["g"]
    n = len(p_kw)
    vm = np.full((n, g["nb"]), np.nan, dtype=np.float32)
    ld = np.full((n, g["n_edges"]), np.nan, dtype=np.float32)
    for i in range(n):
        net.load["p_mw"] = p_kw[i] / 1000.0
        net.load["q_mvar"] = q_kw[i] / 1000.0
        try:
            pp.runpp(net)
        except pp.LoadflowNotConverged:
            continue
        vm[i] = net.res_bus.vm_pu.values
        ld[i, : g["n_line"]] = net.res_line.loading_percent.values[
            [net.line.index.get_loc(j) for j in g["line_idx"]]]
        ld[i, g["n_line"]:] = net.res_trafo.loading_percent.values[
            [net.trafo.index.get_loc(j) for j in g["trafo_idx"]]]
    return vm, ld


def run_powerflow(net_name: str, sc: dict, workers: int = 6):
    """Solve scenarios with pandapower. Returns (vm_pu (n, nb), loading % (n, n_edges)); NaN if not converged."""
    p, q = _pq_kw(sc)
    n = len(p)
    if workers <= 1:
        _worker_init(net_name)
        return _solve_chunk((p, q))
    chunks = [(p[i:i + 50], q[i:i + 50]) for i in range(0, n, 50)]
    with Pool(workers, initializer=_worker_init, initargs=(net_name,)) as pool:
        res = pool.map(_solve_chunk, chunks)
    return np.concatenate([r[0] for r in res]), np.concatenate([r[1] for r in res])


def generate_dataset(net_name: str = "kerber_dorfnetz", n: int = 6000, workers: int = 6, seed: int = 0,
                     path=None, force: bool = False) -> dict:
    """Generate (or load cached) dataset; cached at outputs/gridgnn/dataset_<net>.pt. Drops non-converged cases."""
    path = Path(path) if path else out_dir() / f"dataset_{net_name}.pt"
    if path.exists() and not force:
        d = torch.load(path, weights_only=False)
        if d["n_requested"] == n:
            return d
    sc = sample_scenarios(net_name, n, seed)
    t0 = time.perf_counter()
    vm, ld = run_powerflow(net_name, sc, workers)
    dt = time.perf_counter() - t0
    ok = np.isfinite(vm).all(1) & np.isfinite(ld).all(1)
    d = {k: torch.from_numpy(v[ok]) for k, v in sc.items()}
    d.update(vm=torch.from_numpy(vm[ok]), loading=torch.from_numpy(ld[ok]), net_name=net_name, n_requested=n,
             n_converged=int(ok.sum()), pf_seconds=dt, pf_workers=workers, seed=seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(d, path)
    print(f"[{net_name}] {int(ok.sum())}/{n} converged ({100 * ok.mean():.2f} %), {dt:.1f} s with {workers} workers")
    return d


# ---------------------------------------------------------------------------------------------- model
NODE_SCALE = dict(p=10.0, q=3.0, base=2.5)


def node_features(net_name: str, sc: dict, use_downstream: bool = True) -> torch.Tensor:
    """(n, nb, F) float32 node-feature tensor from per-load scenario arrays."""
    g = build_graph(net_name)
    p, q = _pq_kw(sc)
    M, D = g["M"], g["D"]
    P, Q = p @ M, q @ M  # demand per bus, kW / kvar
    has = ((np.asarray(sc["has_hp"]) @ M) > 0).astype(np.float32)
    base = np.asarray(sc["base_kw"]) @ M
    n = len(P)
    cols = [-P / NODE_SCALE["p"], -Q / NODE_SCALE["q"], has, base / NODE_SCALE["base"],
            np.broadcast_to(g["slack"].astype(np.float32), (n, g["nb"])),
            np.broadcast_to(g["hops"] / max(g["hops"].max(), 1), (n, g["nb"])),
            np.broadcast_to(g["km"] / max(g["km"].max(), 1e-6), (n, g["nb"]))]
    if use_downstream:
        dp, dq = P @ D.T, Q @ D.T
        cols += [dp / (np.maximum(P.sum(1, keepdims=True), 1.0) * 0 + 100.0 * NODE_SCALE["p"] / 10),
                 dq / (np.maximum(Q.sum(1, keepdims=True), 1.0) * 0 + 100.0 * NODE_SCALE["q"] / 3)]
    return torch.from_numpy(np.stack(cols, -1).astype(np.float32))


def edge_features(net_name: str) -> torch.Tensor:
    ea = build_graph(net_name)["edge_attr"].copy()
    ea[:, :3] = ea[:, :3] / np.maximum(ea[:, :3].max(0), 1e-9)
    ea[:, 3] = ea[:, 3] / max(ea[:, 3].max(), 1e-9)
    return torch.from_numpy(ea)


class GridGNN(nn.Module):
    def __init__(self, node_dim, edge_dim, hidden=128, layers=5):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(node_dim, hidden), nn.ReLU(), nn.Linear(hidden, hidden))
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()
        for _ in range(layers):
            mlp = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, hidden))
            self.convs.append(GINEConv(mlp, train_eps=True, edge_dim=edge_dim))
            self.norms.append(nn.LayerNorm(hidden))
        self.node_head = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, 1))
        self.edge_head = nn.Sequential(nn.Linear(2 * hidden + edge_dim, hidden), nn.ReLU(), nn.Linear(hidden, 1))

    def forward(self, x, edge_index, edge_attr, e_u, e_v, e_attr):
        """x (N, F) stacked over batch; edge_index/edge_attr: both directions; e_u/e_v/e_attr: one entry per
        physical branch (stacked over batch). Returns (node_out (N,), edge_out (E,))."""
        h = self.enc(x)
        for conv, norm in zip(self.convs, self.norms):
            h = h + torch.relu(norm(conv(h, edge_index, edge_attr)))
        hu, hv = h[e_u], h[e_v]
        e = 0.5 * (self.edge_head(torch.cat([hu, hv, e_attr], -1)) + self.edge_head(torch.cat([hv, hu, e_attr], -1)))
        return self.node_head(h).squeeze(-1), e.squeeze(-1)


class _Batcher:
    """Builds PyG-style batched index tensors for B copies of the fixed topology."""

    def __init__(self, net_name, device):
        g = build_graph(net_name)
        self.nb, self.ne = g["nb"], g["n_edges"]
        ei = torch.from_numpy(g["edge_index"])
        self.ei = torch.cat([ei, ei.flip(0)], 1).to(device)
        self.ea = edge_features(net_name).to(device)
        self.dev = device
        self._cache: dict = {}

    def get(self, B):
        if B not in self._cache:
            off = (torch.arange(B, device=self.dev) * self.nb)
            ei = (self.ei[None] + off[:, None, None]).permute(1, 0, 2).reshape(2, -1)
            ea = torch.cat([self.ea, self.ea]).repeat(B, 1)
            u = (self.ei[0, : self.ne][None] + off[:, None]).reshape(-1)
            v = (self.ei[1, : self.ne][None] + off[:, None]).reshape(-1)
            self._cache[B] = (ei, ea, u, v, self.ea.repeat(B, 1))
        return self._cache[B]


def _forward(model, bt, x):
    B = x.shape[0]
    ei, ea, u, v, eb = bt.get(B)
    nv, el = model(x.reshape(B * bt.nb, -1), ei, ea, u, v, eb)
    return nv.view(B, bt.nb), el.view(B, bt.ne)


def _targets(vm, loading, norm, trafo_mask):
    tv = ((1 - vm) * 100 - norm["v_mu"]) / norm["v_sd"]
    mu = torch.where(trafo_mask, norm["t_mu"], norm["l_mu"])
    sd = torch.where(trafo_mask, norm["t_sd"], norm["l_sd"])
    return tv, (loading - mu) / sd


def _compute_norm(vm, loading, trafo_mask, slack):
    dv = ((1 - vm) * 100)[:, ~slack]
    lm = loading[:, ~trafo_mask]
    out = dict(v_mu=dv.mean(), v_sd=dv.std() + 1e-6, l_mu=lm.mean(), l_sd=lm.std() + 1e-6)
    if trafo_mask.any():
        tm = loading[:, trafo_mask]
        out.update(t_mu=tm.mean(), t_sd=tm.std() + 1e-6)
    else:
        out.update(t_mu=torch.tensor(0.0), t_sd=torch.tensor(1.0))
    return {k: float(v) for k, v in out.items()}


def _denorm(nv, el, norm, trafo_mask):
    vm = 1 - (nv * norm["v_sd"] + norm["v_mu"]) / 100
    mu = torch.where(trafo_mask, torch.tensor(norm["t_mu"], device=el.device), torch.tensor(norm["l_mu"], device=el.device))
    sd = torch.where(trafo_mask, torch.tensor(norm["t_sd"], device=el.device), torch.tensor(norm["l_sd"], device=el.device))
    return vm, el * sd + mu


def _masks(net_name, device):
    g = build_graph(net_name)
    tm = torch.zeros(g["n_edges"], dtype=torch.bool)
    tm[g["n_line"]:] = True
    return tm.to(device), torch.from_numpy(g["slack"]).to(device)


# --------------------------------------------------------------------------------------------- train
def model_path(net_name):
    return out_dir() / f"model_{net_name}.pt"


def violations(vm, loading):
    """vm (n, nb) incl. slack bus (excluded by caller via mask); returns bool arrays (voltage, overload)."""
    return (vm < V_LIMIT).any(1), (loading > LOAD_LIMIT).any(1)


def train(net_name: str = "kerber_dorfnetz", epochs: int = 150, hidden: int = 128, layers: int = 5,
          batch_size: int = 64, lr: float = 2e-3, seed: int = 0, use_downstream: bool = True,
          dataset=None, n: int = 6000, workers: int = 6, save_path=None, verbose: bool = True) -> dict:
    """Train on the cached dataset (generated if absent), evaluate on the 10 % test split, save the model."""
    d = dataset if isinstance(dataset, dict) else generate_dataset(net_name, n, workers, path=dataset)
    N = len(d["vm"])
    rng = np.random.default_rng(seed)
    perm = rng.permutation(N)
    n_tr, n_va = int(0.8 * N), int(0.1 * N)
    idx = dict(train=perm[:n_tr], val=perm[n_tr:n_tr + n_va], test=perm[n_tr + n_va:])
    g = build_graph(net_name)
    X = node_features(net_name, {k: d[k].numpy() for k in ("base_kw", "hp_kw", "has_hp")}, use_downstream)
    vm, ld = d["vm"], d["loading"]
    torch.manual_seed(seed)
    result: dict = {}
    with gpu_lock("gridgnn-train"):
        dev = DEVICE
        tmask, slack = _masks(net_name, dev)
        norm = _compute_norm(vm[idx["train"]], ld[idx["train"]], tmask.cpu(), slack.cpu())
        X, vm_d, ld_d = X.to(dev), vm.to(dev), ld.to(dev)
        tv, tl = _targets(vm_d, ld_d, {k: torch.tensor(v, device=dev) for k, v in norm.items()}, tmask)
        bt = _Batcher(net_name, dev)
        model = GridGNN(X.shape[-1], bt.ea.shape[-1], hidden, layers).to(dev)
        opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
        steps = epochs * math.ceil(len(idx["train"]) / batch_size)
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps, pct_start=0.1)
        tri = torch.from_numpy(idx["train"]).to(dev)
        vai = torch.from_numpy(idx["val"]).to(dev)
        keep = ~slack
        best, best_state, t0 = 1e9, None, time.perf_counter()

        def loss_on(b):
            nv, el = _forward(model, bt, X[b])
            return ((nv - tv[b])[:, keep] ** 2).mean() + ((el - tl[b]) ** 2).mean()

        for ep in range(epochs):
            model.train()
            sh = tri[torch.randperm(len(tri), device=dev)]
            for i in range(0, len(sh), batch_size):
                b = sh[i:i + batch_size]
                opt.zero_grad()
                loss_on(b).backward()
                nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                opt.step()
                sched.step()
            model.eval()
            with torch.no_grad():
                vl = float(np.mean([float(loss_on(vai[i:i + 256])) for i in range(0, len(vai), 256)]))
            if vl < best:
                best, best_state = vl, {k: v.detach().clone() for k, v in model.state_dict().items()}
            if verbose and (ep % 10 == 0 or ep == epochs - 1):
                print(f"epoch {ep:4d} val_loss {vl:.5f} best {best:.5f} ({time.perf_counter() - t0:.0f}s)")
        model.load_state_dict(best_state)
        train_s = time.perf_counter() - t0
        te = torch.from_numpy(idx["test"]).to(dev)
        metrics = _evaluate(model, bt, X[te], vm_d[te], ld_d[te], norm, tmask, slack)
        metrics.update(net=net_name, n_requested=d["n_requested"], n_converged=d["n_converged"],
                       n_train=len(idx["train"]), n_val=len(idx["val"]), n_test=len(idx["test"]),
                       epochs=epochs, best_val_loss=best, train_seconds=train_s, device=dev,
                       use_downstream=use_downstream)
        # mean-prediction baseline for voltage (train mean per bus)
        base = vm[idx["train"]].mean(0)
        metrics["baseline_vm_mae_pu"] = float((vm[idx["test"]] - base)[:, ~slack.cpu()].abs().mean())
        # speed
        metrics.update(_speed(net_name, model, norm, use_downstream, dev, workers))
        torch.save(dict(state=best_state, norm=norm, hidden=hidden, layers=layers, use_downstream=use_downstream,
                        node_dim=X.shape[-1], edge_dim=bt.ea.shape[-1], net_name=net_name, split=idx,
                        metrics=metrics), Path(save_path) if save_path else model_path(net_name))
    if not save_path:
        (out_dir() / f"metrics_{net_name}.json").write_text(json.dumps(metrics, indent=2))
    result = metrics
    if verbose:
        print(json.dumps(result, indent=2))
    return result


@torch.no_grad()
def _evaluate(model, bt, X, vm, ld, norm, tmask, slack):
    model.eval()
    pv, pl = [], []
    for i in range(0, len(X), 256):
        nv, el = _forward(model, bt, X[i:i + 256])
        a, b = _denorm(nv, el, norm, tmask)
        pv.append(a), pl.append(b)
    pv, pl = torch.cat(pv), torch.cat(pl)
    keep = ~slack
    ev = (pv - vm)[:, keep].abs()
    el = (pl - ld).abs()
    vv_t, ov_t = (vm[:, keep] < V_LIMIT).any(1), (ld > LOAD_LIMIT).any(1)
    vv_p, ov_p = (pv[:, keep] < V_LIMIT).any(1), (pl > LOAD_LIMIT).any(1)
    acc = lambda a, b: float((a == b).float().mean())  # noqa: E731
    return dict(
        voltage_mae_pu=float(ev.mean()), voltage_max_abs_err_pu=float(ev.max()),
        line_loading_mae_pp=float(el[:, ~tmask].mean()), line_loading_max_abs_err_pp=float(el[:, ~tmask].max()),
        trafo_loading_mae_pp=float(el[:, tmask].mean()) if tmask.any() else None,
        voltage_violation_acc=acc(vv_t, vv_p), overload_acc=acc(ov_t, ov_p),
        voltage_violation_rate_true=float(vv_t.float().mean()), overload_rate_true=float(ov_t.float().mean()),
        voltage_range_pu=[float(vm[:, keep].min()), float(vm[:, keep].max())],
        loading_range_pct=[float(ld.min()), float(ld.max())],
    )


# ----------------------------------------------------------------------------------------------- predict
_MODELS: dict = {}


def load_model(net_name: str, device=None):
    device = device or DEVICE
    key = (net_name, device)
    if key not in _MODELS:
        ck = torch.load(model_path(net_name), weights_only=False, map_location=device)
        m = GridGNN(ck["node_dim"], ck["edge_dim"], ck["hidden"], ck["layers"]).to(device)
        m.load_state_dict(ck["state"])
        m.eval()
        _MODELS[key] = (m, ck)
    return _MODELS[key]


@torch.no_grad()
def predict(net_name: str, scenarios: dict, batch_size: int = 1024, device=None):
    """Surrogate prediction. Returns (vm_pu (n, nb), loading % (n, n_edges: lines then transformers)) as numpy."""
    device = device or DEVICE
    model, ck = load_model(net_name, device)
    bt = _Batcher(net_name, device)
    tmask, _ = _masks(net_name, device)
    X = node_features(net_name, scenarios, ck["use_downstream"])
    vs, ls = [], []
    for i in range(0, len(X), batch_size):
        nv, el = _forward(model, bt, X[i:i + batch_size].to(device))
        v, l_ = _denorm(nv, el, ck["norm"], tmask)
        vs.append(v.cpu()), ls.append(l_.cpu())
    return torch.cat(vs).numpy(), torch.cat(ls).numpy()


def _speed(net_name, model, norm, use_downstream, dev, workers, n_gnn=4096, n_pf=120):
    sc = sample_scenarios(net_name, n_gnn, seed=123)
    bt = _Batcher(net_name, dev)
    tmask, _ = _masks(net_name, dev)

    def run():
        X = node_features(net_name, sc, use_downstream).to(dev)
        with torch.no_grad():
            for i in range(0, n_gnn, 1024):
                _denorm(*_forward(model, bt, X[i:i + 1024]), norm, tmask)
        if dev == "cuda":
            torch.cuda.synchronize()

    run()  # warm-up
    t0 = time.perf_counter()
    run()
    gnn = n_gnn / (time.perf_counter() - t0)
    sub = {k: v[:n_pf] for k, v in sc.items()}
    t0 = time.perf_counter()
    run_powerflow(net_name, sub, 1)
    pf1 = n_pf / (time.perf_counter() - t0)
    return dict(gnn_scenarios_per_s=gnn, pandapower_scenarios_per_s_1core=pf1,
                speedup_vs_1core=gnn / pf1, speedup_vs_6core_est=gnn / (pf1 * min(workers, 6)))


# ----------------------------------------------------------------------------------------- hosting
def _crossing(x, y, thr=0.10):
    """First x where y crosses thr (linear interpolation); nan if never."""
    for i in range(len(x)):
        if y[i] >= thr:
            if i == 0:
                return float(x[0])
            return float(x[i - 1] + (thr - y[i - 1]) * (x[i] - x[i - 1]) / (y[i] - y[i - 1]))
    return float("nan")


def hosting_capacity(net_name: str = "kerber_dorfnetz", n_gnn: int = 2000, n_pf: int = 100, step: float = 0.05,
                     workers: int = 6, seed: int = 1000, save: bool = True):
    """P(violation) vs HP adoption from the GNN (n_gnn per step) and power flow (n_pf per step).
    Returns (DataFrame, png path). Needs a trained model."""
    import matplotlib
    import pandas as pd
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    g = build_graph(net_name)
    keep = ~g["slack"]
    levels = np.round(np.arange(0, 1 + 1e-9, step), 4)
    rows = []
    with gpu_lock("gridgnn-hosting"):
        for k, a in enumerate(levels):
            sc = sample_scenarios(net_name, n_gnn, seed + k, adoption=a)
            vm, ld = predict(net_name, sc)
            v, o = (vm[:, keep] < V_LIMIT).any(1), (ld > LOAD_LIMIT).any(1)
            sp = {key: val[:n_pf] for key, val in sample_scenarios(net_name, n_pf, seed + 5000 + k, adoption=a).items()}
            rows.append(dict(adoption=a, gnn_p_voltage=v.mean(), gnn_p_overload=o.mean(), gnn_p_any=(v | o).mean(),
                             _sp=sp))
    # power-flow ground truth (CPU pool, outside the GPU lock)
    allsc = {key: np.concatenate([r["_sp"][key] for r in rows]) for key in rows[0]["_sp"]}
    vm, ld = run_powerflow(net_name, allsc, workers)
    for k, r in enumerate(rows):
        sl = slice(k * n_pf, (k + 1) * n_pf)
        ok = np.isfinite(vm[sl]).all(1) & np.isfinite(ld[sl]).all(1)
        v = (vm[sl][ok][:, keep] < V_LIMIT).any(1)
        o = (ld[sl][ok] > LOAD_LIMIT).any(1)
        r.update(pf_p_voltage=v.mean(), pf_p_overload=o.mean(), pf_p_any=(v | o).mean(), pf_n=int(ok.sum()))
        del r["_sp"]
    df = pd.DataFrame(rows)
    cross = {f"{m}_{c}": _crossing(df.adoption.values * 100, df[f"{m}_p_{c}"].values)
             for m in ("gnn", "pf") for c in ("voltage", "overload", "any")}
    df.attrs["crossing_10pct_adoption_percent"] = cross

    fig, ax = plt.subplots(figsize=(8, 5))
    pfn = df.pf_n.clip(lower=1)
    for col, name, c in (("voltage", "voltage < 0.94 pu", "tab:blue"), ("overload", "line/trafo > 100 %", "tab:red"),
                         ("any", "any violation", "k")):
        ax.plot(df.adoption * 100, df[f"gnn_p_{col}"], "-", color=c, label=f"GNN: {name}")
        p = df[f"pf_p_{col}"]
        ax.errorbar(df.adoption * 100, p, yerr=1.96 * np.sqrt(p * (1 - p) / pfn), fmt="o", ms=4, color=c, alpha=0.7,
                    capsize=2, label=f"Power flow ({n_pf}/step): {name}")
    ax.axhline(0.10, color="grey", ls="--", lw=1)
    ax.set(xlabel="Heat-pump adoption (% of households)", ylabel="Probability of violation",
           title=f"HP hosting capacity, {net_name} (winter-evening peak, simultaneity 1.0)", ylim=(-0.02, 1.02))
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    png = out_dir() / f"hosting_capacity_{net_name}.png"
    if save:
        fig.savefig(png, dpi=150)
        df.to_csv(out_dir() / f"hosting_capacity_{net_name}.csv", index=False)
        (out_dir() / f"hosting_crossings_{net_name}.json").write_text(json.dumps(cross, indent=2))
    plt.close(fig)
    return df, png


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--net", default="kerber_dorfnetz", choices=sorted(NETS))
    ap.add_argument("--generate", type=int, metavar="N", help="generate N scenarios (power flow, cached)")
    ap.add_argument("--train", action="store_true")
    ap.add_argument("--hosting", action="store_true")
    ap.add_argument("--epochs", type=int, default=150)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    if a.generate:
        generate_dataset(a.net, a.generate, a.workers, force=True)
    if a.train:
        train(a.net, a.epochs, workers=a.workers)
    if a.hosting:
        df, png = hosting_capacity(a.net, workers=a.workers)
        print(df.round(3).to_string())
        print(df.attrs["crossing_10pct_adoption_percent"])
        print(png)


if __name__ == "__main__":
    main()
