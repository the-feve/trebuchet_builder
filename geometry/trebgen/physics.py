"""Throw simulation for a hinged-counterweight trebuchet with a sling.

Planar model in the X-Z plane, three angles (absolute, from +X, counter-
clockwise): theta (long side of the arm), psi (hinge to counterweight centre)
and sigma (sling, tip to projectile). The arm is a rigid body on the axle;
the counterweight and projectile are point masses; the sling is massless and
always taut. Lagrange's equations are written from the point positions, which
are sums of L·(cos q, sin q) terms, so the mass matrix and velocity terms
come straight from those sums.

Phases:
1. The projectile slides along the trough (a constraint z = const with a
   normal force; no friction) until the sling lifts it.
2. It swings free in the sling until the sling-to-arm angle drops to the
   release angle (set by the bend of the release pin).
3. Free flight with air drag (sphere, Cd 0.47) to the table's height.

Nothing here models friction in the axle or hinge, pouch drag on the trough,
sling stretch or the arm flexing; real throws land short of this. See
REAL_WORLD for the factor the report uses until test throws calibrate it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

G = 9.81
RHO_AIR = 1.2
CD_SPHERE = 0.47
REAL_WORLD = (0.6, 0.85)  # expected fraction of the model's range on the table


@dataclass
class Machine:
    """SI units (m, kg, s)."""
    L1: float
    L2: float
    Lc: float
    Ls: float
    H: float
    alpha: float
    z_p0: float        # projectile centre at rest
    m_arm: float
    d_arm: float       # arm COM from the pivot along the long side
    I_arm: float       # about the pivot
    m_cw: float
    m_p: float
    d_p: float         # projectile diameter

    @classmethod
    def from_derived(cls, d) -> "Machine":
        mm, g = 1e-3, 1e-3
        return cls(L1=d.L1 * mm, L2=d.L2 * mm, Lc=d.Lc * mm, Ls=d.Ls * mm, H=d.H * mm, alpha=d.alpha,
                   z_p0=(d.z_trough + d.r_p) * mm, m_arm=d.arm["mass"] * g, d_arm=d.arm["com"] * mm,
                   I_arm=d.arm["inertia"] * g * mm * mm, m_cw=d.m_cw * g, m_p=d.m_p * g, d_p=2 * d.r_p * mm)

    def start(self) -> np.ndarray:
        """[theta, psi, sigma] at rest: long arm down and back, bucket hanging,
        sling lying forward along the trough."""
        th = math.pi + self.alpha
        tip_z = self.H + self.L1 * math.sin(th)
        s = math.asin(max(-1.0, min(1.0, (self.z_p0 - tip_z) / self.Ls)))
        return np.array([th, -math.pi / 2, s])

    # Each point is a list of (length, angle index) terms, relative to the axle.
    def _points(self):
        return [(self.m_cw, ((-self.L2, 0), (self.Lc, 1))),
                (self.m_p, ((self.L1, 0), (self.Ls, 2)))]

    @staticmethod
    def _pos(terms, q):
        return np.array([sum(c * math.cos(q[k]) for c, k in terms), sum(c * math.sin(q[k]) for c, k in terms)])

    @staticmethod
    def _jac(terms, q):
        J = np.zeros((2, 3))
        for c, k in terms:
            J[0, k] += -c * math.sin(q[k])
            J[1, k] += c * math.cos(q[k])
        return J

    @staticmethod
    def _bias(terms, q, qd):
        """J̇·q̇: the velocity-dependent part of the point's acceleration."""
        return np.array([sum(-c * math.cos(q[k]) * qd[k] ** 2 for c, k in terms),
                         sum(-c * math.sin(q[k]) * qd[k] ** 2 for c, k in terms)])

    def accel(self, q, qd, on_trough: bool) -> tuple[np.ndarray, float]:
        """q̈ and the trough's push on the projectile (N; 0 when free)."""
        M = np.zeros((3, 3))
        f = np.zeros(3)
        M[0, 0] += self.I_arm
        f[0] += -self.m_arm * G * self.d_arm * math.cos(q[0])
        for m, terms in self._points():
            J = self._jac(terms, q)
            a = self._bias(terms, q, qd)
            M += m * J.T @ J
            f += m * J.T @ (np.array([0.0, -G]) - a)
        if not on_trough:
            return np.linalg.solve(M, f), 0.0
        proj = self._points()[1][1]
        A = self._jac(proj, q)[1]
        b = -self._bias(proj, q, qd)[1]
        K = np.zeros((4, 4))
        K[:3, :3] = M
        K[:3, 3] = -A
        K[3, :3] = A
        sol = np.linalg.solve(K, np.concatenate([f, [b]]))
        return sol[:3], sol[3]

    def projectile(self, q, qd):
        """Position (from the table, x from the axle) and velocity."""
        terms = self._points()[1][1]
        p = self._pos(terms, q) + np.array([0.0, self.H])
        return p, self._jac(terms, q) @ qd

    def cw_drop_max(self, q0) -> float:
        """How far the counterweight's centre can fall from rest (m)."""
        z0 = self._pos(self._points()[0][1], q0)[1]
        return z0 - (-self.L2 - self.Lc)


