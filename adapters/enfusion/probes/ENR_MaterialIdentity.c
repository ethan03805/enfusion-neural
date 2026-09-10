#ifdef WORKBENCH
// Read-only inspection around an observed gameplay camera; no material writes.
class ENR_MaterialIdentity
{
 int Objects;
 int Slots;
 int Containers;

 bool Found(IEntity entity)
 {
  VObject object = entity.GetVObject();
  if (!object) return true;
  Objects++;
  if (Objects > 160) return true;
  ResourceName mesh = object.GetResourceName();
  ResourceName prefab;
  EntityPrefabData data = entity.GetPrefabData();
  if (data) prefab = data.GetPrefabName();
  string materials[64];
  int count = object.GetMaterials(materials);
  vector mins, maxs;
  entity.GetBounds(mins, maxs);
  PrintFormat("ENR_IDENTITY_OBJECT id=%1 origin=%2 mesh=%3 prefab=%4 materials=%5 mins=%6 maxs=%7", Objects, entity.GetOrigin(), mesh, prefab, count, mins, maxs);
  for (int i = 0; i < count && i < 16; i++)
  {
   Slots++;
   string slot = materials[i];
   PrintFormat("ENR_IDENTITY_SLOT id=%1 index=%2 value=%3", Objects, i, slot);
   if (!slot.EndsWith(".emat")) continue;
   Resource resource = BaseContainerTools.LoadContainer(slot);
   if (!resource || !resource.IsValid()) { PrintFormat("ENR_IDENTITY_MATERIAL id=%1 index=%2 loaded=0", Objects, i); continue; }
   BaseContainer container = resource.GetResource().ToBaseContainer();
   if (!container) { PrintFormat("ENR_IDENTITY_MATERIAL id=%1 index=%2 loaded=0", Objects, i); continue; }
   Containers++;
   PrintFormat("ENR_IDENTITY_MATERIAL id=%1 index=%2 loaded=1 class=%3", Objects, i, container.GetClassName());
   for (int j = 0; j < container.GetNumVars() && j < 128; j++)
   {
    string key = container.GetVarName(j);
    int kind = container.GetDataVarType(j);
    if (kind != DataVarType.TEXTURE && kind != DataVarType.RESOURCE_NAME) continue;
    ResourceName value;
    bool read = container.Get(key, value);
    PrintFormat("ENR_IDENTITY_MAP id=%1 index=%2 field=%3 read=%4 value=%5", Objects, i, key, read, value);
   }
  }
  return true;
 }

 static void Run(BaseWorld world)
 {
  ENR_MaterialIdentity probe = new ENR_MaterialIdentity();
  Print("ENR_IDENTITY started");
  world.QueryEntitiesBySphere("4583.34 20.062 10707.7", 45, probe.Found);
  PrintFormat("ENR_IDENTITY completed objects=%1 slots=%2 containers=%3 limit=160", probe.Objects, probe.Slots, probe.Containers);
 }
}
#endif
