// Imports only the original reference mesh copied into this isolated addon.
[WorkbenchPluginAttribute(name: "Enfusion Neural original room import", wbModules: {"ResourceManager"})]
class ENR_MaterialRoomImportPlugin : WorkbenchPlugin
{
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
  if (ENR_ImportConfig.LoadCompleted)
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