@dataclass
class Swing:
    t: np.ndarray
    q: np.ndarray       # (n, 3)
    qd: np.ndarray
    free: np.ndarray    # bool: projectile off the trough
    delta: np.ndarray   # sling-to-arm angle (rad): pi - alpha at rest, 0 when straight out
    liftoff_t: float | None
    max_sling_pull: float  # N, while free
    problem: str | None


def swing(m: Machine, dt: float = 2e-4, t_max: float = 1.5) -> Swing:
    """Run phases 1-2 without releasing, until the sling has swung 30° past
    straight (or time runs out), recording every step."""
    q = m.start()
    qd = np.zeros(3)
    on = True
    ts, qs, qds, frees, deltas = [], [], [], [], []
    liftoff = None
    max_pull = 0.0
    problem = None
    t = 0.0
    a0, _ = m.accel(q, qd, True)
    if a0[0] >= 0:  # the long arm should start swinging up (theta falling)
        return Swing(np.array([0.0]), q[None], qd[None], np.array([False]), np.array([math.pi - m.alpha]), None, 0.0,
                     "The counterweight is too light to lift the arm and projectile.")
    while t < t_max:
        # The angles are integrated, so never wrap: the sling starts folded
        # back along the arm (about pi - alpha) and is straight out at 0.
        delta = q[2] - q[0] + 2 * math.pi
        ts.append(t); qs.append(q.copy()); qds.append(qd.copy()); frees.append(not on); deltas.append(delta)
        if delta < -math.radians(30):
            break
        if on:
            _, lam = m.accel(q, qd, True)
            if lam <= 0:
                on = False
                liftoff = t
        if not on:
            # Sling pull = projectile mass × (its acceleration + g), from the free equations.
            a, _ = m.accel(q, qd, False)
            terms = m._points()[1][1]
            acc = m._jac(terms, q) @ a + m._bias(terms, q, qd)
            max_pull = max(max_pull, m.m_p * float(np.hypot(acc[0], acc[1] + G)))
            p, _ = m.projectile(q, qd)
            if p[1] < m.z_p0 - 0.02:
                problem = "The projectile drags back into the trough; try a longer arm or a shorter sling."
                break

        def f(state):
            qq, vv = state[:3], state[3:]
            acc, _ = m.accel(qq, vv, on)
            return np.concatenate([vv, acc])

        s = np.concatenate([q, qd])
        k1 = f(s)
        k2 = f(s + dt / 2 * k1)
        k3 = f(s + dt / 2 * k2)
        k4 = f(s + dt * k3)
        s = s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        q, qd = s[:3], s[3:]
        t += dt
    if liftoff is None and problem is None:
        problem = "The sling never lifts the projectile off the trough; try a heavier counterweight or a lighter projectile."
    return Swing(np.array(ts), np.array(qs), np.array(qds), np.array(frees), np.array(deltas), liftoff, max_pull, problem)


def fly(p0: np.ndarray, v0: np.ndarray, m_p: float, d_p: float, z_land: float, dt: float = 1e-3, t_max: float = 30.0):
    """Flight with quadratic drag for many shots at once. p0, v0: (n, 2)
    in m and m/s. Returns landing x (m), flight time (s), peak height (m)
    and the sampled path of each shot (list of (k, 2) arrays, every 10 ms)."""
    k = 0.5 * RHO_AIR * CD_SPHERE * math.pi * (d_p / 2) ** 2 / m_p
    p = p0.astype(float).copy()
    v = v0.astype(float).copy()
    n = len(p)
    done = np.zeros(n, bool)
    land_x = np.full(n, np.nan)
    land_t = np.full(n, np.nan)
    peak = p[:, 1].copy()
    paths = [[p[i].copy()] for i in range(n)]
    t = 0.0
    step = 0

    def acc(v):
        sp = np.hypot(v[:, 0], v[:, 1])[:, None]
        return np.array([0.0, -G]) - k * sp * v

    while not done.all() and t < t_max:
        # Midpoint (RK2) step.
        a1 = acc(v)
        vm = v + a1 * dt / 2
        pn = p + vm * dt
        vn = v + acc(vm) * dt
        hit = (~done) & (pn[:, 1] <= z_land) & (vn[:, 1] < 0)
        if hit.any():
            f = (p[hit, 1] - z_land) / np.maximum(p[hit, 1] - pn[hit, 1], 1e-12)
            land_x[hit] = p[hit, 0] + f * (pn[hit, 0] - p[hit, 0])
            land_t[hit] = t + f * dt
            done |= hit
        live = ~done
        p[live], v[live] = pn[live], vn[live]
        peak = np.maximum(peak, p[:, 1])
        t += dt
        step += 1
        if step % 10 == 0:
            for i in np.flatnonzero(live):
                paths[i].append(p[i].copy())
    for i in range(n):
        if not math.isnan(land_x[i]):
            paths[i].append(np.array([land_x[i], z_land]))
    return land_x, land_t, peak, [np.array(pp) for pp in paths]


