# Research directions for HGCal/TICL reconstruction

**Thirteen projects**, each chosen to score on at least one of:
- **Physics performance** on hadronic showers (where the current chain
  most struggles)
- **Computational performance** in HLT, offline, or both
- **Methodological contribution** that travels beyond CMS

Spread across the skillset: systems engineering, statistical methods,
mathematical / algorithmic novelty, and ML/AI. Earlier drafts had
sixteen projects; this version cuts four (see **What was cut** at
the end) and adds five new ones in directions the cut projects
didn't cover well.

The goal is **fast + accurate** TICL across both deployments. Every
project is evaluated against that and what it would take to land it.

---

## Baseline: what the world looks like now

Take this as given going forward:

- **CLUEstering powers both layer-cluster building and pattern
  recognition.** Single library (`clue::Clusterer` in
  `CLUEstering/include/CLUEstering/core/`), single Alpaka GPU code
  path, shared tile structure and distance-metric infrastructure.
- **CLUEstering lives in its own repository**, used by CMS as one
  of several consumers. Improvements to CLUEstering proper
  (Projects 9, 10, 12 in particular) are **upstream library
  contributions** that travel to other experiments using or
  exploring it — ePIC, FCC, ALICE FoCal, CALICE prototypes. This
  expands the audience for systems-engineering work on the inner
  kernels: it's not a CMS-internal optimisation, it's a contribution
  to a library that is becoming the standard density-peak clusterer
  for HEP. Worth treating as such in publication strategy.
- **Deployed identically in HLT and offline.** Under the `alpaka`
  modifier, `HLTTiclTrackstersCLUE3DHighStepSequence` swaps to a
  single `hltHeterogeneousTracksterProducer` call — same module as
  `RecoHGCal/TICL/plugins/alpaka/HeterogeneousTracksterProducer.cc`.
- **HLT throughput target**: ~750 kHz event input, low-ms HGCal
  budget per event.
- **Linking is being addressed separately** by the user's own
  GNN + contrastive metric learning effort. Projects here either
  complement that work or attack different stages of the chain.

So the question "what to improve next" is no longer about porting
clustering to GPU. It is about everything else: features, linking
methods, networks, kernel-level performance, HLT-flavoured
infrastructure, **and improvements to the CLUEstering library itself
that benefit any experiment using it**.

---

## The 14 projects, organised by skillset

| # | Project | Skillset | Primary win |
|---|---------|----------|-------------|
| 1 | Per-LC software compensation via ρ | physics / stat | hadronic energy resolution |
| 2 | Quantile / evidential energy regression | statistics | calibrated tails, per-event uncertainty |
| 3 | Hyperbolic embedding for linking | math / ML | tree-structured hadronic linking |
| 4 | Sinkhorn optimal-transport assignment | math / ML | global linking under ambiguity |
| 5 | Kalman shower-axis evolution | algorithmic | curved hadronic axis fitting |
| 6 | Knowledge distillation: offline → HLT | ML / ops | HLT physics → offline parity |
| 7 | Mixture-of-experts PID | ML | specialist accuracy + sparse compute |
| 8 | Self-supervised LC pretraining | ML | sample efficiency, foundation features |
| 9 | FP16 + Morton-coded CLUEstering | systems | 2–3× clustering throughput |
| 10 | Warp-cooperative density kernels | systems | 1.5–2× kernel throughput |
| 11 | Persistent megakernels for TICL | systems | 40–60% pattern-reco latency cut |
| 12 | L1-seed-aware CLUEstering kernel | systems | regional HLT path 5–10× |
| 13 | HLT → offline SoA persistence | systems / ops | offline reco skips re-clustering |
| 14 | Hough-transform linking | classical algo | non-ML linking alternative |

**A note on Alpaka.** Every project here is implementable in
Alpaka. Three depths of Alpaka work, by category:

- **Pure Alpaka-portable** (Projects 1, 5, 12, 14): straightforward
  kernel work using existing Alpaka primitives.
- **Alpaka-portable with backend extensions** (Projects 9, 10):
  uses warp-shuffle primitives that Alpaka exposes but with some
  backend-specific care for half precision / cooperative shuffles.
- **Alpaka with upstream contributions** (Project 11): persistent
  megakernels need grid-wide synchronisation, which Alpaka does
  not currently expose portably. Part of the project is to
  contribute the abstraction upstream or wrap it. **This is the
  hardest systems work in the document and the highest-yield
  contribution to Alpaka itself.**

---

# Project 1 — Per-LC software compensation via local density ρ

**Skillset:** physics + classical statistics
**Risk:** low
**Where it lives:** `Trackster::vertex_metadata` extension; weight
computed in the existing CLUEstering kernel; consumed by
`TrackstersPCA` and the energy regression head.

### Motivation

HGCal is a non-compensating sampling calorimeter: e/h ≠ 1. The
dominant contribution to hadronic energy resolution is the
event-by-event fluctuation of the EM fraction within the cascade
(π⁰ → 2γ sub-showers respond differently than the hadronic core).

The classical fix — software compensation, used at H1 and ATLAS LCW
— discriminates EM-like from HAD-like deposits by **local energy
density** and applies a weight `w(ρ)` before summing. Worth 15–30%
on hadronic energy resolution in every prior implementation.

It has never been deployed in HGCal because the per-LC density was
too expensive to compute at HL-LHC pileup. **CLUEstering computes
it on the GPU as part of clustering. It's already there.**

### The idea

1. Propagate the per-LC `ρ_i` (already populated in
   `dev_points.weights()` by `KernelCalculateLocalDensity`) into
   `Trackster::vertex_metadata`. Zero extra computation —
   redirecting an existing buffer.
2. Calibrate `w(ρ, layer, subdetector, |z|)` from single-pion sim
   against `E_true / E_visible` per LC. Store as a 2D lookup table
   indexed by `(layer_bin, ρ_bin)`. ATLAS LCW form
   `w(ρ) = 1 + (w₀ − 1) · exp(−ρ / ρ₀)` is the well-trodden choice.
3. Compute compensated energy `E_corr = Σ w(ρ_i, ...) · E_i / mult_i`
   in parallel with `raw_energy()`. Add as a new trackster field.
4. Feed `E_corr` and the LC-level w-distribution moments (mean,
   variance, skewness) into the PFN as extra features — gives the
   PID network explicit EM/HAD discrimination.

### What it improves

- Hadronic energy resolution: realistic **15–30%** improvement.
- EM-fraction discrimination becomes a calibrated physical quantity
  rather than a learned latent.
- HLT-viable: the weight lookup is microseconds; the table fits in
  GPU constant memory.

### Computational challenges

- Calibration is sample-dependent. Need a careful programme of
  single-pion samples across η and energy plus closure tests on
  pion-jet samples.
- The 2D lookup must be branchless on GPU. Texture memory or a
  small constant-memory table works.

### Novelty

Software compensation is classical (H1 1995, ATLAS LCW 2008,
CALICE 2010s). Application per-LC with online GPU-computed density
is **new for HGCal**; existing CMS HGCal compensation work has been
offline hit-level studies that never fed back into reco. The
novelty is in the feasibility.

### First experiment

Dump `(ρ, layer, subdet, E_LC, E_true_LC)` per LC for a charged-pion
sample. Plot `<E_visible / E_true>` vs `ρ` in layer bins. A monotonic
dependence (which it will show) justifies the entire programme.

---

# Project 2 — Quantile / evidential energy regression with calibrated tails

**Skillset:** statistics, ML
**Risk:** low (well-established techniques)
**Where it lives:** energy head of the PFN
(`TracksterInferenceByPFN.cc`); a parallel quantile head plus a
small calibration step.

### Motivation

The current PFN energy head is MSE-trained: it predicts a point
estimate that converges to the conditional mean. Hadronic response
distributions are **asymmetric and heavy-tailed**, so the conditional
mean misses two things that matter physically:

1. The **spread** of the distribution per event — which encodes the
   EM-fraction fluctuation. The current pipeline collapses it to
   zero.
