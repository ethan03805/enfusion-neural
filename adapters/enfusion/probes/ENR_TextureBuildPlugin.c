// Builds only original TIFFs copied into a new isolated addon.
[WorkbenchPluginAttribute(name: "Enfusion Neural original textures", wbModules: {"ResourceManager"})]
class ENR_TextureBuildPlugin : WorkbenchPlugin
{
 override void RunCommandline()
 {
  ResourceManager manager = Workbench.GetModule(ResourceManager);
  if (!manager) { Print("ENR_TEXTURE failed=module"); Workbench.Exit(2); return; }
  for (int i = 0; i < ENR_TextureConfig.Count(); i++)
  {
   string source = ENR_TextureConfig.Source(i);
   manager.RebuildResourceFile(source, "PC", false);
   PrintFormat("ENR_TEXTURE requested=%1", source);
  }
  PrintFormat("ENR_TEXTURE queued=%1", ENR_TextureConfig.Count());
  // Asynchronous building must finish before the owning runner stops this editor.
 }
}
