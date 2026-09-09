# Lighting diversity models

Three deterministic CPU reference models were trained on four original layouts. The loading-bay layout supplies validation. The cross-courtyard test layout was not rendered or accessed before this directory's model lock was committed.

All three variants used 393,216 sampled training pixels, 98,304 validation pixels, 10,000 optimizer steps, batches of 1,024 pixels and the same checkpoint schedule. The same source samples and minibatch indices were used for every variant. Hidden layers remain 32 by 32; their input-layer sizes differ.

| Variant | Inputs | Parameters | Selected step | Validation residual MSE |
| --- | ---: | ---: | ---: | ---: |
| Full scene inputs | 20 | 1,827 | 10,000 | 0.000050234 |
| Without absolute position | 17 | 1,731 | 8,750 | 0.000052614 |
| RGB only | 3 | 1,283 | 9,250 | 0.000097690 |

Validation selected the full-input model as the candidate. This is not a test result or an accepted fidelity claim. `model-lock.json` binds all three models, both affine controls and the fitting report before test access. Test results cannot change that selection.

Features come from source radiance, source geometry and original scene/material constants. No reference value enters inference. The relative variant excludes only absolute world position; normals, view direction and light offset still describe the scene. All variants produce a residual bounded by 0.25 in log1p scene-linear RGB. A bounded residual does not guarantee preservation of visibility or markings.

These are original Cycles experiments. No native GPU implementation, Reforger surface-buffer mapping, live frame-time saving, or photographic appearance has been established for these models. The existing frozen models remain regression controls.

Definitions: `scenes/lighting-diversity-v1.json`. Fitting evidence: `evidence/lighting-diversity-fit-v1.json`. Training: `scripts/train_lighting_diversity.py`. The full objective also requires the untouched test, complete comparisons and a separately verified Enfusion integration proof.