2. The **tails** — high-energy mismeasurements that drive MET tails
   and missing-energy backgrounds at HL-LHC.

Treating energy as a point estimate is throwing away physics.

### The idea

Replace the single energy output with one of (in increasing
sophistication):

**(a) Quantile regression.** Multiple heads at quantiles
`[0.05, 0.16, 0.5, 0.84, 0.95]`, trained with pinball loss. The
median is the point estimate; `q0.84 - q0.16` is a per-event
σ-equivalent; `q0.95 - q0.05` captures tails.

**(b) Evidential deep learning** (Amini et al., 2020). Output the
parameters `(μ, ν, α, β)` of a Normal-Inverse-Gamma prior. Gives
clean decomposition into aleatoric (intrinsic) and epistemic
(model-uncertain) uncertainty.

**(c) Conformal prediction wrapper.** Distribution-free, post-hoc,
with statistically guaranteed coverage. Calibrate on a held-out
set, get rigorous prediction intervals at any confidence level. Zero
inference cost.

Outputs feed downstream:
- The median is the point estimate, replacing the current scalar.
- The spread becomes a per-trackster uncertainty feature for linking
  decisions (pairs with Project 4).
- Wide-spread events become candidates for special handling (extra
  iterations offline, conservative thresholding at HLT).

### What it improves

- Per-trackster uncertainty for downstream PF / MET.
- Hadronic tails get properly weighted in physics analyses.
- HLT decisions can be made conservative on uncertain tracksters,
  rejecting borderline objects that would have been blindly accepted.

### Computational challenges

- Quantile heads add ~5 outputs → ~1% PFN latency increase. HLT-fine.
- Quantile-crossing (where `q0.5 < q0.16` for some event) is a
  known issue; non-crossing quantile networks (Cannon, 2018) fix it.
- Conformal calibration set must be representative of HL-LHC
  conditions across η and energy; need a careful sample mix.

### Novelty

Quantile regression is standard in finance, weather, energy.
Evidential regression has 2–3 HEP applications (jet pT, neutrino
direction). **For HGCal trackster energy regression neither has been
tried.** Strong methodological angle plus a clear "calibrated
uncertainty" story for downstream analyses.

### First experiment

Replace the PFN energy head with a 5-quantile head, retrain. Plot
`(q0.84 - q0.16)` against `|E_pred - E_true|` event-by-event. A
correlation says the network has learned to flag its own bad events
— immediately useful.

---

# Project 3 — Hyperbolic (Poincaré-ball) embedding for hierarchical linking

**Skillset:** mathematical / ML
**Risk:** medium
**Where it lives:** output head and loss of the contrastive metric
learning network; inference-side embedding consumers.

### Motivation

Particle showers in HGCal have a deep hierarchical structure:
primary particle → secondaries (γ from π⁰, charged π) → tertiaries
→ EM and hadronic sub-showers. Embedding such trees into Euclidean
space is **fundamentally inefficient**: tree depth grows
exponentially with node count, while Euclidean ball volume grows
only polynomially with radius. Euclidean distortion is unavoidable.

Hyperbolic space (specifically the Poincaré ball) has exponentially
growing volume with radius. **Any tree embeds into 2-D hyperbolic
space with arbitrarily low distortion** (Sarkar, 2011). The geometry
matches the data.

### The idea

1. Project the contrastive metric learning network output onto the
   Poincaré ball: a sphere of radius `< 1` in `R^d`.
2. Replace the Euclidean contrastive loss with Poincaré distance:
   ```
   d_P(u, v) = arccosh(1 + 2 ||u - v||² / ((1 - ||u||²)(1 - ||v||²)))
   ```
3. Same "pull same particle together, push different apart" semantics
   — but now distances near the boundary grow exponentially, giving
   rare distinctive tracksters "infinite room" to separate.
4. Train with Riemannian SGD (`geoopt` library, well-supported).
5. Downstream linking (k-means / HDBSCAN / Sinkhorn) gets a
   hyperbolic-aware variant — all exist in the literature.

### What it improves

- Hadronic-specific. EM showers are flat hierarchies (1–2 levels);
  hadronic showers have deep hierarchies — exactly where hyperbolic
  geometry helps most.
- **Embedding dimension reduction.** Euclidean networks typically
  use `d = 64` or `d = 128`. Hyperbolic equivalents work at
  `d = 8`–`16` at the same physics accuracy. That is **4× to 16×
  cheaper** memory and compute for the embedding head.
- HLT-critical: smaller embedding dimension is smaller GPU memory
  footprint per event → more concurrent events on one device.

### Computational challenges

- Numerical care needed near the Poincaré boundary `||u|| → 1`.
  Standard fix: clip norms below `1 - ε`.
- `arccosh` and Möbius arithmetic slightly more expensive per op
  than Euclidean. Net cost wins because dimension drops 4–16×.
- Downstream consumers need hyperbolic-aware versions
  (hyperbolic Sinkhorn, hyperbolic k-means). All exist as
  published algorithms; require porting.

### Novelty

Hyperbolic embeddings in HEP are very fresh: Murnane et al. 2023
(tracking), Atkinson et al. 2024 (jet tagging). **No HGCal
application yet** and the physical motivation (hadronic shower tree
structure) is the strongest application case in the field.

### First experiment

Take the existing contrastive metric learning network. Add a
Poincaré-projection layer at the output, swap the loss, train at
`d = 16`. Compare linking efficiency and per-event memory against
the current Euclidean `d = 64`. The expected result is "equal
accuracy, 4× cheaper" — directly useful.

---

# Project 4 — Sinkhorn optimal-transport assignment

**Skillset:** mathematical / algorithmic / ML
**Risk:** medium
**Where it lives:** final assignment step after the contrastive
metric learning embedding, replacing or augmenting threshold-based
linking.

### Motivation

A contrastive embedding tells you "these tracksters belong together"
in distance terms. **It does not tell you how to actually partition
them into particles.** The current options — distance thresholding,
greedy nearest-neighbour, DBSCAN-style — are brittle, order-
dependent, or oblivious to physics constraints.

Optimal transport is the principled answer: formulate linking as a
soft matching between tracksters (sources with energy) and
particles (sinks with predicted energy budget), with cost matrix
derived from embedding distances plus physics penalties. The
Sinkhorn algorithm (Cuturi 2013) solves it in a few matrix
multiplications, is differentiable, and outputs a calibrated
trackster→particle probability matrix.

### The idea

1. Embedding network gives `e_i ∈ R^d` per trackster (Euclidean or
   hyperbolic from Project 3).
2. Predict per-event a particle count and per-particle energy
   budget from event-level features (small regression head sharing
   the embedding backbone).
3. Construct cost matrix `C_ij = ||e_i − μ_j||² + λ_geom · (proj
   distance) + λ_E · (energy mismatch)`.
4. Run 20–30 log-domain Sinkhorn iterations. Output: soft assignment
   matrix `P_ij = P(trackster i ∈ particle j)`.
5. Threshold for hard decisions OR pass `P` directly to PF as a
   probability distribution.

### What it improves

- **Linking accuracy under ambiguity.** Two close hadronic showers
  with overlapping fragments are naturally separated by the
  mass-balance constraint.
- **Differentiable end-to-end** — the embedding network can be
  trained jointly with the assignment via the implicit function
  theorem (Eisenberger 2022; supported in `POT`).
- **Calibrated linking probabilities** for downstream PF
  consumption.
- HLT-viable: Sinkhorn on a `~100 × ~100` matrix is microseconds.

### Computational challenges

- Numerical stability at low entropy regularisation — log-domain
  iteration is the standard fix.
- Particle-count prior. Either learned per-event or seeded from a
  count of high-persistence cluster components.
- Sensible choice of `λ_geom, λ_E`. Can be learned.

### Novelty

OT in HEP is growing: Energy Mover's Distance (Komiske, Metodiev,
Thaler 2019), jet calibration via OT (Pollard 2023). **Sinkhorn-
based trackster linking in HGCal is new.** The strong narrative is
"contrastive embedding gives geometry, Sinkhorn does the
assignment" — the modern combo (cf. SuperGlue for feature
matching).

