#ifdef WORKBENCH
class ENR_IlluminationInventory
{
 static void Inspect(BaseContainer container, string path, int depth)
 {
  if (!container || depth > 2) return;
  PrintFormat("ENR_ILLUM_CONTAINER path=%1 class=%2 fields=%3", path, container.GetClassName(), container.GetNumVars());
  for (int i = 0; i < container.GetNumVars() && i < 256; i++)
  {
   string key = container.GetVarName(i);
   int kind = container.GetDataVarType(i);
   string defaultValue;
   bool hasDefault = container.GetDefaultAsString(key, defaultValue);
   PrintFormat("ENR_ILLUM_FIELD path=%1 name=%2 type=%3 has_default=%4 default=%5", path, key, kind, hasDefault, defaultValue);
   if (kind == DataVarType.OBJECT) { Inspect(container.GetObject(key), path + "." + key, depth + 1); continue; }
   if (kind == DataVarType.SCALAR)
   {
    float number;
    bool read = container.Get(key, number);
    PrintFormat("ENR_ILLUM_NUMBER path=%1 name=%2 read=%3 value=%4", path, key, read, number);
   }
   else if (kind == DataVarType.COLOR)
   {
    Color colorValue = new Color(0, 0, 0, 0);
    bool colorRead = container.Get(key, colorValue);
    PrintFormat("ENR_ILLUM_COLOR path=%1 name=%2 read=%3 rgba=%4 %5 %6 %7", path, key, colorRead, colorValue.R(), colorValue.G(), colorValue.B(), colorValue.A());
   }
  }
 }

 static bool Step(BaseWorld world, float timeslice)
 {
  Print("ENR_ILLUM started");
  WorldEditor editor = Workbench.GetModule(WorldEditor);
  int scanned;
  int found;
  for (int sub = 0; sub < world.GetNumSubScenes() && scanned < 5000; sub++)
  {
   PrintFormat("ENR_ILLUM_SUB index=%1 name=%2 entities=%3", sub, world.GetSubSceneName(sub), world.GetNumEntities(sub));
   for (int index = 0; index < world.GetNumEntities(sub) && scanned < 5000; index++)
   {
    scanned++;
    IEntity entity = world.FindEntityByID(world.GetEntity(sub, index));
    GenericWorldEntity worldEntity = GenericWorldEntity.Cast(entity);
    GenericWorldLightEntity lightEntity = GenericWorldLightEntity.Cast(entity);
    if (!worldEntity && !lightEntity) continue;
    found++;
    PrintFormat("ENR_ILLUM_ENTITY sub=%1 index=%2 type=%3 name=%4", sub, index, entity.Type(), entity.GetName());
    EntityPrefabData data = entity.GetPrefabData();
    if (data) { PrintFormat("ENR_ILLUM_PREFAB name=%1", data.GetPrefabName()); Inspect(data.GetPrefab(), "prefab", 0); }
    Inspect(editor.GetApi().EntityToSource(entity), "instance", 0);
    if (worldEntity)
    {
     Material sky = worldEntity.GetSkyMaterial();
     if (sky)
     {
      string skyName; sky.GetName(skyName);
      PrintFormat("ENR_ILLUM_SKY name=%1", skyName);
      Resource resource = BaseContainerTools.LoadContainer(skyName);
      if (resource && resource.IsValid()) Inspect(resource.GetResource().ToBaseContainer(), "sky", 0);
     }
    }
   }
  }
  PrintFormat("ENR_ILLUM completed scanned=%1 found=%2 limit=%3", scanned, found, scanned >= 5000);
  return true;
 }
}
#endif
