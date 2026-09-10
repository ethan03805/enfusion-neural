// Read native VFS resources; destinations are confined to the isolated profile.
[WorkbenchPluginAttribute(name: "Enfusion Neural material access", wbModules: {"ResourceManager"})]
class ENR_MaterialAccessPlugin : WorkbenchPlugin
{
 override void RunCommandline()
 {
  Print("ENR_ACCESS started");
  for (int i = 0; i < ENR_AccessConfig.Count(); i++)
  {
   string label = ENR_AccessConfig.Label(i);
   string source = ENR_AccessConfig.Source(i);
   string destination = "$profile:ENR_native_" + label;
   bool exists = FileIO.FileExists(source);
   bool copied = FileIO.CopyFile(source, destination);
   PrintFormat("ENR_ACCESS_FILE name=%1 exists=%2 copied=%3 destination=%4", label, exists, copied, destination);
  }
  Print("ENR_ACCESS completed");
  Workbench.Exit(0);
 }
}
