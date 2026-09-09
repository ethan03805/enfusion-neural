[WorkbenchPluginAttribute(name: "Enfusion Neural sequence", wbModules: {"WorldEditor"})]
class ELab_CapturePlugin : WorkbenchPlugin
{
 override void RunCommandline()
 {
  WorldEditor editor = Workbench.GetModule(WorldEditor);
  if (!editor.GetApi().GetWorld())
  {
   Print("ELAB {\"protocol\":1,\"event\":\"error\",\"message\":\"No world loaded\"}");
   return;
  }
  editor.SwitchToGameMode(false, true);
  ELab_CaptureState.Elapsed = 0;
  ELab_CaptureState.Armed = true;
 }
}