@dataclass
class Throw:
    ok: bool
    problem: str | None
    release_angle_deg: float | None      # used (sling to arm)
    best_release_angle_deg: float | None
    range_m: float | None                # from the axle, model
    best_range_m: float | None
    release_speed: float | None
    launch_angle_deg: float | None
    release_height_m: float | None
    release_t: float | None
    flight_time: float | None
    peak_height_m: float | None
    liftoff_t: float | None
    max_sling_pull_n: float
    energy_j: float                       # counterweight's full drop
    efficiency: float | None              # projectile KE at release / energy_j
    range_efficiency: float | None        # range / vacuum range at 100% (2·m_cw·h/m_p)
    sweep: list                           # [(release angle deg, range m)] for the chart
    path: list                            # [[x, z]] flight path (m)
    frames: list                          # [[t, theta, psi, sigma]] swing to release, ~5 ms apart

    def expected_range(self) -> tuple[float, float] | None:
        if self.range_m is None:
            return None
        return (self.range_m * REAL_WORLD[0], self.range_m * REAL_WORLD[1])


def simulate(m: Machine, release_angle_deg: float | None = None) -> Throw:
    """The full throw. release_angle_deg None = use the best one."""
    q0 = m.start()
    energy = m.m_cw * G * m.cw_drop_max(q0)
    sw = swing(m)
    empty = Throw(False, sw.problem, None, None, None, None, None, None, None, None, None, None, sw.liftoff_t,
                  sw.max_sling_pull, energy, None, None, [], [], [])
    idx = np.flatnonzero(sw.free & (sw.delta > 0) & (sw.delta < math.pi - m.alpha))
    if sw.problem and not len(idx):
        return empty
    if not len(idx):
        empty.problem = "The sling never swings round far enough to release."
        return empty
    # Candidate releases: every 5th free step (1 ms).
    cand = idx[::5]
    P, V = [], []
    for i in cand:
        p, v = m.projectile(sw.q[i], sw.qd[i])
        P.append(p); V.append(v)
    P, V = np.array(P), np.array(V)
    land, tf, peak, paths = fly(P, V, m.m_p, m.d_p, m.d_p / 2)
    land = np.where(np.isnan(land), -1e9, land)
    angles = np.degrees(sw.delta[cand])
    b = int(np.argmax(land))
    if release_angle_deg is None:
        j = b
    else:
        # The first step where the sling-to-arm angle has dropped to the pin's.
        hits = np.flatnonzero(angles <= release_angle_deg)
        j = int(hits[0]) if len(hits) else len(cand) - 1
    i = cand[j]
    v = V[j]
    speed = float(np.hypot(*v))
    ke = 0.5 * m.m_p * speed ** 2
    vac = 2 * m.m_cw * m.cw_drop_max(q0) / m.m_p
    r = float(land[j])
    frames = [[round(float(sw.t[k]), 4), *[round(float(x), 4) for x in sw.q[k]]] for k in range(0, i + 1, 25)]
    frames.append([round(float(sw.t[i]), 4), *[round(float(x), 4) for x in sw.q[i]]])
    sweep = [[round(float(a), 1), round(float(x), 3)] for a, x in zip(angles, land) if x > -1e8][::2]
    return Throw(
        ok=r > 0 and sw.problem is None, problem=sw.problem if sw.problem else (None if r > 0 else
            "With this release angle the projectile goes backwards or straight up; change the release angle."),
        release_angle_deg=round(float(angles[j]), 1), best_release_angle_deg=round(float(angles[b]), 1),
        range_m=r, best_range_m=float(land[b]), release_speed=speed,
        launch_angle_deg=math.degrees(math.atan2(v[1], v[0])), release_height_m=float(P[j][1]),
        release_t=float(sw.t[i]), flight_time=float(tf[j]), peak_height_m=float(peak[j]), liftoff_t=sw.liftoff_t,
        max_sling_pull_n=sw.max_sling_pull, energy_j=energy, efficiency=ke / energy if energy > 0 else None,
        range_efficiency=r / vac if vac > 0 else None, sweep=sweep,
        path=[[round(float(x), 4), round(float(z), 4)] for x, z in paths[j]], frames=frames)
