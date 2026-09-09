#ifdef WORKBENCH
class ENR_ColorLookup
{
 static bool Applied;
 static void Init(BaseWorld world)
 {
  if (Applied) return;
  Applied = true;
  int cam = world.GetCurrentCameraId();
  PrintFormat("ENR_LOOKUP case=%1 camera=%2 priority=1000", ENR_LookupConfig.Case, cam);
  if (ENR_LookupConfig.Case == "off") { Print("ENR_LOOKUP requested=none"); return; }
  Resource material = BaseContainerTools.LoadContainer(ENR_LookupConfig.MaterialPath);
  if (!material || !material.IsValid()) { Print("ENR_LOOKUP failed=material"); return; }
  BaseContainer container = material.GetResource().ToBaseContainer();
  if (!container) { Print("ENR_LOOKUP failed=container"); return; }
  string table;
  bool enabled;
  bool tableRead = container.Get("ColorTable", table);
  bool enabledRead = container.Get("Enabled", enabled);
  PrintFormat("ENR_LOOKUP material_class=%1 table_read=%2 table=%3 enabled_read=%4 enabled=%5", container.GetClassName(), tableRead, table, enabledRead, enabled);
  world.SetCameraPostProcessEffect(cam, 1000, PostProcessEffectType.ColorGrading, ENR_LookupConfig.MaterialPath);
  Print("ENR_LOOKUP requested=apply");
  if (ENR_LookupConfig.Case == "removed")
  {
   world.SetCameraPostProcessEffect(cam, 1000, PostProcessEffectType.ColorGrading, "");
   Print("ENR_LOOKUP requested=remove");
  }
 }
}
#endif
