#ifdef WORKBENCH
// Inspect only the observed house at its measured world origin.
class ENR_MaterialBinding
{
 int Matches;
 int Nodes;

 void Inspect(BaseContainer container, string path, int depth)
 {
  if (!container || depth > 5 || Nodes >= 80) return;
  Nodes++;
  PrintFormat("ENR_BIND_CONTAINER path=%1 class=%2 fields=%3", path, container.GetClassName(), container.GetNumVars());
  for (int i = 0; i < container.GetNumVars() && i < 256; i++)
  {
   string key = container.GetVarName(i);
   int kind = container.GetDataVarType(i);
   string defaultValue;
   bool hasDefault = container.GetDefaultAsString(key, defaultValue);
   PrintFormat("ENR_BIND_FIELD path=%1 name=%2 type=%3 has_default=%4 default=%5", path, key, kind, hasDefault, defaultValue);
   if (kind == DataVarType.OBJECT) { Inspect(container.GetObject(key), path + "." + key, depth + 1); continue; }
   if (kind == DataVarType.OBJECT_ARRAY)
   {
    BaseContainerList list = container.GetObjectArray(key);
    if (!list) continue;
    PrintFormat("ENR_BIND_ARRAY path=%1 name=%2 count=%3", path, key, list.Count());
    for (int j = 0; j < list.Count() && j < 32; j++) Inspect(list.Get(j), path + "." + key + "[" + j + "]", depth + 1);
    continue;
   }
   if (kind == DataVarType.STRING || kind == DataVarType.TEXTURE || kind == DataVarType.RESOURCE_NAME)
   {
    string value;
    bool read = container.Get(key, value);
    PrintFormat("ENR_BIND_TEXT path=%1 name=%2 read=%3 value=%4", path, key, read, value);
   }
  }
 }

 bool Found(IEntity entity)
 {
  VObject object = entity.GetVObject();
  if (!object || object.GetResourceName() != "{B608F5042424A544}Assets/Structures/Houses/Village/House_Village_E_1L02/House_Village_E_1L02t.xob") return true;
  if (vector.Distance(entity.GetOrigin(), "4586.93 18.167 10757.1") > 1) return true;
  Matches++;
  PrintFormat("ENR_BIND_MATCH origin=%1 mesh=%2", entity.GetOrigin(), object.GetResourceName());
  EntityPrefabData data = entity.GetPrefabData();
  if (data) Inspect(data.GetPrefab(), "prefab", 0);
  WorldEditor editor = Workbench.GetModule(WorldEditor);
  IEntitySource source = editor.GetApi().EntityToSource(entity);
  PrintFormat("ENR_BIND_SOURCE available=%1", source != null);
  if (source)
  {
   Inspect(source, "instance", 0);
   PrintFormat("ENR_BIND_COMPONENTS count=%1", source.GetComponentCount());
   for (int i = 0; i < source.GetComponentCount() && i < 24; i++) Inspect(source.GetComponent(i), "component[" + i + "]", 0);
  }
  return true;
 }

 static void Run(BaseWorld world)
 {
  ENR_MaterialBinding probe = new ENR_MaterialBinding();
  Print("ENR_BIND started");
  world.QueryEntitiesBySphere("4586.93 18.167 10757.1", 2, probe.Found);
  PrintFormat("ENR_BIND completed matches=%1 nodes=%2", probe.Matches, probe.Nodes);
 }
}
#endif