### First experiment

Use existing contrastive embeddings frozen. Implement Sinkhorn
assignment in PyTorch. Compare against current threshold-based
linking with the same embedding. If Sinkhorn wins ≥3% on linking
efficiency at fixed purity, the joint-training version follows.

---

# Project 5 — Kalman-filter shower-axis evolution

**Skillset:** algorithmic / state-space modelling
**Risk:** medium-high (physics validation needed)
**Where it lives:** new `KalmanShowerAxis` per-trackster algorithm,
producing extended trackster features consumed by linking and PID.

### Motivation

A trackster has a single PCA axis. Hadronic showers do not — they
curve, branch, and lose direction after nuclear interactions. The
single-axis approximation washes out exactly the information that
distinguishes single-hadronic-shower from overlapping-hadronic-
shower.

A shower along depth is naturally a **state-space process**:
- State `s_l = (x_l, y_l, dx/dz, dy/dz, E_l)` at layer `l`
- Transition: small `(x, y)` drift, small angular change, energy
  deposition + fluctuations
- Observation: the LC found at layer `l`

This is exactly what Kalman filters are for. CMS uses Kalman
filtering extensively for tracks — but not for tracksters.

### The idea

1. Order LCs within a trackster by layer.
2. Initialise state at the front layer from the first LC.
3. For each subsequent layer:
   - Predict the next state from the current state + a learned (or
     analytic) transition model (`F`) — average shower drift, small
     angular dispersion.
   - Update with the LC observation; compute Kalman gain; update
     state estimate and uncertainty.
4. After the forward pass, run a Rauch-Tung-Striebel smoother
   backwards for the best per-layer axis estimate with full uncertainty.

Outputs:
- Smoothed per-layer axis position and direction.
- Per-layer residuals — telling you where the shower deviated.
- A scalar **single-shower likelihood** from the residual
  distribution — useful for "is this one shower or two?".
- A measurement of shower curvature, particularly informative for
  charged hadrons in the magnetic field (negligible in HGCal but
  not zero) and for nuclear-interaction-driven branches.

For hadronic showers with large angular changes (non-Gaussian
transitions), use the **Unscented Kalman Filter** (Julier &
Uhlmann 1997) which handles non-linear transitions without
linearisation.

### What it improves

- Better hadronic axis for downstream skeleton-based linking.
- Per-layer uncertainty estimate — a real input for downstream
  goodness-of-fit cuts.
- A principled likelihood for "one shower vs many" — the missing
  ingredient in current linking-vs-splitting decisions.

### Computational challenges

- Hadronic transitions are non-Gaussian and have heavy tails. UKF
  handles this better than EKF; needs validation.
- Per-trackster `O(L)` with `L ≈ 50` layers, trivially parallel
  over tracksters → fast. HLT-viable.
- Transition-model parameters (drift, dispersion) can be learned
  per-energy-bin from sim.

### Novelty

Kalman for track fitting is universal in HEP. Kalman for **shower**
axis evolution has been tried at CALICE (Sefkow et al., for
embedded tracks in calorimeter cells) but not for HGCal trackster
axes. As a way to extract per-layer features from tracksters this
is **new**, and combines naturally with Project 7's MoE PID which
needs per-trackster summary statistics.

### First experiment

Run a Kalman filter on a single high-energy hadronic trackster.
Compare smoothed axis to truth-level shower axis vs the existing
PCA axis. If meaningfully closer to truth, the project is
justified.

---

# Project 6 — Knowledge distillation: heavy offline → small HLT models

**Skillset:** ML / operations
**Risk:** low–medium
**Where it lives:** training infrastructure; deployed as drop-in
replacement for the current ONNX models at HLT.

### Motivation

The current chain trains separate models for HLT (size-constrained)
and offline (capacity-rich). This creates two problems:

1. **Two pipelines to maintain**, two validation efforts, two
   versions to keep aligned.
2. **HLT physics lags offline**, often by a CMSSW release cycle —
   improvements to the offline PFN take time to propagate.

Knowledge distillation (Hinton 2015) collapses the two pipelines.
Train the heavy offline model as the "teacher". Distill into a
small "student" with the same architecture family but ~10× fewer
parameters. The student is trained on a loss combining ground-truth
labels with **the teacher's soft outputs and intermediate feature
representations** (FitNets, Romero et al., 2014).

### The idea

1. Train offline model normally — PFN with full capacity, full
   feature set, all the iterations the offline budget allows.
2. Build a small student — same input format, same output format,
   ~5–10× fewer parameters.
3. Distillation loss:
   ```
   L = α · L_truth(student, y) + β · L_KD(student, teacher) + γ · L_feat
   ```
   where `L_KD` is KL divergence on the soft outputs and `L_feat` is
   MSE on selected intermediate activations (matched by trainable
   projection layers).
4. Deploy the student at HLT. Refresh the student whenever the
   teacher is retrained — automatable.

### What it improves

- **HLT physics close to offline**, at HLT speed. Direct measurable
  gain for trigger efficiencies on hadronic objects.
- **Single training pipeline** — maintainability, validation
  efficiency, faster propagation of improvements.
- Pairs naturally with Project 7 (MoE) — the offline teacher can
  be an MoE; the student is a single dense network that approximates
  it.

### Computational challenges

- Training cost slightly higher (teacher + student forward passes).
  Offset by training only one model family.
- The student architecture choice matters — FitNets-style
  intermediate-activation matching requires layer-to-layer
  correspondence. For deep PFNs use multi-stage distillation.

### Novelty

Standard ML technique. **In HEP** there is one ATLAS paper (jet
tagging distillation, 2024) and that's about it. **For HGCal / TICL
this is new.** The operational impact is bigger than the
methodological one but both are real.

### First experiment

Take the current offline PFN. Train a student with 1/10 the
parameters, comparing direct training vs distillation. If
distillation wins by ≥2% on per-class metrics for the small model,
the project is justified.

---

# Project 7 — Mixture-of-experts PID with shower-type specialists

**Skillset:** ML
**Risk:** medium
**Where it lives:** PID head of the PFN; new gate network +
expert sub-networks.

### Motivation

A single PFN PID head learns to discriminate γ from π⁰ from e from
μ from charged π from K from p — simultaneously, on the same
features. These decision boundaries have **very different
structure** (γ vs π⁰ is a substructure problem; μ vs charged π is
a depth-of-penetration problem; HAD-with-EM-core vs pure-HAD is an
intermediate problem). One network must learn all of them and
necessarily underperforms on each.

Mixture of experts (MoE; Jacobs 1991; revived for LLMs in Switch
Transformer 2021, Mixtral 2024) routes each input to a specialist
sub-network. Each expert learns its domain well; total parameter
count is higher but per-inference compute is lower because only
one expert activates.

### The idea

1. **Gate network** sees trackster summary features (raw energy,
   barycenter η, axis direction, PCA eigenvalue ratios, time
   spread, EM fraction from Project 1, persistence). Outputs a
   distribution over ~4–6 experts.
2. **Experts**, each smaller than the unified PFN:
   - EM specialist: γ / e / π⁰
   - HAD-pure specialist: charged π / K / p with no early π⁰
   - HAD-with-EM-core specialist: hadronic shower containing
     significant π⁰ component
   - MIP specialist: μ tagging
   - Residual specialist: catch-all
3. **Training**: warmup with supervised gating (route to the right
   expert based on truth), then end-to-end with the gate trained on
   the final classification loss plus an entropy regulariser to
   keep gating sparse.
4. **Inference**: only the top-1 expert runs per trackster
   (sparse activation). Total FLOPs drop vs the unified PFN despite
   having more total parameters.

### What it improves

- Per-class PID quality — especially the historically poor cases:
  HAD-with-EM-core, π⁰ vs γ at high E.
- Inference time drops via sparse activation. HLT-friendly.
- Interpretability: which expert fired tells you what the network
  thinks the particle is.

### Computational challenges

