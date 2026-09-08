# Sources

External references inform design choices. Local measurements remain the source of truth for what this project has executed. Links reviewed 8 September 2026.

| Reference | Relevance |
| --- | --- |
| [Reforger time and weather manager](https://community.bistudio.com/wikidata/external-data/arma-reforger/ArmaReforgerScriptAPIPublic/interfaceTimeAndWeatherManagerEntity.html) | Weather state selection and looping used by the reference scene adapter; installed script declarations and capture telemetry verify the local build |
| [ONNX Runtime DirectML provider](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html) | Windows GPU execution, device selection, D3D12 queue interoperability and sustained engineering status |
| [ONNX Runtime installation](https://onnxruntime.ai/docs/install/) | Current DirectML/WinML packaging direction |
| [AMD Windows support matrices](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html) | Verify exact GPU/OS/framework combinations before future ROCm setup; none is assumed here |
| [Microsoft D3D12 timestamp queries](https://learn.microsoft.com/en-us/windows/win32/direct3d12/timing) | GPU timestamp interpretation and queue timing |
| [GitHub Pages with custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) | Documentation build and deployment |

The original local feasibility investigation inspected Workbench script declarations and demonstrated screenshot export plus an RGB-inversion D3D12 control. This repository builds on that evidence but does not publish installed API files, Steam assets or private machine profiles. Enfusion Lab version 0.1.0 is the capture tool used for the first milestone.
