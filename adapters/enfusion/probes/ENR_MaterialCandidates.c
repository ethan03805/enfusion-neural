#ifdef WORKBENCH
class ENR_MaterialCandidates
{
 static int Phase;
 static float Elapsed;
 static ref Material RoofMaterial;

 static void Report(BaseWorld world, string label)
 {
  vector camera[4]; world.GetCurrentCamera(camera);
  PrintFormat("ENR_MAT_CANDIDATE phase=%1 origin=%2 direction=%3 world_frame=%4", label, camera[3], camera[2], world.GetFrameNumber());
  ChimeraWorld chimera = GetGame().GetWorld();
  TimeAndWeatherManagerEntity weather = chimera.GetTimeAndWeatherManager();
  WeatherState current = weather.GetCurrentWeatherState();
  string stateName = "unavailable";
  if (current) stateName = current.GetStateName();
  int year, month, day; weather.GetDate(year, month, day);
  PrintFormat("ENR_MAT_ENV phase=%1 hour=%2 wind=%3 state=%4 date=%5,%6,%7", label, weather.GetTimeOfTheDay(), weather.GetWindSpeed(), stateName, year, month, day);
  PrintFormat("ENR_MAT_EXPOSURE phase=%1 hdr=%2 scene_middle=%3", label, world.GetCameraHDRBrightness(world.GetCurrentCameraId()), world.GetCameraSceneMiddleBrightness(world.GetCurrentCameraId()));
 }

 static void Assign(float value)
 {
  if (!RoofMaterial) RoofMaterial = Material.GetMaterial("{C8C32599C4B55BF9}Assets/Structures/Houses/Village/House_Village_E_1L02/Data/House_Village_E_1L02t_roof.emat");
  if (!RoofMaterial) { Print("ENR_MAT_CANDIDATE cached=0"); return; }
  string loadedName; RoofMaterial.GetName(loadedName);
  int index = RoofMaterial.GetParamIndex("RoughnessScale");
  bool assigned = RoofMaterial.SetParam("RoughnessScale", value);
  PrintFormat("ENR_MAT_CANDIDATE cached=1 name=%1 index=%2 assigned=%3 value=%4", loadedName, index, assigned, value);
 }

 static bool Step(BaseWorld world, float timeslice)
 {
  Elapsed += timeslice;
  if (Phase == 0)
  {
   Report(world, "source");
   bool accepted0 = System.MakeScreenshot("$profile:source");
   PrintFormat("ENR_MAT_CANDIDATE source_accepted=%1", accepted0);
   Phase = 1; Elapsed = 0;
  }
  else if (Phase == 1 && Elapsed >= 1.5)
  {
   Report(world, "set040"); Assign(0.4); Phase = 2; Elapsed = 0;
  }
  else if (Phase == 2 && Elapsed >= 2)
  {
   Report(world, "candidate040");
   bool accepted1 = System.MakeScreenshot("$profile:candidate040");
   PrintFormat("ENR_MAT_CANDIDATE candidate040_accepted=%1", accepted1);
   Phase = 3; Elapsed = 0;
  }
  else if (Phase == 3 && Elapsed >= 1.5)
  {
   Report(world, "set070"); Assign(0.7); Phase = 4; Elapsed = 0;
  }
  else if (Phase == 4 && Elapsed >= 2)
  {
   Report(world, "candidate070");
   bool accepted2 = System.MakeScreenshot("$profile:candidate070");
   PrintFormat("ENR_MAT_CANDIDATE candidate070_accepted=%1", accepted2);
   Phase = 5; Elapsed = 0;
  }
  else if (Phase == 5 && Elapsed >= 1.5)
  {
   Report(world, "reset");
   if (RoofMaterial) RoofMaterial.ResetParam("RoughnessScale");
   Phase = 6; Elapsed = 0;
  }
  else if (Phase == 6 && Elapsed >= 2)
  {
   Report(world, "restored"); Print("ENR_MAT_CANDIDATE completed"); return true;
  }
  return false;
 }
}
#endif
