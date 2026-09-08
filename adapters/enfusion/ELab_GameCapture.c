#ifdef WORKBENCH
// Project-owned extension of Enfusion Lab's protocol-1 simulation capture adapter.
// The generated ENR_ReferenceConfig contains validated numerical/string literals.
class ELab_CaptureState
{
 static bool Armed;
 static float Elapsed;
 static float Delay = 8;
 static bool EnvironmentReady;
}

modded class ArmaReforgerScripted
{
 override void OnUpdate(BaseWorld world, float timeslice)
 {
  super.OnUpdate(world, timeslice);
  if (!ELab_CaptureState.Armed)
   return;
  WorldEditor editor = Workbench.GetModule(WorldEditor);
  ChimeraWorld chimera = GetGame().GetWorld();
  TimeAndWeatherManagerEntity weather;
  if (chimera)
   weather = chimera.GetTimeAndWeatherManager();
  if (!weather)
  {
   ELab_CaptureState.Armed = false;
   Print("ELAB {\"protocol\":1,\"event\":\"error\",\"message\":\"Reference scene has no time/weather manager\"}");
   return;
  }
  if (!ELab_CaptureState.EnvironmentReady)
  {
   array<ref WeatherState> states = {};
   weather.GetWeatherStatesList(states);
   bool found;
   foreach (WeatherState state : states)
   {
    PrintFormat("ENR_WEATHER name=%1", state.GetStateName());
    if (state.GetStateName() == ENR_ReferenceConfig.Weather)
     found = true;
   }
   if (!found)
   {
    ELab_CaptureState.Armed = false;
    Print("ELAB {\"protocol\":1,\"event\":\"error\",\"message\":\"Requested reference weather state is unavailable\"}");
    return;
   }
   bool dateOK = weather.SetDate(ENR_ReferenceConfig.Year, ENR_ReferenceConfig.Month, ENR_ReferenceConfig.Day, true);
   bool speedOK = weather.SetWindSpeedOverride(true, ENR_ReferenceConfig.WindSpeed);
   bool angleOK = weather.SetWindDirectionOverride(true, ENR_ReferenceConfig.WindDirection);
   if (!dateOK || !speedOK || !angleOK)
   {
    ELab_CaptureState.Armed = false;
    Print("ELAB {\"protocol\":1,\"event\":\"error\",\"message\":\"Reference environment control rejected\"}");
    return;
   }
   weather.ForceWeatherTo(true, ENR_ReferenceConfig.Weather, 0, 86400);
   ELab_CaptureState.EnvironmentReady = true;
  }
  if (!weather.SetTimeOfTheDay(ENR_ReferenceConfig.Hour, true))
  {
   ELab_CaptureState.Armed = false;
   Print("ELAB {\"protocol\":1,\"event\":\"error\",\"message\":\"Reference time control rejected\"}");
   return;
  }
  string position = "2048 60 2048";
  string direction = "1 0 0";
  string delay = "8";
  editor.GetCmdLine("-elabPosition", position);
  editor.GetCmdLine("-elabDirection", direction);
  editor.GetCmdLine("-elabSettle", delay);
  ELab_CaptureState.Delay = delay.ToFloat();
  vector look = direction.ToVector();
  world.SetCamera(world.GetCurrentCameraId(), position.ToVector(), look.VectorToAngles());
  ELab_CaptureState.Elapsed += timeslice;
  if (ELab_CaptureState.Elapsed < ELab_CaptureState.Delay)
   return;
  ELab_CaptureState.Armed = false;
  int width = editor.GetApi().GetScreenWidth();
  int height = editor.GetApi().GetScreenHeight();
  vector camera[4];
  world.GetCurrentCamera(camera);
  int year, month, day;
  weather.GetDate(year, month, day);
  WeatherState current = weather.GetCurrentWeatherState();
  string stateName = "unavailable";
  if (current)
   stateName = current.GetStateName();
  PrintFormat("ENR {\"protocol\":1,\"event\":\"environment\",\"date\":[%1,%2,%3],\"hour\":%4,\"wind_speed_mps\":%5,\"wind_direction_degrees\":%6,\"weather_state\":\"%7\"}", year, month, day, weather.GetTimeOfTheDay(), weather.GetWindSpeed(), weather.GetWindDirection(), stateName);
  PrintFormat("ENR {\"protocol\":1,\"event\":\"exposure\",\"hdr_brightness\":%1,\"scene_middle_brightness\":%2}", world.GetCameraHDRBrightness(world.GetCurrentCameraId()), world.GetCameraSceneMiddleBrightness(world.GetCurrentCameraId()));
  PrintFormat("ELAB {\"protocol\":1,\"event\":\"camera\",\"position\":[%1,%2,%3],\"direction\":[%4,%5,%6],\"world_frame\":%7,\"elapsed_simulation_seconds\":%8}", camera[3][0], camera[3][1], camera[3][2], camera[2][0], camera[2][1], camera[2][2], world.GetFrameNumber(), ELab_CaptureState.Elapsed);
  PrintFormat("ELAB {\"protocol\":1,\"event\":\"started\",\"viewport_width\":%1,\"viewport_height\":%2}", width, height);
  if (System.MakeScreenshot("$profile:frame"))
   Print("ELAB {\"protocol\":1,\"event\":\"submitted\"}");
  else
   Print("ELAB {\"protocol\":1,\"event\":\"error\",\"message\":\"Screenshot rejected\"}");
 }
}
#endif
