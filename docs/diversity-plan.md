# Scene diversity experiment

This experiment is in progress. Its definitions are committed before rendering and training. No result or integration capability is claimed by this plan.

Four original training layouts cover return walls, covered alcoves, staggered workshop furniture and split passages. A separate loading bay supplies validation cases. An untouched cross-courtyard supplies the final camera/light path. Every layout includes reflective objects, geometric markings and thin posts. These are original synthetic assets; the separate Reforger integration tests will include urban streets, interiors, vegetation, vehicles and characters.

## Comparison

RGB-only, the current 20 scene features and a 17-feature version without absolute world position each receive the same sampled training pixels, minibatches, 10,000 optimizer steps and validation schedule. Hidden layers remain 32 by 32; the input-layer parameter count differs. Two affine controls use the same training data. The current frozen models remain controls.

There are 48 training cases and 12 validation cases at 480 × 270. A source/reference pair uses 2,048 samples and differs only in diffuse-bounce depth, 1 versus 12. The untouched 48-frame test uses 8,192 samples for source, reference and an independent reference seed in every frame. Geometry, exposure and color settings remain paired.

The lowest validation residual MSE selects each checkpoint and then the candidate variant. All model hashes are saved in a lock before test rendering is permitted. Test images and the published regression paths cannot change selection, normalization, training samples or thresholds.

## Acceptance

The selected candidate must improve mean test log-radiance RMSE by at least 5% over identity and both new affine controls. Relative to the source, no evaluated frame may worsen boundary or thin-post RMSE by more than 2%, or marking-contrast error by more than 0.002 weighted-log units. Mean temporal reconstruction-error RMSE may worsen by at most 2%. Reference-seed sensitivity greater than half a claimed gain makes that claim inconclusive.

All variants, complete test clips, regressions and failures will be published. The existing two paths remain regression checks with their original reference-noise limitation. Passing one synthetic layout does not establish all-asset or gameplay fidelity.

## Enfusion integration

Use isolated Workbench addons to establish supported scene input and output access with an identity control and a visible inversion control. Record formats, frame association, available surface inputs, synchronization and placement relative to postprocessing and UI. Test varied Reforger environments, including urban buildings, interiors, vegetation, vehicles, characters and small objects. An ordinary effect declaration or external screenshot processor alone cannot prove a live neural bridge.

The goal retains both the lighting comparison and the integration proof. A missing engine interface must remain an explicit unresolved requirement, rather than being relabeled as completed by synthetic evidence.

[Frozen experiment definition](https://github.com/ethan03805/enfusion-neural/blob/main/scenes/lighting-diversity-v1.json)
