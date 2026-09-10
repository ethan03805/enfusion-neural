#ifdef WORKBENCH
class ENR_IlluminationControl
{
 static int Phase;
 static float Elapsed;
 static ref Material SkyMaterial;

 static void Report(BaseWorld world, string label)
 {
  vector camera[4]; world.GetCurrentCamera(camera);
  PrintFormat("ENR_ILLUM_CONTROL phase=%1 origin=%2 direction=%3 world_frame=%4", label, camera[3], camera[2], world.GetFrameNumber());
  ChimeraWorld chimera = GetGame().GetWorld();
  TimeAndWeatherManagerEntity weather = chimera.GetTimeAndWeatherManager();
  WeatherState current = weather.GetCurrentWeatherState();
  string stateName = "unavailable";
  if (current) stateName = current.GetStateName();
  int year, month, day; weather.GetDate(year, month, day);
  PrintFormat("ENR_ILLUM_ENV phase=%1 hour=%2 wind=%3 state=%4 date=%5,%6,%7", label, weather.GetTimeOfTheDay(), weather.GetWindSpeed(), stateName, year, month, day);
  PrintFormat("ENR_ILLUM_EXPOSURE phase=%1 hdr=%2 scene_middle=%3", label, world.GetCameraHDRBrightness(world.GetCurrentCameraId()), world.GetCameraSceneMiddleBrightness(world.GetCurrentCameraId()));
 }

 static bool Step(BaseWorld world, float timeslice)
 {
  Elapsed += timeslice;
  if (Phase == 0)
  {
   GenericWorldEntity worldEntity = GenericWorldEntity.Cast(world.FindEntityByName("world"));
   if (worldEntity) SkyMaterial = worldEntity.GetSkyMaterial();
   if (!SkyMaterial) { Print("ENR_ILLUM_CONTROL error=sky_unavailable"); return true; }
   string loadedName; SkyMaterial.GetName(loadedName);
   if (loadedName != "{621C7F2EC2763297}Terrains/Common/Sky/Atmosphere/Atmosphere.emat")
   { PrintFormat("ENR_ILLUM_CONTROL error=unexpected_sky name=%1", loadedName); return true; }
   PrintFormat("ENR_ILLUM_CONTROL sky=%1 index=%2", loadedName, SkyMaterial.GetParamIndex("SkyIntensityLV"));
   Report(world, "source");
   bool accepted0 = System.MakeScreenshot("$profile:source");
   PrintFormat("ENR_ILLUM_CONTROL source_accepted=%1", accepted0);
   Phase = 1; Elapsed = 0;
  }
  else if (Phase == 1 && Elapsed >= 1.5)
  {
   Report(world, "set");
   bool assigned = SkyMaterial.SetParam("SkyIntensityLV", 8.5);
   PrintFormat("ENR_ILLUM_CONTROL assigned=%1 value=8.5", assigned);
   Phase = 2; Elapsed = 0;
  }
  else if (Phase == 2 && Elapsed >= 5)
  {
   Report(world, "changed");
   bool accepted1 = System.MakeScreenshot("$profile:changed");
   PrintFormat("ENR_ILLUM_CONTROL changed_accepted=%1", accepted1);
   Phase = 3; Elapsed = 0;
  }
  else if (Phase == 3 && Elapsed >= 1.5)
  {
   Report(world, "reset");
   SkyMaterial.ResetParam("SkyIntensityLV");
   Print("ENR_ILLUM_CONTROL reset_requested");
   Phase = 4; Elapsed = 0;
  }
  else if (Phase == 4 && Elapsed >= 5)
  {
   Report(world, "restored"); Print("ENR_ILLUM_CONTROL completed"); return true;
  }
  return false;
 }
}
#endif