- Training stability of MoEs is tricky — gates collapse to
  always-pick-one-expert without proper regularisation. Standard
  fixes (load-balancing loss, noisy gates) are well-documented.
- Sparse activation at inference is fastest if the gate's choice is
  the same across a batch — true for HLT batched events, sometimes
  not for single-event offline. Both modes need supported.

### Novelty

MoE is now mainstream in LLMs. **For HEP PID it's new** — one CMS
internal note in 2024 explored MoE for jet tagging, and that's it.
For HGCal **first usage**. Pairs with Project 8 (self-supervised)
because expert specialisation amplifies the value of strong
shared features.

### First experiment

Train a 4-expert MoE PID on the existing sample. Compare per-class
metrics against the unified PFN. The hypothesis is that MoE wins
significantly on hadronic classes; that result alone justifies
the project.

---

# Project 8 — Self-supervised pretraining of LC embeddings

**Skillset:** ML
**Risk:** medium
**Where it lives:** offline training infrastructure; produces an
encoder that becomes shared backbone for linking, PID, regression.

### Motivation

Supervised training in HEP hits a sample-size wall. SimTracksters
are expensive (full GEANT) and inherently noisy. The truth-matching
itself has ambiguities. Training data is finite; networks are
big; the marginal return on more sim is diminishing.

**Self-supervised pretraining** (BERT, MAE, DINO, BYOL) breaks the
wall. Train a network to predict missing parts of an event from the
rest — **no labels needed**. After pretraining, the encoder has
strong general-purpose features; downstream tasks fine-tune with
5–10× less labelled data.

For HGCal there is essentially unlimited unlabelled real data (every
recorded event), unlimited sim data with no truth-matching
requirements. The conditions for a foundation model are met.

### The idea

1. **Inputs**: per-event LC sets (positions, energies, layer indices,
   times if available).
2. **Pretext task** (masked LC modelling, analogous to BERT):
   randomly mask ~30% of LCs in an event. The encoder sees the
   remaining ~70% and must predict (regress) the positions, energies,
   and layer indices of the masked ones.
3. **Architecture**: a moderate-sized transformer or DeepSet over
   LCs (no graph required — permutation invariance suffices).
4. **Loss**: regression on positions/energies, cross-entropy on
   layer index for masked LCs.
5. **After pretraining**: throw away the decoder, keep the encoder.
   For each downstream task (linking, PID, energy regression),
   fine-tune with a small task-specific head. Often a *frozen*
   encoder + small task head is enough — making fine-tuning cheap.

### What it improves

- **Sample efficiency** for every downstream task. New simulations,
  new geometry, new conditions: refresh fine-tuning, redeploy.
- **Shared representation** across linking / PID / regression. A
  single backbone serves all three tasks → less duplicated
  computation at inference.
- HLT-friendly: the encoder is shared and small; downstream heads
  are tiny.

### Computational challenges

- Pretraining is expensive: days–weeks of GPU time on the available
  unlabelled corpus. One-time cost.
- Choice of masking strategy matters; random LC masking is a
  starting point. Structured masking (entire layers, entire φ
  sectors) may give richer features.
- Validation methodology: how do you know the encoder is "good"
  before fine-tuning? Use linear-probe accuracy on a small labelled
  set as a proxy.

### Novelty

Self-supervised pretraining for HEP is emerging: HEP-MAE (2023),
Particle Transformer Pretraining (2024) for jets. **For HGCal /
TICL nothing yet.** Strong methodological + practical contribution;
foundation-model arc.

### First experiment

100k events, small transformer (~5M parameters), masked-LC
pretraining. Fine-tune the encoder on PID, compare to the same
architecture trained from scratch on PID. If pretrained beats
from-scratch by ≥5% accuracy at the same labelled-sample budget,
the foundation-model arc is justified.

---

# Project 9 — Half-precision + Morton-coded CLUEstering

**Skillset:** GPU systems engineering
**Risk:** medium (engineering-heavy)
**Where it lives:** template specialisations and data-layout
changes inside `CLUEstering/include/CLUEstering/`.

### Motivation

The CLUEstering inner loop is the hottest kernel in TICL: per-LC
density computation iterating over tile neighbours. Two
characteristics make it ripe for low-level optimisation:

1. **The density is rank-sensitive, not value-sensitive.** It only
   matters which LCs are closer than `dc` and which are not, plus
   approximate density ordering. FP16 / BF16 noise is below the
   threshold that matters. HGCal position ranges fit in 16-bit
   integers with room to spare.
2. **Hadronic events are spatially sparse.** Most tiles in the
   forward region of the calorimeter are empty. Storing points by
   spatial locality lets the GPU cache benefit instead of
   scattering.

These two observations stack: **half precision + Morton-coded
layout = ~3× clustering throughput** at zero physics cost.

### The idea

**Half precision.** Add a `clue::Clusterer<Ndim, half_float>`
specialisation, gated by `#if` for hardware support. Keep `δ` and
final assignments at FP32; everything inside the density loop in
FP16. NVIDIA / AMD GPUs give ~2× throughput on FP16 (FP32 ALU
units run two FP16 ops); memory bandwidth halves.

**Morton coding.** Quantise `(x, y, z)` to 16-bit integers
(HGCal cell pitch / 100 fits easily). Bit-interleave to a 48-bit
Morton code; pack with weight into a single 64-bit word per
point. Sort by Morton code at LC ingestion using
`cub::DeviceRadixSort` (`O(N)` GPU time). Neighbours in 3-D are
now neighbours in memory; cache hit rate on the inner loop rises
sharply. Tile-traversal becomes bit-prefix arithmetic.

### What it improves

- **Clustering throughput 2–3×** on NVIDIA, similar on AMD.
- **Memory footprint halved** → more concurrent events per GPU at
  HLT.
- **Cache hit rate up** on hadronic events (sparse).
- Both LC build pass and pattern recognition pass benefit equally —
  the unified architecture means one code change, two beneficiaries.

### Computational challenges

- FP16 subnormals and overflow on `distance²`. Need a comparison
  test against FP32 reference; accept agreement at `~1e-4` on
  density values, exact agreement on cluster assignment.
- Morton sort is `O(N log N)` but the constant is small; must be
  amortised by speedup. Verified true on N ≥ ~10k; for tiny
  events (~hundreds of LCs) skip the sort.
- Coordinate with CLUEstering authors so this lands upstream and
  benefits ePIC / FCC / ALICE FoCal users too.

### Novelty

Half-precision spatial clustering on GPU has been done for SPH and
collision detection in graphics. **For CLUE specifically it has not
been published.** Morton-ordered CLUE is also new (the closest prior
is Götz et al. 2015 for DBSCAN). Systems paper + a contribution to
CLUEstering proper.

### First experiment

Microbenchmark outside CMSSW: a single CLUEstering call on a fixed
event, timed in (FP32 SoA, FP16 SoA, FP16 + Morton). The numbers
dictate sequencing.

---

# Project 10 — Warp-cooperative density and nearest-higher kernels

**Skillset:** GPU compiler-level engineering
**Risk:** medium-high
**Where it lives:** `ClusteringKernels.hpp` —
`KernelCalculateLocalDensity` and the nearest-higher kernel.

### Motivation

The CLUE inner loop currently assigns **one point per thread**. The
loop body iterates over candidate neighbours sequentially. Three
problems on modern GPUs:

1. **Warp divergence**: threads in the same warp may have very
   different neighbour counts (hadronic core LC has many; tail LC
   has few). The warp runs at the speed of its slowest thread.
2. **Uncoalesced loads**: each thread loads neighbours from
   uncorrelated tile slots → memory accesses scatter across cache
   lines.
3. **No reuse between adjacent points** that share most of their
   neighbour candidates.

These are exactly the issues GPU-graph-traversal literature solved
a decade ago with **warp-cooperative kernels** (Merrill et al.,
PPoPP 2012; Gunrock; cuGraph). Same pattern, applied to CLUE.

### The idea

Restructure so **one warp processes one point cooperatively**:

