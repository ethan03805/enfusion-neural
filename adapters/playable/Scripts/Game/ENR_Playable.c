// Loaded only by the isolated local prototype project. No renderer hooks.
class ENR_PlayableState
{
 static float Elapsed;
 static float NextLog;
 static bool Attempted;
 static IEntity Player;
}

modded class ArmaReforgerScripted
{
 override void OnUpdate(BaseWorld world, float timeslice)
 {
  super.OnUpdate(world, timeslice);
  if (!world) return;
  ENR_PlayableState.Elapsed += timeslice;
  ChimeraWorld chimera = GetGame().GetWorld();
  if (!chimera) return;
  TimeAndWeatherManagerEntity weather = chimera.GetTimeAndWeatherManager();
  if (!weather) return;
  if (!ENR_PlayableState.Attempted && ENR_PlayableState.Elapsed > 4)
  {
   PlayerController controller = GetGame().GetPlayerController();
   if (!controller) return;
   ENR_PlayableState.Attempted = true;
   weather.SetDate(1989, 6, 21, true);
   weather.SetTimeOfTheDay(13, true);
   weather.ForceWeatherTo(true, "Clear", 0, 86400);
   weather.SetWindSpeedOverride(true, 0);
   vector position = "4773.46 166.042 7094.57";
   position[1] = world.GetSurfaceY(position[0], position[2]) + 0.2;
   Resource resource = Resource.Load("{26A9756790131354}Prefabs/Characters/Factions/BLUFOR/US_Army/Character_US_Rifleman.et");
   if (!resource || !resource.IsValid()) { Print("ENR_LIVE spawn_resource_failed"); return; }
   EntitySpawnParams parameters = new EntitySpawnParams();
   parameters.TransformMode = ETransformMode.WORLD;
   Math3D.MatrixIdentity4(parameters.Transform);
   parameters.Transform[3] = position;
   ENR_PlayableState.Player = GetGame().SpawnEntityPrefab(resource, world, parameters);
   bool controlled = controller.SetControlledEntity(ENR_PlayableState.Player);
   PrintFormat("ENR_LIVE player_spawned=%1 controlled=%2 position=%3", ENR_PlayableState.Player != null, controlled, position);
  }
  if (ENR_PlayableState.Elapsed >= ENR_PlayableState.NextLog)
  {
   ENR_PlayableState.NextLog = ENR_PlayableState.Elapsed + 1;
   vector camera[4]; world.GetCurrentCamera(camera);
   PrintFormat("ENR_LIVE simulation_s=%1 frame=%2 dt_ms=%3 camera=%4 direction=%5", ENR_PlayableState.Elapsed, world.GetFrameNumber(), timeslice * 1000, camera[3], camera[2]);
  }
 }
}
