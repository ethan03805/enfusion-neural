// Imports only the original reference mesh copied into this isolated addon.
[WorkbenchPluginAttribute(name: "Enfusion Neural original room import", wbModules: {"ResourceManager"})]
class ENR_MaterialRoomImportPlugin : WorkbenchPlugin
{
 void InspectContainer(BaseContainer container, string path, int depth)
 {
  if (!container || depth > 4) return;
  PrintFormat("ENR_META_CONTAINER path=%1 class=%2 name=%3 vars=%4", path, container.GetClassName(), container.GetName(), container.GetNumVars());
  for (int i = 0; i < container.GetNumVars(); i++)
  {
   string key = container.GetVarName(i);
   int kind = container.GetDataVarType(i);
   string defaultValue;
   bool hasDefault = container.GetDefaultAsString(key, defaultValue);
   PrintFormat("ENR_META_FIELD path=%1 name=%2 type=%3 has_default=%4 default=%5", path, key, kind, hasDefault, defaultValue);
   float number;
   int integer;
   bool flag;
   bool read;
   if (kind == 1) read = container.Get(key, number);
   else if (kind == 7) { read = container.Get(key, integer); number = integer; }
   else if (kind == 9) { read = container.Get(key, flag); number = flag; }
   else if (kind == 13) { InspectContainer(container.GetObject(key), path + "." + key, depth + 1); continue; }
   else continue;
   PrintFormat("ENR_META_VALUE path=%1 name=%2 read=%3 value=%4", path, key, read, number);
  }
 }

 override void RunCommandline()
 {
  Print("ENR_IMPORT {\"event\":\"started\"}");
  ResourceManager manager = Workbench.GetModule(ResourceManager);
  PrintFormat("ENR_IMPORT {\"event\":\"module\",\"available\":%1}", manager != null);
  string absolutePath;
  if (!manager || !Workbench.GetAbsolutePath("Assets/ENR_ReferenceRoom/material-room.fbx", absolutePath))
  {
   Print("ENR_IMPORT {\"event\":\"failed\",\"stage\":\"source_path\"}");
   Workbench.Exit(2);
   return;
  }
  Print("ENR_IMPORT {\"event\":\"source_resolved\"}");
  if (ENR_ImportConfig.InspectMetadata)
  {
   MetaFile meta = manager.GetMetaFile(absolutePath);
   if (!meta) { Print("ENR_IMPORT {\"event\":\"failed\",\"stage\":\"metadata\"}"); Workbench.Exit(6); return; }
   InspectContainer(meta, "metadata", 0);
   BaseContainerList configurations = meta.GetObjectArray("Configurations");
   int inspected;
   if (configurations)
   {
    for (int c = 0; c < configurations.Count() && c < 8; c++)
    {
     BaseContainer configuration = configurations.Get(c);
     if (configuration.GetName() != "PC") continue;
     InspectContainer(configuration, "PC", 0);
     inspected++;
    }
   }
   PrintFormat("ENR_IMPORT {\"event\":\"metadata_inspected\",\"configurations\":%1}", inspected);
   if (inspected != 1) { Workbench.Exit(7); return; }
   Print("ENR_IMPORT {\"event\":\"completed\"}");
   Workbench.Exit(0);
   return;
  }
  else if (ENR_ImportConfig.BuildLive)
  {
   manager.RebuildResourceFile("Assets/ENR_ReferenceRoom/material-room.fbx", "PC", false);
   Print("ENR_IMPORT {\"event\":\"live_build_requested\"}");
   // Rebuild is asynchronous. The owning runner observes files/logs and ends
   // only this private process; requesting Exit here can truncate the import.
   return;
  }
  else if (ENR_ImportConfig.LoadCompleted)
  {
   Print("ENR_IMPORT {\"event\":\"load_completed_build\"}");
  }
  else if (ENR_ImportConfig.TypedMetadata)
  {
   manager.RebuildResourceFile("Assets/ENR_ReferenceRoom/material-room.fbx", "PC", false);
   Print("ENR_IMPORT {\"event\":\"typed_rebuild_returned\"}");
  }
  else if (ENR_ImportConfig.FBXHandler)
  {
   FBXImportRequest request = new FBXImportRequest();
   request.resourcePath = absolutePath;
   request.exportMorphs = false;
   request.exportSceneHierarchy = false;
   request.exportSkinning = false;
   ExportFBXResource handler = new ExportFBXResource();
   JsonApiStruct response = handler.GetResponse(request);
   if (!response) { Print("ENR_IMPORT {\"event\":\"failed\",\"stage\":\"handler_response\"}"); Workbench.Exit(3); return; }
   response.Pack();
   Print("ENR_IMPORT_RESPONSE " + response.AsString());
   Print("ENR_IMPORT {\"event\":\"handler_returned\"}");
  }
  else
  {
   bool registered = manager.RegisterResourceFile(absolutePath, true);
   PrintFormat("ENR_IMPORT {\"event\":\"registered\",\"accepted\":%1}", registered);
   if (!registered) { Workbench.Exit(3); return; }
  }
  Resource resource = Resource.Load(ENR_ImportConfig.Model);
  if (!resource || !resource.IsValid() || !resource.GetResource().ToMeshObject())
  {
   Print("ENR_IMPORT {\"event\":\"failed\",\"stage\":\"mesh_load\"}");
   Workbench.Exit(4);
   return;
  }
  PrintFormat("ENR_IMPORT {\"event\":\"mesh_loaded\",\"resource\":\"%1\"}", resource.GetResource().GetResourceName());
  string materials[64];
  int materialCount = resource.GetResource().ToMeshObject().GetMaterials(materials);
  PrintFormat("ENR_IMPORT {\"event\":\"materials\",\"count\":%1}", materialCount);
  Print("ENR_IMPORT {\"event\":\"completed\"}");
  Workbench.Exit(0);
 }
}