1. Warp picks point `i`. All 32 lanes share `coords_i`.
2. Walk tiles in the search box. Per tile, load up to 32 candidate
   neighbours in one coalesced load (one lane → one candidate).
3. All 32 lanes evaluate distance + kernel in parallel.
4. Reduce per-lane contributions to `ρ_i` via `__shfl_xor_sync`
   (or Alpaka warp-shuffle abstraction).
5. Single write of the warp's summed contribution per tile.

For nearest-higher kernel: same pattern with a warp-level `argmin`
reduction.

Optionally cache visited tile contents in shared memory so adjacent
warps benefit — "warp-cooperative neighbour caching" (standard in
N-body codes).

### What it improves

- Density kernel: **1.5–2×** from coalescing + reduced divergence.
- Nearest-higher kernel: **2–3×** from warp-level argmin.
- Stacks multiplicatively with Project 9 → realistic **5–10×
  combined** on the pattern-recognition step.

### Computational challenges

- Alpaka's warp abstractions are still maturing. May need to drop
  to CUDA/HIP intrinsics inside `#if ALPAKA_ACC_GPU_*_ENABLED`.
- Floating-point sum order changes between serial and warp-reduced;
  accept ~`1e-5` divergence.
- Falls back to thread-per-point for very small search boxes
  (EM-only low-PU events).

### Novelty

Warp-cooperative graph traversal is a recognised HPC technique.
**Warp-cooperative density-peak clustering is new**; closest prior
is GPU-DBSCAN warp restructuring (Andrade 2013, Poudel 2019), which
has not been applied to CLUE. Strong systems paper target — SC,
IPDPS, or PPoPP.

### First experiment

Profile current density kernel with Nsight Compute. If warp
divergence > 30% and uncoalesced load rate > 20% on a representative
PU200 event (both expected), proceed.

---

# Project 11 — Persistent megakernels for the TICL clustering pipeline

**Skillset:** deep GPU systems engineering / Alpaka extension
**Risk:** high (the most challenging systems project here)
**Where it lives:** new kernel architecture inside CLUEstering
proper, with Alpaka backend-specific extensions for grid-wide
synchronisation.

### Motivation

The CLUEstering pipeline runs as a sequence of separately-launched
kernels: build tiles → compute density → nearest-higher search →
seed propagation → assignment → per-LC feature collection. Each is
a separate GPU launch with its own setup cost, plus a forced global
synchronisation point between them. Modern Phase 2 HLT pipelines
suffer from this in two ways:

1. **Launch overhead.** ~5–10 µs per launch × ~6 kernels = 30–60 µs
   of pure overhead per event before counting actual compute.
2. **Lost intra-kernel concurrency.** Between kernels the GPU
   pipeline drains entirely. Memory loads for "phase N+1" cannot
   start until phase N finishes and the next kernel launches.

