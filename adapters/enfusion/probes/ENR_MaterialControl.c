#ifdef WORKBENCH
class ENR_MaterialControl
{
 static int Phase;
 static float Elapsed;
 static ref Material RoofMaterial;

 static void Report(BaseWorld world, string label)
 {
  vector camera[4];
  world.GetCurrentCamera(camera);
  PrintFormat("ENR_MAT_CONTROL phase=%1 origin=%2 direction=%3 world_frame=%4", label, camera[3], camera[2], world.GetFrameNumber());
 }

 static bool Step(BaseWorld world, float timeslice)
 {
  Elapsed += timeslice;
  if (Phase == 0)
  {
   Report(world, "source");
   bool sourceAccepted = System.MakeScreenshot("$profile:source");
   PrintFormat("ENR_MAT_CONTROL source_accepted=%1", sourceAccepted);
   Phase = 1; Elapsed = 0;
   return false;
  }
  if (Phase == 1 && Elapsed >= 1.5)
  {
   Report(world, "set");
   RoofMaterial = Material.GetMaterial("{C8C32599C4B55BF9}Assets/Structures/Houses/Village/House_Village_E_1L02/Data/House_Village_E_1L02t_roof.emat");
   if (RoofMaterial)
   {
    string loadedName;
    RoofMaterial.GetName(loadedName);
    int index = RoofMaterial.GetParamIndex("RoughnessScale");
    bool assigned = RoofMaterial.SetParam("RoughnessScale", 0.05);
    PrintFormat("ENR_MAT_CONTROL cached=1 name=%1 index=%2 assigned=%3 value=0.05", loadedName, index, assigned);
   }
   else Print("ENR_MAT_CONTROL cached=0");
   Phase = 2; Elapsed = 0;
   return false;
  }
  if (Phase == 2 && Elapsed >= 2)
  {
   Report(world, "changed");
   bool changedAccepted = System.MakeScreenshot("$profile:changed");
   PrintFormat("ENR_MAT_CONTROL changed_accepted=%1", changedAccepted);
   Phase = 3; Elapsed = 0;
   return false;
  }
  if (Phase == 3 && Elapsed >= 1.5)
  {
   Report(world, "reset");
   if (RoofMaterial) RoofMaterial.ResetParam("RoughnessScale");
   Print("ENR_MAT_CONTROL reset_requested");
   Phase = 4; Elapsed = 0;
   return false;
  }
  if (Phase == 4 && Elapsed >= 2)
  {
   Report(world, "restored");
   Print("ENR_MAT_CONTROL completed");
   return true;
  }
  return false;
 }
}
#endif
