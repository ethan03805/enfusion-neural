# Arma scenes

These captures begin the real-environment test set. They are unprocessed Enfusion images; no lighting model or aligned reference has been applied.

<figure><a href="media/arma-st-philippe-entities.png"><img src="media/arma-st-philippe-entities.png" width="2560" height="1440" loading="lazy" alt="M998 and standing rifleman in a Saint-Philippe garden, surrounded by vegetation, fences and buildings"></a><figcaption>Saint-Philippe · source capture with a placed vehicle and character</figcaption></figure>

The isolated simulation loads Everon using a resource name observed by the native inventory. Camera position, projection, exposure, date, weather, wind and output dimensions pass the capture checks. Internal viewport scale, FSR and presentation frame identity remain unverified. The full-resolution PNG is unchanged from the captured file.

| Coverage | State |
| --- | --- |
| Garden, vegetation, fences and building exteriors | Captured and visually inspected |
| Upright vehicle and standing character | Captured and visually inspected |
| Factory yard, warehouse exteriors and industrial structures | Four views captured and inspected |
| Warehouse interior and stored objects | Four views inspected; source anomaly retained |
| Montignac town streets, crossings and building facades | Four views inspected; source anomaly retained |
| Neural fidelity on Arma scenes | Untested |
| Supported engine inputs and output | Unproven |

The first entity attempt placed both prefabs underground because the editor terrain query returned zero during simulation. Switching to the simulation world's surface query corrected height, but an XYZ rotation then overturned the vehicle. The final run sets an upright spawn matrix before creation. Both failed attempts remain in [the evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-arma-scenes-v1.json), alongside the successful capture and its exact script/config hashes. A successful screenshot alone never establishes correct entity placement.

<figure><a href="media/arma-factory-yard.png"><img src="media/arma-factory-yard.png" width="2560" height="1440" loading="lazy" alt="Factory buildings, chimney, corrugated warehouse and paved yard in Saint-Philippe"></a><figcaption>Saint-Philippe factory · unprocessed source view</figcaption></figure>

The factory scout records four directions from one camera position. The first faces a nearby container; the others show the yard, industrial buildings and warehouse facade. All four views were inspected and retain their hashes and camera records. Sample 2 was chosen afterward to illustrate the complex; no model output was selected or evaluated. The [factory config](https://github.com/ethan03805/enfusion-neural/blob/main/scenes/arma-factory-v1.json) reproduces the four views.

<figure><a href="media/arma-warehouse-interior.png"><img src="media/arma-warehouse-interior.png" width="2560" height="1440" loading="lazy" alt="Warehouse aisle with shelving, crates, timber stacks and high windows"></a><figcaption>Warehouse interior · unprocessed source view</figcaption></figure>

Four [interior views](https://github.com/ethan03805/enfusion-neural/blob/main/scenes/arma-warehouse-interior-v1.json) include shadowed timber, crates, shelving and high windows. One direction shows storage objects that appear unsupported; its cause is unverified. This scene has not been accepted as an appearance reference. Both the aisle view and the anomaly remain visible below and in the evidence.

<details><summary>Interior source anomaly</summary><figure><a href="media/arma-warehouse-source-anomaly.png"><img src="media/arma-warehouse-source-anomaly.png" width="2560" height="1440" loading="lazy" alt="Warehouse source capture with crates and pallets appearing unsupported in one direction"></a><figcaption>Sample 1 · source object visibility needs investigation; no neural processing was applied</figcaption></figure></details>

<figure><a href="media/arma-montignac-street.png"><img src="media/arma-montignac-street.png" width="2560" height="1440" loading="lazy" alt="Montignac street with a pedestrian crossing, church towers, fences, lamps and houses"></a><figcaption>Montignac · unprocessed street view</figcaption></figure>

The four [Montignac views](https://github.com/ethan03805/enfusion-neural/blob/main/scenes/arma-montignac-v1.json) add streets, crossing markings, houses and outdoor furniture. Sample 2 illustrates the street. Sample 1 shows distant contents at the right edge that appear unsupported, so it is retained as a second source anomaly. All four directions were inspected; these are town views, with no model or appearance reference applied.

<details><summary>Street source anomaly</summary><figure><a href="media/arma-montignac-source-anomaly.png"><img src="media/arma-montignac-source-anomaly.png" width="2560" height="1440" loading="lazy" alt="Montignac houses with unsupported-looking building contents at the far right of the source capture"></a><figcaption>Sample 1 · distant object visibility needs investigation</figcaption></figure></details>

The next capture experiment should repeat the affected views with a longer initial settling period and a longer hold after each camera turn, changing one control at a time. Keep the original images and compare the same image regions. If the anomaly persists, inspect the affected scene resources and visibility settings before accepting these views. Its cause has not been established.

After that, add short camera paths through the town, factory and interior, plus controlled vehicle/character motion. Verify source visibility and repeatability before introducing model outputs. [Supported integration](integration.md) and aligned lighting references remain separate requirements.

Reproduce the source view with the [versioned camera config](https://github.com/ethan03805/enfusion-neural/blob/main/scenes/arma-st-philippe-v1.json) and a completed [native world inventory](integration.md#inventory-without-a-world):

```powershell
python scripts/capture_enfusion_scout.py --out experiments/local/st-philippe-recheck --config scenes/arma-st-philippe-v1.json --world-inventory experiments/local/resource-inventory-module-v2/resources.json --entities --lab-source <enfusion-lab-root>
```

Each run uses a new isolated addon. Inspect its images before accepting the scene. Entity physics and foliage continue during capture; this is not a deterministic animation fixture or a real-time performance measurement.

Arma Reforger imagery © Bohemia Interactive a.s.; it is outside this repository's code license. [Game-content usage rules](https://www.bohemia.net/en/community/game-content-usage-rules).