CUDA graphs (which I considered for this slot earlier) fix problem
(1) but not problem (2). The deeper answer is **persistent
megakernels**: a single kernel launched per event that internally
runs all phases of the CLUEstering pipeline, using grid-wide
cooperative synchronisation between phases. This eliminates both
problems. It is the dominant pattern in modern GPU HPC for
multi-phase data flow (Aila & Laine 2009; NVIDIA RTX kernels; the
Mosaic library; Triton's persistent autoschedulers).

Crucially: **no comparable HEP pipeline runs a persistent megakernel
today.** Patatrack uses CUDA graphs. ALICE O² uses kernel
sequences. Pulling this off in CLUEstering would be a genuine
first.

### The idea

1. Express the entire CLUEstering compute as a single kernel body
   with explicit phase markers:
   ```
   __global__ persistentClueKernel(...) {
     tile_build_phase();      grid_sync();
     density_phase();         grid_sync();
     nearest_higher_phase();  grid_sync();
     assignment_phase();      grid_sync();
     feature_phase();
   }
   ```
   `grid_sync()` uses cooperative groups on CUDA, the equivalent on
   HIP. Alpaka does not currently expose grid-wide sync portably,
   so this requires either contributing the abstraction upstream to
   Alpaka or wrapping backend-specific calls with `#if
   ALPAKA_ACC_GPU_*_ENABLED`. **This is part of the contribution.**
2. Each block keeps its slice of work in shared memory across
   phases — point indices, partial density sums, tile membership.
   Re-reading from global memory between phases (which kernel-
   sequence implementations must do) is avoided.
3. Use **fine-grained intra-kernel pipelining**: while phase N is
   computing on warps A, warps B can already be prefetching the
   memory phase N+1 needs. Standard GPU technique once you're in
   one kernel; impossible across separate launches.
4. The kernel is parameterised so that the same persistent
   structure runs for the 2D LC-build pass and the 3D pattern-
   recognition pass — only the metric, dimension, and parameters
   differ.

### What it improves

- **End-to-end pattern-recognition latency** dropped substantially —
  realistic **40–60% reduction** vs the current kernel-sequence
  implementation. Combined with Projects 9 + 10 inside the
  individual phases, the pattern-recognition step likely drops out
  of the HLT critical path entirely.
- **GPU occupancy** maximised — the GPU never drains between phases.
- **Smaller GPU memory traffic** — inter-phase state lives in
  registers and shared memory rather than going to global memory and
  back.
- A direct upstream contribution to **CLUEstering and (potentially)
  to Alpaka** — the grid-sync abstraction is generically useful.

### Computational challenges

- **Cooperative-group blocks must fit on the GPU simultaneously.**
  Grid-wide sync requires no queueing. This bounds occupancy and
  is the biggest constraint. Mitigation: persistent-thread-block
  pattern (Aila & Laine) where a small number of blocks process
  work in a loop, rather than spawning one block per point.
- **Alpaka does not expose grid sync** portably. Need to either
  contribute the abstraction or accept backend-specific code.
  Either way involves working with the Alpaka core team.
- **Debugging is hard.** GPU debugging tools mostly assume
  separate-kernel granularity. Mitigation: build the persistent
  kernel as a composition of well-tested per-phase kernels first,
  validated against the kernel-sequence baseline, then fuse.
- **Backend portability is a serious concern.** CUDA cooperative
  groups are stable since CUDA 9; HIP added grid sync recently
  (ROCm 5.3+); SYCL has analogous primitives but with different
  semantics; CPU backends can simulate via OpenMP barriers but
  performance is unrepresentative. Project will likely produce
  CUDA-first results with HIP follow-up.
- **CUDA graphs as a fallback path**: for configurations where
  persistent kernels don't fit (older GPUs, certain HIP versions),
  fall back to CUDA graphs of the kernel-sequence implementation.
  This gives 30–40% of the latency win at much lower implementation
  risk. Engineering plan should produce both.

### Novelty

Persistent megakernels are mature in HPC: Aila & Laine 2009
(ray tracing), Steinkraus 2017 (graph processing), recent work on
persistent kernels in machine learning (FlashAttention, persistent
softmax). **In HEP it is unprecedented.** No tracking, no
calorimetry, no jet reconstruction pipeline today uses persistent
megakernels. Successfully landing this in CLUEstering would be a
flagship contribution at SC, IPDPS, or PPoPP — the strongest
systems publication available in this whole document.

### First experiment

Implement the persistent-kernel pattern for **just the density +
nearest-higher phases**, leaving tile-build and assignment as
separate launches. This proves the grid-sync mechanism works and
measures the headline phase against the same kernels run
separately. If the prototype gets ≥25% latency reduction on the
two-phase portion, the full persistence project is justified.

---

# Project 12 — L1-seed-aware CLUEstering kernel

**Skillset:** systems / HLT throughput / regional computation
**Risk:** medium
**Where it lives:** new traversal mode in `ClusteringKernels.hpp`,
plus producer support for an "active tile mask" input from L1
seeds.

### Motivation

Many Phase 2 HLT paths only care about specific regions:
single-TkEle (one cone), double-EG (two cones), tau paths (small
η/φ regions), muon paths (almost no HGCal activity). The existing
`HLTHgcalTiclPFClusteringForEgammaL1Seeded` does regional reco at
the PFCluster level — **but CLUEstering still clusters the entire
endcap** before that filter.

A principled fix: **push the L1 region of interest into CLUE's tile
traversal**. Tiles outside any L1-defined region are never visited.
The cost of clustering becomes proportional to the area of
interest, not the area of the calorimeter.

### The idea

1. Add producer input: `vector<RegionOfInterest>` — list of
   `(η, φ, radius)` tuples. Empty == "everything" (global mode).
2. On kernel launch, compute on-device which tiles intersect any
   ROI. Small fast kernel, microseconds.
3. Modify `KernelCalculateLocalDensity` and nearest-higher kernels
   to skip tiles whose active bit is 0. The existing `for_recursion`
   structure makes this a one-bit check per iteration.
4. Keep the global path unchanged via a default ROI mask of all-1s.

### What it improves

- **HLT throughput on L1-seeded paths.** By typical region
  coverage:
  - single e/γ: ~10×
  - double e/γ: ~5×
  - jet paths: ~2×
- Power / GPU energy savings.
- Smaller working set per event → more concurrent events on GPU.

### Computational challenges

- Multi-region overlap deduplication needed (double e/γ regions
  may overlap). Easiest: deduplicate at point level after
  clustering, before downstream consumers.
- Some paths need the full global clustering (jets, MET). Modifier
  dispatch handles this cleanly via existing `era` infrastructure.

### Novelty

L1-aware computation is standard HLT design. **Pushing it down
into a GPU clustering kernel is new**. Closest prior art is ATLAS
HLT regional unpacking, which is binary skip-or-don't, not the
fine-grained tile-level filter proposed here. Pairs naturally with
the Patatrack regional pixel-tracking work.

### First experiment

Profile a typical L1-e/γ HLT event with Nsight Systems. Measure
the fraction of CLUEstering work happening outside L1 regions.
If > 70% (it will be), the project is essentially free.

---

# Project 13 — HLT → offline SoA persistence

**Skillset:** systems / data flow / operational
**Risk:** low-medium (mostly politics)
**Where it lives:** event-content streamers in
`HLTrigger/Configuration/python/`, offline consumer modules in
`RecoHGCal/TICL/`.

### Motivation

Today HLT runs full TICL pattern recognition; offline reruns it
from scratch. This is wasteful — the HLT result was computed under
guaranteed identical conditions and is good enough to seed offline.
Historically the barrier was that HLT and offline outputs differed
(different SoA layouts, different precision, missing fields). **The
unified-CLUEstering architecture removes that barrier**: HLT and
offline now run the *same* library.

The project is purely about plumbing — persist the CLUEstering SoA
output from HLT to the event stream; offline reads it and skips
the clustering pass.

### The idea

1. Add an `HLTHgCalCLUESoAStreamer` writing CLUE's on-device SoA
   (cluster assignment, per-LC ρ, per-LC δ, trackster vertex lists)
   to the HLT event stream via the existing `EventContent`
   framework.
2. Add an offline consumer constructing the legacy `Trackster`
   collection directly from the persisted SoA.
3. Offline reco gains a switch: `useHLTPatternRecognition = True`
   skips the offline CLUE pass entirely.
4. **Deterministic equivalence test**: bit-compare offline outputs
   when run with vs without HLT-persistence. Feasible only because
   both deployments now run the same library.

### What it improves

- **Offline wall-clock time** drops by the cost of clustering —
  the most expensive single step in offline TICL. Prompt reco
  finishes sooner.
- **HLT-offline consistency** trivially perfect by construction.
  Currently a source of validation headaches.
- **Compute cost savings** — meaningful at the experiment scale.

### Computational challenges

- HLT output bandwidth increases by the per-event SoA size (single-
  digit kB). Measure before committing.
- Recovery iteration in offline may want to re-cluster locally —
  needs region-restricted re-clustering. Pairs cleanly with
  Project 12.
- Event-content schema politics — needs DPG buy-in.

### Novelty

ATLAS persists HLT tracking outputs in the same spirit. **For
HGCal/TICL this has not been done**; the unified architecture is
what makes it feasible. Operational contribution rather than
methodological, but high impact.

### First experiment

Profile end-to-end offline reconstruction with and without TICL
re-execution (mock the persistence by reading from a side channel).
Quantify wall-clock saved. The number tells you how hard to push
for the schema change.

---

# Project 14 — Hough-transform linking (classical, non-GNN, non-embedding)

**Skillset:** classical algorithms / computer vision in HEP
**Risk:** medium
**Where it lives:** new `TracksterLinkingbyHough` Alpaka plugin
running entirely on device. Slots into
`TracksterLinkingPluginFactory` alongside the GNN / metric-learning
linker.

### Motivation

Both the existing GNN linker and contrastive metric learning are
**learned** approaches. They require labelled training data, are
subject to data-distribution drift between sim and data, and don't
naturally encode physical priors. They also share a fundamental
structure — pairwise embedding / edge scoring — which means failure
modes correlate. If both struggle on a class of events, swapping
between them doesn't help.

A genuinely different paradigm is worth having on the menu. The
Hough transform (Hough 1962, Duda & Hart 1972) is the classical
computer-vision technique for detecting parametric shapes in noisy
data. In HEP tracking it has been used for decades (DELPHI 1991, H1
1996, more recently in ATLAS trigger). **For calorimetric linking
it is a fresh angle.** The physics insight is simple: tracksters
from a single particle share an axis that points to a common
origin (the IP for unseeded particles, the front face for
track-seeded ones). In an appropriate parametric space, they
**vote together for the same peak**. Particles emerge as peaks; no
learning needed.

### The idea

1. **Per-trackster, extract axis parameters.** Direction `n` and
   origin `x₀` from PCA (or Kalman from Project 5). Project the
   axis backwards to a reference surface (IP for unseeded paths,
   HGCal front face for track-seeded paths). Result: a candidate
   `(θ, φ)` for the parent particle, with an uncertainty derived
   from PCA spread (or per-layer Kalman uncertainty).
2. **Each trackster votes.** Accumulate into a 2D Hough plane:
   `H(θ, φ) += w_E · G_σ(θ − θ_t, φ − φ_t)`, where `w_E` is the
   trackster energy and `G_σ` is a Gaussian uncertainty kernel.
   Trivially parallel: one Alpaka kernel where each thread handles
   one trackster, atomic-adds into the accumulator.
3. **Find peaks.** Non-maximum suppression over `H(θ, φ)` —
   standard image-processing kernel, well-suited to Alpaka. Each
   peak is a candidate particle.
4. **Assign tracksters to peaks.** Each trackster is linked to the
   nearest peak in `(θ, φ)` within an energy-weighted tolerance.
   Tracksters too far from any peak remain unlinked (handled by
   the existing recovery iteration).
5. **Optional refinement.** Refit each particle's axis using the
   pooled LCs from all linked tracksters; re-vote; iterate 2–3
   times. Converges quickly because most assignments are stable.

For track-seeded paths (electrons, charged hadrons): seed the
Hough peak directly from the propagated track. Tracksters within
a (θ, φ, energy) tolerance of the track are linked. This is
essentially the existing track-seeded reco, but reformulated to
share kernel code with the unseeded path.

### What it improves

- **Fragmented hadronic showers handled naturally.** Multiple
  tracksters from one cascade share a Hough peak by physical
  construction, not by a learned embedding that may or may not
  generalise.
- **No training data required.** Robust to sim/data drift, to new
  geometries, to new energy regimes.
- **Trivially parallel on GPU**, fits Alpaka cleanly. Per-event
  cost is dominated by the accumulator (microseconds for an HL-LHC
  event).
- **Interpretable.** Peaks are physical objects in `(θ, φ)`. Every
  linking decision has a transparent explanation.
- **Complementary to GNN / metric learning, not competitive.**
  Ensemble of Hough + ML linking: if both agree, high confidence;
  if they disagree, flag for downstream uncertainty handling.

### Computational challenges

- **Hough resolution choice.** Bin size in `(θ, φ)` trades off
  spatial resolution against accumulator noise. For HL-LHC PU it
  has to be fine enough to separate nearby particles but coarse
  enough that hadronic spread doesn't kill the peak. Solved by
  multi-resolution Hough (votes at multiple bin scales) or by
  using the trackster's PCA uncertainty as an adaptive kernel
  bandwidth.
- **Non-Gaussian uncertainties.** Hadronic tracksters can have
  bimodal axis distributions; a single Gaussian vote loses
  information. Mitigation: per-trackster vote shape is itself
  learned (a tiny convolution kernel) without changing the
  Hough-accumulator framework.
- **Late nuclear-interaction fragments** may not point to the
  original origin. They'll vote in the wrong place. Mitigation:
  iterative Hough with axis refit (step 5 above) — once the
  particle's true direction is known, late fragments can be
  assigned via geometric proximity rather than vote agreement.
- **Track-seeded handling.** Mixing seeded and unseeded
  populations in the same Hough plane requires care; typically
  best done as a two-stage process (seeded first, then unseeded
  among the remainder).

### Novelty

- Hough for HEP tracking is classical and well-cited.
- Hough for HGCal **trackster linking** — **does not exist in the
  literature.** The closest comparable is "track-following" in
  calorimeters (e.g., CALICE shower-axis fitting) which uses
  similar primitives at the cell level but not for linking
  multi-trackster particles.
- A strong narrative for publication: in an era of universally-ML
  linking, a well-designed classical algorithm matches or beats
  GNN on physical performance, runs faster, doesn't need training
  data, and gives interpretable outputs. This is the kind of
  counter-narrative paper that gets attention at ML4PS workshops
  and methodology-focused venues.

### First experiment

Take a charged-pion sample, run the existing chain through pattern
recognition, and for each event plot the Hough plane of the
reconstructed tracksters with truth-particle directions overlaid.
Visual agreement (peaks in Hough plane align with truth
directions) is sufficient validation to justify implementation.
Quantitative comparison against the GNN linker comes next.

---

# Viability across deployments

| # | Project | HLT viability | Offline gain | Stacks with |
|---|---------|---------------|--------------|-------------|
| 1 | per-LC compensation | ✔ (µs lookup) | hadronic resolution **large** | 2, 7 |
| 2 | quantile / evidential | ✔ (~1% latency) | calibrated tails **medium-large** | 4, 7 |
| 3 | hyperbolic embedding | ✔✔ (4× cheaper) | tree-hadronic **medium-large** | 4 |
| 4 | Sinkhorn OT linking | ✔ (µs matrix) | global linking **medium-large** | 3, 7 |
| 5 | Kalman shower axis | ✔ (O(L) per ts) | hadronic axis **medium** | 7 |
| 6 | KD: offline → HLT | ✔ (the win) | offline unaffected | all ML projects |
| 7 | MoE PID | ✔ (sparse FLOPs) | per-class **large** | 1, 5, 8 |
| 8 | self-supervised pretrain | ✔ (inference cheap) | sample eff **medium** | 6, 7 |
| 9 | FP16 + Morton CLUE | ✔✔ (memory + speed) | small (FP16 noise) | 10, 11 |
| 10 | warp-cooperative kernels | ✔✔ | small | 9, 11 |
| 11 | Persistent megakernels | ✔✔✔ (HLT-defining) | mild | 9, 10, 12 |
| 12 | L1-aware CLUEstering | ✔✔✔ (5–10× regional) | n/a | 11, 13 |
| 13 | HLT → offline persistence | (HLT-side cost) | wall time **large** | 12 |
| 14 | Hough-transform linking | ✔ (µs voting) | hadronic **medium**, ensemble with GNN | 3, 5 |

Reading: projects with ✔✔ or ✔✔✔ HLT viability are the
**throughput-defining** contributions. Projects with **large** in the
offline gain column are the **physics-defining** ones. The
intersection — Projects 1, 3, 7 — are the genuinely dual-deployment
wins.

---

# Stacking — how the 13 fit together

```
┌─────────────────────────────────────────────────────────────────┐
│                  Unified CLUEstering (given)                    │
│   LC build + pattern recognition, single GPU library, both      │
│   HLT and offline. Inputs: rechits + (optional) L1 regions.     │
│                                                                 │
│   Improved by:                                                  │
│      Project 9  — FP16 + Morton                                 │
│      Project 10 — warp-cooperative kernels                      │
│      Project 11 — CUDA graphs                                   │
│      Project 12 — L1-aware traversal                            │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────────┐
        │  Per-LC features computed during clustering    │
        │     Project 1 — w(ρ) software compensation     │
        └────────────────────────────────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────────┐
        │  Trackster aggregates                          │
        │     Project 5 — Kalman per-layer axis + likelihood│
        │     Existing PCA + barycenter                  │
        └────────────────────────────────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────────┐
        │  Shared LC / event encoder (foundation features)│
        │     Project 8 — self-supervised pretraining    │
        └────────────────────────────────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────────┐
        │  Linking                                       │
        │     existing GNN / contrastive metric learning │
        │     Project 3 — hyperbolic embedding (upgrade) │
        │     Project 4 — Sinkhorn OT assignment         │
        │     Project 14 — Hough transform (classical    │
        │                  non-ML alternative, ensemble) │
        └────────────────────────────────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────────┐
        │  PID + energy regression                       │
        │     Project 2 — quantile / evidential regression│
        │     Project 7 — MoE PID                        │
        └────────────────────────────────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────────┐
        │  Operational layer                             │
        │     Project 6 — KD: offline teacher → HLT student│
        │     Project 13 — HLT SoA → offline             │
        └────────────────────────────────────────────────┘
```

The vertical structure is the pipeline; the projects are positioned
where they intervene. **Project 6 (KD) and Project 13 (persistence)
sit outside the pipeline — they're operational layers spanning HLT
and offline.**

Key stacking insights:

- **Project 1 → Project 7**: the EM-fraction feature from
  compensation becomes one of the gate inputs for MoE PID. The MoE
  HAD-with-EM expert exists *because* compensation gives it a clean
  signal.
- **Project 3 → Project 4**: hyperbolic embedding feeds Sinkhorn
  via hyperbolic-distance cost matrices. Both train end-to-end.
- **Project 9 → Project 10 → Project 11**: layered systems wins.
  FP16 + Morton + warp-cooperative all live inside individual
  kernels; CUDA graphs orchestrate them at the chain level.
- **Project 8 ↔ all ML projects**: self-supervised features become
  shared input for linking (Project 3), PID (Project 7),
  regression (Project 2). One backbone, multiple heads.
- **Project 6 ↔ all ML projects**: distillation makes any
  improvement to the offline ML model immediately deployable at
  HLT.

---

# PhD-scale sequencing

**Year 1 — Physics result + HLT throughput foundation**
- Project 1 (compensation) — early physics paper.
- Project 9 (FP16 + Morton) — lands in CLUEstering proper.
- Project 11 (CUDA graphs) — HLT latency.
- Project 2 (quantile regression) — quick, complements 1.

**Year 2 — Depth and infrastructure**
- Project 12 (L1-aware) — the single biggest HLT throughput win.
- Project 7 (MoE PID) — per-class hadronic gains.
- Project 6 (KD) — operational layer, enables 7 at HLT.
- Project 10 (warp-cooperative kernels) — collaboration with
  CLUEstering core team.

**Year 3 — Methodological capstone + operational**
- Project 8 (self-supervised) — capstone foundation-model paper.
- Project 3 (hyperbolic) and / or Project 4 (Sinkhorn) — linking
  upgrades aligned with the GNN / metric-learning team.
- Project 5 (Kalman axis) — feature engineering for PID.
- Project 13 (SoA persistence) — operational deployment.

Five chapters: **physics** (1 + 2), **HGCal systems**
(9 + 10 + 11 + 12), **ML methods** (6 + 7 + 8), **mathematical**
(3 + 4 + 5), **operational** (13). Each chapter has redundancy — if
one project fails, the chapter still has results.

---

# What was cut from earlier drafts

For the record. Each had merit but didn't make this round:

- **Topological persistence clustering on top of CLUE** — interesting
  algorithmically but doesn't reach HLT viability for busy events,
  and the offline-only gain didn't compete with Project 5 (Kalman
  axis) as a per-trackster structural feature source. Could
  resurface as a small offline-quality enrichment study.
