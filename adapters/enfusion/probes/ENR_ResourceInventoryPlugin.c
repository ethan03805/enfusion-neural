// Read-only resource inventory; no world, simulation or image capture.
[WorkbenchPluginAttribute(name: "Enfusion Neural resource inventory", wbModules: {"ScriptEditor"})]
class ENR_ResourceInventoryPlugin : WorkbenchPlugin
{
 override void RunCommandline()
 {
  Print("ENR_INVENTORY {\"event\":\"started\"}");
  ENR_ResourceProbe probe = new ENR_ResourceProbe();
  probe.Run();
  Print("ENR_INVENTORY {\"event\":\"completed\"}");
  Workbench.Exit(0);
 }
}
