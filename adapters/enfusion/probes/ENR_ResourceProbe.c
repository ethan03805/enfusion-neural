// Read-only inventory for the isolated integration investigation.
// No game resources are modified or copied into the published repository.
class ENR_ResourceProbe
{
 string Query;
 int Count;
 int Locations;
 int NamedLocations;

 void CoreFile(string path)
 {
  Count++;
  if (Count > 250) return;
  PrintFormat("ENR_CORE_FILE query=%1 path=%2", Query, path);
  FileHandle file = FileIO.OpenFile(path, FileMode.READ);
  if (!file) return;
  string line;
  int lines;
  while (!file.IsEOF() && lines < 70)
  {
   if (file.ReadLine(line) < 0) break;
   PrintFormat("ENR_CORE_MATERIAL path=%1 line=%2 text=%3", path, lines, line);
   lines++;
  }
  file.Close();
 }

 bool FoundLocation(IEntity entity)
 {
  MapDescriptorComponent descriptor = MapDescriptorComponent.Cast(entity.FindComponent(MapDescriptorComponent));
  if (!descriptor) return true;
  Locations++;
  vector position = entity.GetOrigin();
  string displayName = entity.GetName();
  MapItem item = descriptor.Item();
  if (item && !item.GetDisplayName().IsEmpty()) displayName = item.GetDisplayName();
  if (displayName.IsEmpty()) return true;
  NamedLocations++;
  if (NamedLocations > 400) return true;
  PrintFormat("ENR_LOCATION name=%1 type=%2 position=%3", displayName, descriptor.GetBaseType(), position);
  return true;
 }

 void WorldLocations(BaseWorld world)
 {
  world.QueryEntitiesBySphere("2048 0 2048", 20000, FoundLocation);
  PrintFormat("ENR_LOCATION_DONE count=%1 named=%2 limit=400", Locations, NamedLocations);
 }

 void Found(ResourceName resourceName, string filePath = "")
 {
  Count++;
  if (Count > 120) return;
  PrintFormat("ENR_RESOURCE query=%1 resource=%2 path=%3", Query, resourceName, filePath);
  if (Query != "ColorGrading" && Query != "PostProcess" && Query != "Color" && Query != "HDR") return;
  string path = resourceName.GetPath();
  if (!path.EndsWith(".emat")) return;
  FileHandle file = FileIO.OpenFile(path, FileMode.READ);
  if (!file) return;
  string line;
  int lines;
  while (!file.IsEOF() && lines < 90)
  {
   if (file.ReadLine(line) < 0) break;
   PrintFormat("ENR_MATERIAL path=%1 line=%2 text=%3", path, lines, line);
   lines++;
  }
  file.Close();
 }

 void Run()
 {
  array<string> folders = {"system/materials", "System/Materials", "$core:system/materials", "Common/PostProcess"};
  foreach (string folder : folders)
  {
   Query = folder;
   Count = 0;
   bool found = FileIO.FindFiles(CoreFile, folder, ".emat");
   PrintFormat("ENR_CORE_DONE query=%1 count=%2 success=%3", Query, Count, found);
  }
  RunSearches();
 }

 void RunSearches()
 {
  array<string> queries = {"ColorGrade", "Post", "PP_", "HDR"};
  array<string> extensions = {"emat", "edds", "et", "ent", "conf"};
  foreach (string query : queries)
  {
   Query = query;
   Count = 0;
   array<string> filters = {query};
   bool result = Workbench.SearchResources(Found, extensions, filters);
   PrintFormat("ENR_RESOURCE_DONE query=%1 count=%2 success=%3", Query, Count, result);
  }
 }
}