- **Differentiable CLUEstering** — too speculative for a planned
  thesis chapter. Soft-clustering relaxations have a long tail of
  research before they beat well-tuned hard clustering. Project 5
  (Kalman) gives a smaller but more deliverable algorithmic
  contribution.
- **Slot-attention / DETR-style linking** — covered by combining
  Project 3 (hyperbolic embedding) + Project 4 (Sinkhorn). One
  fewer architecture to maintain.
- **Reeb-graph / Mapper-based linking** — beautiful TDA framing
  but offline-only and speculative. Cut in favour of mainstream
  projects with clearer first experiments.
- **Anytime CLUEstering** — interesting systems direction but
  speculative for HEP and would interact awkwardly with CUDA graphs
  and L1-aware traversal. Project 11 + 12 + 13 deliver bounded HLT
  latency through simpler means.

---

# What I deliberately did not propose

- **End-to-end one-shot reconstruction** — user has rejected this
  explicitly.
- **Replacing the GNN linker wholesale** — user is leading that
  effort.
- **Anything requiring changes to the rechit producer side of
  HGCal local reco** — out of scope and politically expensive.
- **More than 14 projects** — the cut is the work.

---

# Personal ranking — where I'd put my own time

Three rankings across different criteria. Take these as my opinions
on top of the technical content above, not as objective truth. The
short version is at the bottom.

