#ifdef WORKBENCH
class ENR_Settings
{
 static void Module(BaseContainer container)
 {
  if (!container) return;
  for (int i = 0; i < container.GetNumVars(); i++)
  {
   string key = container.GetVarName(i);
   int kind = container.GetDataVarType(i);
   float number;
   int integer;
   bool flag;
   if (kind == 13) { Module(container.GetObject(key)); continue; }
   if (kind == 1) container.Get(key, number);
   else if (kind == 7) { container.Get(key, integer); number = integer; }
   else if (kind == 9) { container.Get(key, flag); number = flag; }
   else continue;
   PrintFormat("ENR {\"protocol\":2,\"event\":\"setting\",\"module\":\"%1\",\"key\":\"%2\",\"value\":%3}", container.GetClassName(), key, number);
  }
 }
 static void Log()
 {
  array<string> modules = {"VideoUserSettings", "DisplayUserSettings", "GraphicsQualitySettings", "PipelineUserSettings", "ResourceManagerUserSettings", "GrassMaterialSettings", "PostprocessUserSettings", "TerrainGenMaterialSettings", "MaterialSystemUserSettings", "WaterPoolMaterialSettings"};
  foreach (string name : modules) Module(GetGame().GetEngineUserSettings().GetModule(name));
 }
}
#endif