## Ranked by TICL impact (production reconstruction quality and throughput)

This is the "what helps the experiment most" axis.

1. **Project 11 — Persistent megakernels.** Single largest HLT
   latency win on the table. Pattern recognition likely drops out
   of the HLT critical path entirely when combined with Projects 9
   and 10. Also unlocks Alpaka's growth into a serious HPC
   framework.
2. **Project 1 — Per-LC software compensation.** Largest single
   physics improvement on hadronic energy resolution. ~15–30% gain
   at essentially zero computational cost — the rare project where
   the cost-benefit ratio is approximately infinite.
3. **Project 12 — L1-seed-aware CLUEstering.** 5–10× throughput on
   the L1-seeded HLT paths that dominate the trigger budget.
   Operationally critical for HL-LHC and easy to land.
4. **Project 7 — Mixture-of-experts PID.** Per-class hadronic
   accuracy gains plus cheaper inference. Pairs perfectly with
   Project 1's EM-fraction signal as a gate input.
5. **Project 9 — FP16 + Morton CLUEstering.** Throughput multiplier
   that lands upstream in the CLUEstering library and ripples out
   to every experiment using it. The "two-for-one" property is
   what gets it this high.

## Ranked by learning value (skills you carry away)

This is the "how much will I grow as a scientist/engineer" axis.

1. **Project 11 — Persistent megakernels.** Deepest GPU
   programming work in the document — cooperative groups, intra-
   kernel pipelining, persistent-thread patterns, contributing to
   the Alpaka core abstraction. These are skills that transfer to
   any GPU-programming role at a top HPC/ML lab anywhere in the
   world.
2. **Project 10 — Warp-cooperative kernels.** One level less
   intense than Project 11 but the same family of skills. Warp-
   primitive programming is universal in GPU work and the patterns
   you learn here apply directly to graph neural networks,
   transformer attention kernels, and any other parallel-reduction
   problem.
3. **Project 8 — Self-supervised pretraining.** Foundation-model
   methodology is the dominant trend in ML for the last 3+ years
   and shows no sign of slowing. The skills (masked modelling,
   contrastive losses, scaling-law analysis, transfer learning)
   are transferable to any ML domain.
4. **Project 3 — Hyperbolic embedding.** Non-Euclidean ML and
   Riemannian optimisation are mathematically deep and growing
   subfields. The mental flexibility you gain from "spaces other
   than R^n" is broadly applicable.
5. **Project 5 — Kalman shower-axis evolution.** State-space
   estimation is one of the most under-taught core skills in
   computational physics. Carries to robotics, finance, signal
   processing, and a lot of ML at the boundary with control theory.

## Ranked by publishability and CV impact

This is the "what gets noticed when applying for postdocs / industry
research positions" axis.

1. **Project 11 — Persistent megakernels for HEP reconstruction.**
   Tier-1 systems venues (SC, IPDPS, PPoPP). The combination of
   "HEP cross-disciplinary appeal" + "first persistent-kernel
   implementation in the field" + "open-source library
   contribution" + "production deployment at CMS" is the rare
   single project that hits three different prestige circuits.
2. **Project 8 — Self-supervised foundation model for HGCal.**
   Tier-1 ML venues (NeurIPS-ML4PS, ICLR-ML4Sci, sometimes ICML
   workshops). Foundation models for science are the headline ML
   narrative right now and "first HGCal foundation model" lasts as
   a citation magnet for years.
3. **Project 10 — Warp-cooperative density-peak clustering.**
   Strong IPDPS / SC contribution. Pure systems story with a clean
   speedup number. Less cross-disciplinary appeal than Project 11
   but more immediate, more achievable.
4. **Project 14 — Hough-transform linking.** Counter-trend paper.
   In a world where every linking paper uses ML, a careful
   classical method that competes with GNNs hits a sweet spot for
   methodological-rigor venues and gets read precisely because it
   is contrarian. Good for a methodology-focused career profile.
5. **Project 3 — Hyperbolic embedding for HGCal linking.** Strong
   NeurIPS-ML4PS angle. Real methodological novelty (first
   hyperbolic embedding for calorimetric linking) paired with
   physical motivation (hadronic showers are trees) makes it both
   publishable and defensible to physicists.

## Overall — my top three favourites if I had to pick

Across all three axes, weighted equally:

### 🥇 Project 11 — Persistent megakernels

The undisputed first place. Triple-positive across all rankings:
highest TICL impact, highest learning value, highest
publishability. It is also the **most risky and most difficult**
project in this document — there is a real chance it doesn't work
out cleanly in Alpaka or runs into HW/driver limitations on
mixed-vendor sites. If it works, it's a flagship
contribution. If it half-works, the CUDA-graphs fallback gives a
solid Plan B that's still publishable.

This is the project a PhD would be remembered for.

### 🥈 Projects 1 + 7 (jointly)

Per-LC software compensation paired with MoE PID. Together they
form a clean "specialist hadronic" thesis chapter that solves the
**actual physics problem the user cares about** (hadronic poor
performance) with a defensible mix of classical physics (Project
1 has a 30-year pedigree) and modern ML (Project 7 is current ML
methodology). The pairing matters: Project 1's EM-fraction signal
becomes Project 7's MoE gating feature. Neither makes full sense
without the other.

This is the most certain physics result in the document.

### 🥉 Project 8 — Self-supervised pretraining

The foundation-model arc. Slowest to produce a result (months of
pretraining + downstream evaluation) but the kind of work that
gets cited by everyone doing HEP ML for years. It also gives the
PhD a methodological capstone that's defensible at any ML venue,
not just HEP-internal ones.

## Practical recommendation

If you can only do one: **Project 1**. It is the most certain
win, the most direct physics result, the smallest engineering
risk, and the fastest to a publishable result. The
cost-benefit ratio is genuinely the best in the document.

If you have three years and want a thesis people remember:

- **Year 1**: Project 1 → early physics paper, baseline established.
- **Year 2**: Project 11 → flagship systems contribution while the
  rest of the chain runs on the Year 1 deliverable.
- **Year 3**: Project 7 (or Project 8) → methodological capstone,
  with Project 1's outputs feeding it.

Three chapters, all defensible independently, all interlocking
when read together. That is the thesis.

If you want a fourth chapter, Project 14 (Hough-transform linking)
is the most distinctive — most other PhDs in this space will be
GNN papers. Yours wouldn't be.

---

# Notes / open questions

(Section left for the user's own annotations.)
